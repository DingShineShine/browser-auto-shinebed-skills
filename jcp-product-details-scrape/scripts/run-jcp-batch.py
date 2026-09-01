import argparse
import atexit
import hashlib
import json
import re
import subprocess
import sys
import time
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path


JCP_HOME = "https://www.jcpenney.com/"


def run_cmd(args: list[str], cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def as_text(value) -> str:
    return "" if value is None else str(value)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def slug(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "-", value).strip("-")
    return cleaned[:90] or fallback


def hash_text(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", errors="replace")).hexdigest()[:12]


def make_search_url(sku: str) -> str:
    return f"https://www.jcpenney.com/s?searchTerm={sku}"


def print_progress(message: str) -> None:
    print(message, flush=True)


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def browser_eval(session: str, js: str, cwd: Path, timeout: int = 120) -> str:
    result = run_cmd(["browser-act", "--session", session, "eval", js], cwd=cwd, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip())
    return result.stdout.strip()


def is_nav_timeout(message: str) -> bool:
    return "Timed out waiting for page load state" in message


def group_key_from_row(row: dict) -> tuple[str, str]:
    return (as_text(row.get("sku_name") or row.get("spu_name")), as_text(row.get("jcp_prefix") or row.get("sku_prefix")))


def group_key_from_group(group: dict) -> tuple[str, str]:
    return (
        as_text(group.get("sku_name") or group.get("spu_name")),
        as_text(group.get("jcp_prefix") or group.get("sku_prefix")),
    )


def rows_by_group(source_rows: list[dict]) -> dict[tuple[str, str], list[dict]]:
    grouped: dict[tuple[str, str], list[dict]] = {}
    for row in source_rows:
        grouped.setdefault(group_key_from_row(row), []).append(row)
    return grouped


def selected_groups(groups: list[dict], start: int, limit: int) -> list[tuple[int, dict]]:
    selected = list(enumerate(groups, start=1))[start - 1 :]
    return selected[:limit] if limit else selected


def unique_group_skus(group: dict, source_rows: list[dict]) -> list[str]:
    skus: OrderedDict[str, None] = OrderedDict()
    for row in source_rows:
        sku = as_text(row.get("crawl_sku")).strip()
        if sku:
            skus.setdefault(sku, None)
    for sku in group.get("source_skus") or []:
        sku = as_text(sku).strip()
        if sku:
            skus.setdefault(sku, None)
    request_sku = as_text(group.get("request_sku")).strip()
    if request_sku:
        skus.setdefault(request_sku, None)
    return list(skus)


def alias_cache_path(alias_dir: Path, sku: str) -> Path:
    return alias_dir / f"{slug(sku, 'sku')}.json"


def default_alias(sku: str, status: str, message: str) -> dict:
    return {
        "input_sku_id": sku,
        "alias_url": f"https://browse-api.jcpenney.com/v3/product-aliases/url/{sku}",
        "alias_id": "",
        "ppId": "",
        "pdpUrl": "",
        "selectedSKUId": "",
        "alias_status": status,
        "http_status": "",
        "message": message,
        "resolved_at": utc_now(),
    }


def existing_ok_json(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        payload = read_json(path)
    except Exception:
        return False
    return bool(payload.get("ok")) and not payload.get("error")


def build_alias_js(sku_ids: list[str], timeout_ms: int, concurrency: int) -> str:
    config = {
        "skuIds": sku_ids,
        "timeoutMs": timeout_ms,
        "concurrency": max(1, concurrency),
    }
    return (
        """
(async () => {
  const config = __CONFIG__;
  const startedAt = new Date().toISOString();

  function asString(value) {
    return value == null ? "" : String(value);
  }

  function normalizeJcpUrl(value) {
    const raw = String(value || "").trim();
    if (!raw) return "";
    const url = new URL(raw, "https://www.jcpenney.com/");
    if (!/(^|\\.)jcpenney\\.com$/i.test(url.hostname)) {
      throw new Error("Expected a jcpenney.com URL, got: " + url.hostname);
    }
    return url.href;
  }

  async function resolveOne(skuId) {
    const sku = String(skuId || "").trim();
    const aliasUrl = "https://browse-api.jcpenney.com/v3/product-aliases/url/" + encodeURIComponent(sku);
    const base = {
      input_sku_id: sku,
      alias_url: aliasUrl,
      alias_id: "",
      ppId: "",
      pdpUrl: "",
      selectedSKUId: "",
      alias_status: "",
      http_status: "",
      message: "",
      resolved_at: new Date().toISOString()
    };
    if (!sku) {
      return { ...base, alias_status: "skipped", message: "Empty SKU ID." };
    }
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), Math.max(1000, config.timeoutMs || 20000));
    try {
      const response = await fetch(aliasUrl, {
        credentials: "include",
        signal: controller.signal,
        headers: {
          "Accept": "application/json",
          "X-Client-Name": "PDPREGULAR",
          "x-client-source": "PDP",
          "jcp_version": "GREEN"
        }
      });
      const text = await response.text();
      let data = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch (error) {
        data = {};
      }
      const pdpUrl = normalizeJcpUrl(data.pdpUrl);
      return {
        ...base,
        alias_id: asString(data.id),
        ppId: asString(data.ppId),
        pdpUrl,
        selectedSKUId: asString(data.selectedSKUId),
        alias_status: response.ok && pdpUrl ? "ok" : "http_" + response.status,
        http_status: asString(response.status),
        message: response.ok ? "" : ("product-aliases returned HTTP " + response.status)
      };
    } catch (error) {
      return {
        ...base,
        alias_status: "error",
        message: String(error && error.message || error)
      };
    } finally {
      clearTimeout(timeout);
    }
  }

  async function mapLimit(items, limit, worker) {
    const results = new Array(items.length);
    let cursor = 0;
    const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
      while (cursor < items.length) {
        const index = cursor++;
        results[index] = await worker(items[index], index);
      }
    });
    await Promise.all(workers);
    return results;
  }

  const aliases = await mapLimit(config.skuIds || [], Math.max(1, config.concurrency || 4), resolveOne);
  return JSON.stringify({
    ok: true,
    started_at: startedAt,
    resolved_at: new Date().toISOString(),
    count: aliases.length,
    aliases
  });
})()
        """.replace("__CONFIG__", json.dumps(config, ensure_ascii=False))
    ).strip()


def open_browser(args, skill_dir: Path) -> int:
    if args.reuse_session:
        print_progress(f"Reusing browser-act session {args.session}")
        return 0
    browser_id = args.browser_id or (f"adspower:{args.ads_id}" if args.ads_id else "")
    if not browser_id:
        raise SystemExit("--browser-id or --ads-id is required unless --reuse-session is set.")
    print_progress(f"Opening browser {browser_id} with about:blank")
    opened = run_cmd(
        ["browser-act", "--session", args.session, "browser", "open", browser_id, "about:blank"],
        cwd=skill_dir,
        timeout=180,
    )
    if opened.returncode != 0:
        print_progress((opened.stderr or opened.stdout).strip())
    return opened.returncode


def close_browser_session(session: str, skill_dir: Path) -> None:
    print_progress(f"Closing browser-act session {session}")
    closed = run_cmd(["browser-act", "session", "close", session], cwd=skill_dir, timeout=60)
    if closed.returncode != 0:
        print_progress(f"  close warning: {(closed.stderr or closed.stdout).strip()}")


def ensure_jcp_context(session: str, skill_dir: Path) -> None:
    print_progress("Preparing JCP browser context for alias resolution")
    nav = run_cmd(["browser-act", "--session", session, "navigate", JCP_HOME], cwd=skill_dir, timeout=120)
    if nav.returncode != 0:
        message = (nav.stderr or nav.stdout).strip()
        if is_nav_timeout(message):
            print_progress(f"  navigate warning: {message}; continuing")
        else:
            raise RuntimeError(message)
    wait = run_cmd(["browser-act", "--session", session, "wait", "stable", "--timeout", "60000"], cwd=skill_dir, timeout=90)
    if wait.returncode != 0:
        print_progress(f"  wait warning: {(wait.stderr or wait.stdout).strip()}")
        time.sleep(2)


def resolve_aliases(
    sku_ids: list[str],
    alias_dir: Path,
    output_dir: Path,
    args,
    skill_dir: Path,
) -> dict[str, dict]:
    alias_dir.mkdir(parents=True, exist_ok=True)
    alias_map: dict[str, dict] = {}
    missing: list[str] = []

    for sku in sku_ids:
        cache_path = alias_cache_path(alias_dir, sku)
        if not args.refresh_alias and cache_path.exists():
            try:
                cached = read_json(cache_path)
                if cached.get("input_sku_id"):
                    alias_map[sku] = cached
                    continue
            except Exception:
                pass
        missing.append(sku)

    if missing:
        ensure_jcp_context(args.session, skill_dir)

    for start in range(0, len(missing), args.alias_batch_size):
        chunk = missing[start : start + args.alias_batch_size]
        print_progress(f"Resolving aliases {start + 1}-{start + len(chunk)} of {len(missing)}")
        try:
            payload_text = browser_eval(
                args.session,
                build_alias_js(chunk, args.fetch_timeout_ms, args.alias_concurrency),
                skill_dir,
                timeout=args.eval_timeout,
            )
            payload = json.loads(payload_text)
            aliases = payload.get("aliases") or []
        except Exception as error:
            aliases = [default_alias(sku, "error", str(error)) for sku in chunk]

        by_sku = {as_text(alias.get("input_sku_id")): alias for alias in aliases if alias.get("input_sku_id")}
        for sku in chunk:
            alias = by_sku.get(sku) or default_alias(sku, "missing_alias_result", "Alias batch did not return this SKU.")
            alias_map[sku] = alias
            write_json(alias_cache_path(alias_dir, sku), alias)

        counts = Counter(as_text(alias_map[sku].get("alias_status")) for sku in chunk)
        print_progress("  " + ", ".join(f"{status or 'blank'}={count}" for status, count in sorted(counts.items())))

    alias_payload = {
        "generated_at": utc_now(),
        "source_sku_count": len(sku_ids),
        "status_counts": dict(Counter(as_text(alias.get("alias_status")) for alias in alias_map.values())),
        "aliases": alias_map,
    }
    write_json(output_dir / "alias_map.json", alias_payload)
    print_progress(f"Alias map saved: {output_dir / 'alias_map.json'}")
    return alias_map


def fetch_key_for_alias(alias: dict, sku: str) -> tuple[str, str, str, str]:
    pdp_url = as_text(alias.get("pdpUrl")).strip()
    pp_id = as_text(alias.get("ppId")).strip()
    if alias.get("alias_status") == "ok" and pdp_url:
        key = f"ppid:{pp_id}" if pp_id else f"url:{hash_text(pdp_url)}"
        return key, "pdp", pdp_url, pp_id
    return f"search:{sku}", "search", make_search_url(sku), ""


def build_fetch_plan(
    selected: list[tuple[int, dict]],
    grouped_rows: dict[tuple[str, str], list[dict]],
    alias_map: dict[str, dict],
) -> tuple[OrderedDict[str, dict], dict[int, dict]]:
    units: OrderedDict[str, dict] = OrderedDict()
    group_units: dict[int, dict] = {}

    for group_index, group in selected:
        key = group_key_from_group(group)
        source_rows = grouped_rows.get(key, [])
        source_skus = unique_group_skus(group, source_rows)
        fetch_keys: OrderedDict[str, None] = OrderedDict()

        for sku in source_skus:
            alias = alias_map.get(sku) or default_alias(sku, "not_resolved", "SKU was not present in alias map.")
            fetch_key, kind, url, pp_id = fetch_key_for_alias(alias, sku)
            fetch_keys.setdefault(fetch_key, None)
            if fetch_key not in units:
                units[fetch_key] = {
                    "fetch_key": fetch_key,
                    "kind": kind,
                    "url": url,
                    "ppId": pp_id,
                    "request_sku": sku,
                    "source_skus": [],
                    "groups": [],
                    "aliases": [],
                }
            unit = units[fetch_key]
            if sku not in unit["source_skus"]:
                unit["source_skus"].append(sku)
            if not any(entry["group_index"] == group_index for entry in unit["groups"]):
                unit["groups"].append(
                    {
                        "group_index": group_index,
                        "sku_name": key[0],
                        "jcp_prefix": key[1],
                    }
                )
            unit["aliases"].append(alias)

        group_units[group_index] = {
            "fetch_keys": list(fetch_keys),
            "source_skus": source_skus,
        }

    return units, group_units


def pdp_raw_path(pdp_dir: Path, ordinal: int, unit: dict) -> Path:
    safe_key = slug(unit["fetch_key"].replace(":", "-"), f"fetch-{ordinal}")
    return pdp_dir / f"{ordinal:03d}-{safe_key}-{hash_text(unit['fetch_key'])}.json"


def get_page_snapshot(session: str, cwd: Path) -> dict:
    js = (
        "JSON.stringify({href:location.href,title:document.title,"
        "hasProductDetails:!!(window.__PRELOADED_STATE__&&window.__PRELOADED_STATE__.productDetails),"
        "productId:window.__PRELOADED_STATE__&&window.__PRELOADED_STATE__.productDetails&&window.__PRELOADED_STATE__.productDetails.id,"
        "webId:window.__PRELOADED_STATE__&&window.__PRELOADED_STATE__.productDetails&&window.__PRELOADED_STATE__.productDetails.webId})"
    )
    try:
        return json.loads(browser_eval(session, js, cwd, timeout=30))
    except Exception as error:
        return {"error": str(error)}


def navigate_to_unit(session: str, url: str, skill_dir: Path) -> tuple[str, dict]:
    navigation_warning = ""
    nav = run_cmd(["browser-act", "--session", session, "navigate", url], cwd=skill_dir, timeout=120)
    if nav.returncode != 0:
        message = (nav.stderr or nav.stdout).strip()
        if is_nav_timeout(message):
            navigation_warning = message
            print_progress(f"  navigate warning: {message}; continuing with page extraction")
        else:
            raise RuntimeError(message)

    wait = run_cmd(["browser-act", "--session", session, "wait", "stable", "--timeout", "60000"], cwd=skill_dir, timeout=90)
    if wait.returncode != 0:
        print_progress(f"  wait warning: {(wait.stderr or wait.stdout).strip()}")
        time.sleep(2)

    return navigation_warning, get_page_snapshot(session, skill_dir)


def build_scrape_js(skill_dir: Path, page_url: str, args) -> str:
    script = run_cmd(
        [
            sys.executable,
            "scripts/scrape-product-details.py",
            "--url",
            page_url,
            "--compact",
            "--fetch-timeout-ms",
            str(args.fetch_timeout_ms),
            "--offering-concurrency",
            str(args.offering_concurrency),
        ],
        cwd=skill_dir,
        timeout=30,
    )
    if script.returncode != 0:
        raise RuntimeError((script.stderr or script.stdout).strip())
    return script.stdout.strip()


def summarize_unit_raw(raw: dict) -> dict:
    product = raw.get("product") or {}
    return {
        "fetch_key": raw.get("fetch_key", ""),
        "kind": raw.get("fetch_kind", ""),
        "url": raw.get("fetch_url", ""),
        "request_sku": raw.get("request_sku", ""),
        "ok": bool(raw.get("ok")) and not raw.get("error"),
        "variant_count": raw.get("variant_count", 0),
        "warning_count": raw.get("warning_count", 0),
        "product_id": product.get("product_id", ""),
        "web_id": product.get("web_id", ""),
        "product_name": product.get("name", ""),
        "current_url": raw.get("current_url", ""),
        "raw_path": raw.get("raw_path", ""),
        "message": raw.get("message", ""),
    }


def fetch_pdp_unit(ordinal: int, unit: dict, pdp_dir: Path, args, skill_dir: Path) -> dict:
    raw_path = pdp_raw_path(pdp_dir, ordinal, unit)
    if args.resume and existing_ok_json(raw_path):
        raw = read_json(raw_path)
        raw["raw_path"] = str(raw_path)
        print_progress(f"[fetch {ordinal}] {unit['fetch_key']} already ok, reusing")
        return raw

    print_progress(f"[fetch {ordinal}] {unit['kind']} {unit['fetch_key']} -> {unit['request_sku']}")
    page = {}
    navigation_warning = ""
    try:
        navigation_warning, page = navigate_to_unit(args.session, unit["url"], skill_dir)
        if page.get("error") and navigation_warning:
            raise RuntimeError(page.get("error") or navigation_warning)
        page_url = page.get("href") or unit["url"]
        scrape_js = build_scrape_js(skill_dir, page_url, args)
        scraped_text = browser_eval(args.session, scrape_js, skill_dir, timeout=args.eval_timeout)
        raw = json.loads(scraped_text)
    except Exception as error:
        raw = {
            "ok": False,
            "error": True,
            "stage": "fetch_pdp_unit",
            "message": str(error),
            "variants": [],
            "warnings": [],
        }
        if not page:
            page = get_page_snapshot(args.session, skill_dir)

    raw["fetch_key"] = unit["fetch_key"]
    raw["fetch_kind"] = unit["kind"]
    raw["fetch_url"] = unit["url"]
    raw["fetch_ppId"] = unit.get("ppId", "")
    raw["request_sku"] = unit["request_sku"]
    raw["unit_source_skus"] = unit.get("source_skus", [])
    raw["unit_groups"] = unit.get("groups", [])
    raw["unit_alias_status_counts"] = dict(Counter(as_text(alias.get("alias_status")) for alias in unit.get("aliases", [])))
    raw["page_snapshot"] = page
    raw["navigation_warning"] = navigation_warning
    raw["raw_path"] = str(raw_path)
    write_json(raw_path, raw)

    ok = bool(raw.get("ok")) and not raw.get("error")
    product = raw.get("product") or {}
    print_progress(
        f"  ok={ok} variants={raw.get('variant_count', 0)} "
        f"product={product.get('product_id', '')} warnings={raw.get('warning_count', 0)}"
    )
    return raw


def alias_for_group(source_skus: list[str], alias_map: dict[str, dict]) -> list[dict]:
    return [alias_map.get(sku) or default_alias(sku, "not_resolved", "SKU was not present in alias map.") for sku in source_skus]


def resolution_status(aliases: list[dict]) -> str:
    ppids = {as_text(alias.get("ppId")) for alias in aliases if alias.get("alias_status") == "ok" and alias.get("ppId")}
    if len(ppids) > 1:
        return "multiple_ppids"
    if len(ppids) == 1:
        return "single_ppid"
    return "alias_unresolved"


def build_group_raw(
    group_index: int,
    group: dict,
    source_rows: list[dict],
    group_unit_info: dict,
    fetched_by_key: dict[str, dict],
    alias_map: dict[str, dict],
    raw_dir: Path,
) -> dict:
    sku_name, prefix = group_key_from_group(group)
    source_skus = group_unit_info.get("source_skus") or unique_group_skus(group, source_rows)
    aliases = alias_for_group(source_skus, alias_map)
    fetch_keys = group_unit_info.get("fetch_keys") or []
    fetches = [fetched_by_key[key] for key in fetch_keys if key in fetched_by_key]

    variants_by_sku: OrderedDict[str, dict] = OrderedDict()
    warnings: list[str] = []
    products: list[dict] = []
    current_urls: list[str] = []
    fetch_failures: list[str] = []

    for raw in fetches:
        ok = bool(raw.get("ok")) and not raw.get("error")
        if not ok:
            fetch_failures.append(f"{raw.get('fetch_key', '')}: {raw.get('message', '')}")
        product = raw.get("product") or {}
        if product:
            products.append(product)
        current_url = as_text(raw.get("current_url") or (raw.get("page_snapshot") or {}).get("href"))
        if current_url:
            current_urls.append(current_url)
        for warning in raw.get("warnings") or []:
            warnings.append(f"{raw.get('fetch_key', '')}: {warning}")
        if raw.get("navigation_warning"):
            warnings.append(f"{raw.get('fetch_key', '')}: {raw.get('navigation_warning')}")
        for variant in raw.get("variants") or []:
            sku_id = as_text(variant.get("sku_id"))
            if sku_id and sku_id not in variants_by_sku:
                variants_by_sku[sku_id] = variant

    source_ppids = sorted({as_text(alias.get("ppId")) for alias in aliases if alias.get("alias_status") == "ok" and alias.get("ppId")})
    alias_counts = Counter(as_text(alias.get("alias_status")) for alias in aliases)
    ok_fetches = [raw for raw in fetches if bool(raw.get("ok")) and not raw.get("error")]
    group_slug = slug(f"{sku_name}-{prefix}", f"group-{group_index}")
    raw_path = raw_dir / f"{group_index:02d}-{group_slug}.json"
    notes = []
    if fetch_failures:
        notes.append(f"{len(fetch_failures)} fetch unit(s) failed.")
    if len(source_ppids) > 1:
        notes.append("Multiple ppIds were resolved inside this SKU name + prefix group.")
    if alias_counts and alias_counts.get("ok", 0) < len(aliases):
        notes.append("Some source SKU aliases did not resolve and used searchTerm fallback.")

    payload = {
        "ok": bool(ok_fetches),
        "error": not bool(ok_fetches),
        "scraped_at": utc_now(),
        "sku_name": sku_name,
        "spu_name": sku_name,
        "source_group_key": group.get("group_key", ""),
        "source_jcp_prefix": prefix,
        "source_sku_prefix": prefix,
        "request_sku": as_text(group.get("request_sku")),
        "request_skus": source_skus,
        "source_group_count": len(source_rows) if source_rows else group.get("source_count", 0),
        "source_skus": source_skus,
        "source_rows": [row.get("source_row") for row in source_rows] or group.get("source_rows", []),
        "resolution_status": resolution_status(aliases),
        "source_ppids": source_ppids,
        "ppid_count": len(source_ppids),
        "pdp_fetch_count": len(fetch_keys),
        "pdp_fetch_keys": fetch_keys,
        "pdp_fetches": [summarize_unit_raw(raw) for raw in fetches],
        "alias_status_counts": dict(alias_counts),
        "aliases": aliases,
        "products": products,
        "product": products[0] if products else {},
        "current_urls": current_urls,
        "current_url": current_urls[0] if current_urls else "",
        "variants": list(variants_by_sku.values()),
        "variant_count": len(variants_by_sku),
        "warning_count": len(warnings),
        "warnings": warnings,
        "fetch_failures": fetch_failures,
        "message": " | ".join(notes),
    }
    write_json(raw_path, payload)
    payload["raw_path"] = str(raw_path)
    return payload


def collect_selected_skus(
    selected: list[tuple[int, dict]],
    grouped_rows: dict[tuple[str, str], list[dict]],
) -> list[str]:
    skus: OrderedDict[str, None] = OrderedDict()
    for _, group in selected:
        for sku in unique_group_skus(group, grouped_rows.get(group_key_from_group(group), [])):
            skus.setdefault(sku, None)
    return list(skus)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    parser = argparse.ArgumentParser(description="Run JCPenney alias-first PDP variant scraping by SKU name + JCP prefix group.")
    parser.add_argument("--source-json", required=True)
    parser.add_argument("--skill-dir", required=True)
    parser.add_argument("--session", default="jcp-details")
    parser.add_argument("--ads-id", default="", help="AdsPower user id. Converted to adspower:<user_id> for browser open.")
    parser.add_argument("--browser-id", default="", help="browser-act browser id. For AdsPower use adspower:<user_id>.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--start", type=int, default=1, help="1-based group index to start from.")
    parser.add_argument("--limit", type=int, default=0, help="Optional maximum number of groups.")
    parser.add_argument("--reuse-session", action="store_true", help="Skip browser open and reuse this run's already-open browser-act session.")
    parser.add_argument("--resume", action="store_true", help="Reuse ok alias/PDP cache files and rebuild group raw JSON.")
    parser.add_argument("--refresh-alias", action="store_true", help="Ignore alias cache and resolve product-aliases again.")
    parser.add_argument("--keep-session-open", action="store_true", help="Leave the browser-act session open after this script finishes.")
    parser.add_argument("--eval-timeout", type=int, default=600, help="Timeout in seconds for browser-side extraction eval.")
    parser.add_argument("--fetch-timeout-ms", type=int, default=10000, help="Timeout in milliseconds for browser-side API fetches.")
    parser.add_argument("--offering-concurrency", type=int, default=8, help="Concurrent sku-offerings fetches inside the page.")
    parser.add_argument("--alias-batch-size", type=int, default=40, help="Number of source SKU IDs per product-aliases browser eval.")
    parser.add_argument("--alias-concurrency", type=int, default=6, help="Concurrent product-aliases calls inside the page.")
    parser.add_argument("--request-sku-override", default="", help="Override request_sku for a single selected group.")
    args = parser.parse_args()

    if args.start < 1:
        raise SystemExit("--start must be >= 1.")
    if args.alias_batch_size < 1:
        raise SystemExit("--alias-batch-size must be >= 1.")
    if args.alias_concurrency < 1:
        raise SystemExit("--alias-concurrency must be >= 1.")

    source_path = Path(args.source_json).resolve()
    skill_dir = Path(args.skill_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    raw_dir = output_dir / "raw"
    alias_dir = output_dir / "aliases"
    pdp_dir = output_dir / "pdp_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    pdp_dir.mkdir(parents=True, exist_ok=True)

    source = read_json(source_path)
    groups = source["groups"]
    selected = selected_groups(groups, args.start, args.limit)
    if args.request_sku_override:
        if len(selected) != 1:
            raise SystemExit("--request-sku-override requires exactly one selected group.")
        index, group = selected[0]
        selected = [(index, {**group, "request_sku": args.request_sku_override})]
    if not selected:
        raise SystemExit("No groups selected.")

    grouped_rows = rows_by_group(source["rows"])
    source_skus = collect_selected_skus(selected, grouped_rows)
    print_progress(f"Selected groups: {len(selected)}; unique source JCP SKUs: {len(source_skus)}")

    open_status = open_browser(args, skill_dir)
    if open_status:
        return open_status
    if not args.reuse_session and not args.keep_session_open:
        atexit.register(close_browser_session, args.session, skill_dir)

    alias_map = resolve_aliases(source_skus, alias_dir, output_dir, args, skill_dir)
    units, group_units = build_fetch_plan(selected, grouped_rows, alias_map)
    fetch_queue = {
        "generated_at": utc_now(),
        "unit_count": len(units),
        "units": list(units.values()),
    }
    write_json(output_dir / "fetch_queue.json", fetch_queue)
    print_progress(f"Fetch queue saved: {output_dir / 'fetch_queue.json'} ({len(units)} unit(s))")

    fetched_by_key: dict[str, dict] = {}
    summary = []
    for ordinal, unit in enumerate(units.values(), start=1):
        raw = fetch_pdp_unit(ordinal, unit, pdp_dir, args, skill_dir)
        fetched_by_key[unit["fetch_key"]] = raw

    for group_index, group in selected:
        group_raw = build_group_raw(
            group_index,
            group,
            grouped_rows.get(group_key_from_group(group), []),
            group_units.get(group_index, {}),
            fetched_by_key,
            alias_map,
            raw_dir,
        )
        product = group_raw.get("product") or {}
        summary.append(
            {
                "group_index": group_index,
                "sku_name": group_raw.get("sku_name", ""),
                "spu_name": group_raw.get("spu_name", ""),
                "source_group_key": group_raw.get("source_group_key", ""),
                "source_jcp_prefix": group_raw.get("source_jcp_prefix", ""),
                "request_sku": group_raw.get("request_sku", ""),
                "ok": bool(group_raw.get("ok")) and not group_raw.get("error"),
                "resolution_status": group_raw.get("resolution_status", ""),
                "source_ppids": group_raw.get("source_ppids", []),
                "pdp_fetch_count": group_raw.get("pdp_fetch_count", 0),
                "variant_count": group_raw.get("variant_count", 0),
                "warning_count": group_raw.get("warning_count", 0),
                "product_id": product.get("product_id", ""),
                "web_id": product.get("web_id", ""),
                "product_name": product.get("name", ""),
                "current_url": group_raw.get("current_url", ""),
                "raw_path": group_raw.get("raw_path", ""),
                "message": group_raw.get("message", ""),
            }
        )
        print_progress(
            f"[group {group_index}] {group_raw.get('resolution_status')} "
            f"fetches={group_raw.get('pdp_fetch_count', 0)} variants={group_raw.get('variant_count', 0)}"
        )

    summary_path = output_dir / "scrape_summary.json"
    write_json(summary_path, summary)
    print_progress(f"Summary saved: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
