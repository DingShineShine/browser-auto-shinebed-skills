import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SOURCE_JSON = BASE_DIR / "source_rows.json"
RAW_DIR = BASE_DIR / "raw"
ALIAS_MAP_JSON = BASE_DIR / "alias_map.json"
FETCH_QUEUE_JSON = BASE_DIR / "fetch_queue.json"
OUTPUT_JSON = BASE_DIR / "workbook_data.json"


VARIANT_FIELDS = [
    "sku_id",
    "web_id",
    "product_id",
    "product_name",
    "brand",
    "lot_id",
    "color",
    "color_family",
    "color_option_id",
    "size",
    "primary_barcode",
    "secondary_barcode",
    "itsa_status",
    "source",
    "has_inventory",
    "atp",
    "inventory_atp",
    "inventory_quality",
    "offering_status",
    "actual_sku_id",
    "marketing_label",
    "original_price_min",
    "original_price_max",
    "sale_price_min",
    "sale_price_max",
    "sale_percent_off_min",
    "sale_percent_off_max",
    "coupon_code",
    "coupon_price_min",
    "coupon_price_max",
    "pricing_inventory",
    "ship_to_home_status",
    "bopus_status",
    "my_alert_indicator",
    "image_url",
    "swatch_url",
    "offering_url",
]


SOURCE_MATCH_COLUMNS = [
    "source_row",
    "source_sku",
    "seller_sku",
    "crawl_sku",
    "sku_name",
    "jcp_prefix",
    "match_status",
    "request_sku_original",
    "request_sku_used",
    "group_source_sku_count",
    "resolution_status",
    "pdp_fetch_keys",
    "alias_status",
    "alias_ppid",
    "alias_pdp_url",
    "alias_selected_sku_id",
    "alias_id",
    "alias_http_status",
    "alias_message",
    *VARIANT_FIELDS,
    "scraped_at",
    "current_url",
    "raw_file",
    "group_note",
]


SCRAPED_VARIANT_COLUMNS = [
    "sku_name",
    "jcp_prefix",
    "request_sku_used",
    "source_match_status",
    "matched_source_rows",
    "matched_source_skus",
    "matched_seller_skus",
    "resolution_status",
    "source_ppids",
    "pdp_fetch_keys",
    *VARIANT_FIELDS,
    "scraped_at",
    "current_url",
    "raw_file",
]


GROUP_SUMMARY_COLUMNS = [
    "group_index",
    "sku_name",
    "jcp_prefix",
    "source_sku_count",
    "unique_source_sku_count",
    "request_sku_original",
    "request_sku_used",
    "resolution_status",
    "ppid_count",
    "source_ppids",
    "pdp_fetch_count",
    "pdp_fetch_keys",
    "alias_ok_count",
    "alias_failed_count",
    "scrape_ok",
    "status",
    "fetched_variant_count",
    "matched_source_row_count",
    "matched_unique_sku_count",
    "missing_source_row_count",
    "missing_unique_sku_count",
    "extra_variant_count",
    "coverage_rate",
    "warning_count",
    "product_id",
    "web_id",
    "product_name",
    "current_url",
    "raw_file",
    "notes",
]


ALIAS_MAP_COLUMNS = [
    "source_sku",
    "source_row_count",
    "source_rows",
    "source_sku_names",
    "source_prefixes",
    "source_seller_skus",
    "alias_status",
    "alias_ppid",
    "alias_pdp_url",
    "alias_selected_sku_id",
    "alias_id",
    "alias_http_status",
    "alias_message",
    "resolved_at",
    "alias_url",
]


WARNING_COLUMNS = [
    "group_index",
    "sku_name",
    "jcp_prefix",
    "request_sku_used",
    "warning_index",
    "warning",
    "raw_file",
]


RUN_INFO_COLUMNS = ["field", "value"]


def as_text(value) -> str:
    return "" if value is None else str(value)


def configure_paths(base_dir: Path, output_json: Path | None = None) -> None:
    global BASE_DIR, SOURCE_JSON, RAW_DIR, ALIAS_MAP_JSON, FETCH_QUEUE_JSON, OUTPUT_JSON
    BASE_DIR = base_dir
    SOURCE_JSON = BASE_DIR / "source_rows.json"
    RAW_DIR = BASE_DIR / "raw"
    ALIAS_MAP_JSON = BASE_DIR / "alias_map.json"
    FETCH_QUEUE_JSON = BASE_DIR / "fetch_queue.json"
    OUTPUT_JSON = output_json or BASE_DIR / "workbook_data.json"


def join_values(values) -> str:
    return ";".join(as_text(value) for value in values if as_text(value) != "")


def trim_warning(value, limit=800) -> str:
    text = as_text(value).replace("\r", " ").replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def raw_path_for_group(index: int) -> Path | None:
    matches = sorted(RAW_DIR.glob(f"{index:02d}-*.json"))
    return matches[-1] if matches else None


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_optional_json(path: Path):
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except Exception:
        return {}


def load_alias_map() -> tuple[dict[str, dict], dict]:
    payload = read_optional_json(ALIAS_MAP_JSON)
    aliases = payload.get("aliases") if isinstance(payload, dict) else {}
    if isinstance(aliases, list):
        aliases = {as_text(alias.get("input_sku_id")): alias for alias in aliases if alias.get("input_sku_id")}
    if not isinstance(aliases, dict):
        aliases = {}
    return aliases, payload if isinstance(payload, dict) else {}


def load_fetch_queue() -> dict:
    payload = read_optional_json(FETCH_QUEUE_JSON)
    return payload if isinstance(payload, dict) else {}


def group_row_key(row: dict) -> tuple[str, str]:
    return (as_text(row.get("sku_name") or row.get("spu_name")), as_text(row.get("jcp_prefix") or row.get("sku_prefix")))


def alias_columns(alias: dict | None, fallback_status: str = "") -> dict:
    alias = alias or {}
    return {
        "alias_status": as_text(alias.get("alias_status") or fallback_status),
        "alias_ppid": as_text(alias.get("ppId")),
        "alias_pdp_url": as_text(alias.get("pdpUrl")),
        "alias_selected_sku_id": as_text(alias.get("selectedSKUId")),
        "alias_id": as_text(alias.get("alias_id") or alias.get("id")),
        "alias_http_status": as_text(alias.get("http_status")),
        "alias_message": as_text(alias.get("message")),
    }


def alias_status_counts(aliases: list[dict]) -> Counter:
    return Counter(as_text(alias.get("alias_status")) for alias in aliases)


def failed_alias_count(counts: Counter) -> int:
    return sum(count for status, count in counts.items() if status != "ok")


def build_alias_map_rows(source_rows: list[dict], alias_map: dict[str, dict]) -> list[dict]:
    rows_by_sku: OrderedDict[str, list[dict]] = OrderedDict()
    for row in source_rows:
        sku = as_text(row.get("crawl_sku"))
        if sku:
            rows_by_sku.setdefault(sku, []).append(row)

    fallback_status = "not_resolved" if alias_map else "not_available"
    alias_rows = []
    for sku, rows in rows_by_sku.items():
        alias = alias_map.get(sku) or {}
        alias_rows.append(
            {
                "source_sku": sku,
                "source_row_count": len(rows),
                "source_rows": join_values(row.get("source_row") for row in rows),
                "source_sku_names": join_values(OrderedDict.fromkeys(as_text(row.get("sku_name") or row.get("spu_name")) for row in rows)),
                "source_prefixes": join_values(OrderedDict.fromkeys(as_text(row.get("jcp_prefix") or row.get("sku_prefix")) for row in rows)),
                "source_seller_skus": join_values(OrderedDict.fromkeys(as_text(row.get("seller_sku")) for row in rows)),
                **alias_columns(alias, fallback_status),
                "resolved_at": as_text(alias.get("resolved_at")),
                "alias_url": as_text(alias.get("alias_url")),
            }
        )
    return alias_rows


def status_for_group(ok: bool, matched_count: int, missing_count: int, warning_count: int) -> str:
    if not ok:
        return "failed"
    if missing_count and not matched_count:
        return "all_missing"
    if missing_count:
        return "partial_missing"
    if warning_count:
        return "ok_with_warnings"
    return "ok"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    parser = argparse.ArgumentParser(description="Build workbook_data.json from JCP source rows, raw PDP results, and alias map.")
    parser.add_argument("--base-dir", default=str(BASE_DIR), help="Directory containing source_rows.json, raw/, alias_map.json, and fetch_queue.json.")
    parser.add_argument("--output-json", default="", help="Optional output workbook_data.json path.")
    parser.add_argument("--browser-id", default="", help="Optional browser id to record in the Run Info sheet.")
    args = parser.parse_args()
    configure_paths(Path(args.base_dir).resolve(), Path(args.output_json).resolve() if args.output_json else None)

    source = read_json(SOURCE_JSON)
    source_rows = source["rows"]
    groups = source["groups"]
    alias_map, alias_meta = load_alias_map()
    fetch_queue = load_fetch_queue()

    rows_by_group = {}
    rows_by_group_sku = {}
    for row in source_rows:
        key = group_row_key(row)
        rows_by_group.setdefault(key, []).append(row)
        rows_by_group_sku.setdefault((*key, as_text(row["crawl_sku"])), []).append(row)

    group_summary = []
    alias_map_rows = build_alias_map_rows(source_rows, alias_map)
    source_match_rows = []
    scraped_variant_rows = []
    warning_rows = []
    seen_source_rows = set()

    for index, group in enumerate(groups, start=1):
        sku_name = as_text(group.get("sku_name") or group.get("spu_name"))
        prefix = as_text(group.get("jcp_prefix") or group.get("sku_prefix"))
        key = (sku_name, prefix)
        group_source_rows = rows_by_group.get(key, [])

        raw_path = raw_path_for_group(index)
        raw = (
            read_json(raw_path)
            if raw_path
            else {
                "ok": False,
                "error": True,
                "message": "No raw JSON file found for group.",
                "variants": [],
                "warnings": [],
            }
        )

        variants = raw.get("variants") or []
        warnings = raw.get("warnings") or []
        product = raw.get("product") or {}
        request_sku_used = as_text(raw.get("request_sku") or group.get("request_sku"))
        request_sku_original = as_text(group.get("request_sku"))
        raw_file = str(raw_path) if raw_path else ""
        ok = bool(raw.get("ok")) and not raw.get("error")
        resolution = as_text(raw.get("resolution_status"))
        source_ppids = [as_text(value) for value in (raw.get("source_ppids") or []) if as_text(value)]
        pdp_fetch_keys = [as_text(value) for value in (raw.get("pdp_fetch_keys") or []) if as_text(value)]
        raw_aliases = raw.get("aliases") or []
        aliases_by_sku = {
            as_text(alias.get("input_sku_id")): alias
            for alias in raw_aliases
            if alias.get("input_sku_id")
        }
        group_aliases = [
            aliases_by_sku.get(as_text(row["crawl_sku"])) or alias_map.get(as_text(row["crawl_sku"])) or {}
            for row in group_source_rows
        ]
        group_alias_counts = Counter(raw.get("alias_status_counts") or {})
        if not group_alias_counts and group_aliases:
            group_alias_counts = alias_status_counts(group_aliases)

        source_skus = [as_text(row["crawl_sku"]) for row in group_source_rows]
        source_sku_set = set(source_skus)
        variant_by_sku = {}
        for variant in variants:
            sku_id = as_text(variant.get("sku_id"))
            if sku_id and sku_id not in variant_by_sku:
                variant_by_sku[sku_id] = variant

        variant_sku_set = set(variant_by_sku)
        matched_unique = sorted(source_sku_set & variant_sku_set)
        missing_unique = sorted(source_sku_set - variant_sku_set)
        extra_variants = sorted(variant_sku_set - source_sku_set)
        matched_source_row_count = sum(1 for row in group_source_rows if as_text(row["crawl_sku"]) in variant_sku_set)
        missing_source_row_count = len(group_source_rows) - matched_source_row_count
        warning_count = int(raw.get("warning_count") or len(warnings))
        coverage_rate = matched_source_row_count / len(group_source_rows) if group_source_rows else 0

        notes = []
        if request_sku_used and request_sku_used != request_sku_original:
            notes.append(f"Request SKU changed from {request_sku_original} to {request_sku_used}.")
        if resolution == "multiple_ppids":
            notes.append("Multiple ppIds were resolved inside this SKU name + prefix group.")
        elif resolution == "alias_unresolved":
            notes.append("No source SKU in this group resolved to a product-aliases ppId.")
        if not ok:
            notes.append(as_text(raw.get("message") or "Scrape failed."))
        if missing_source_row_count:
            notes.append(f"{missing_source_row_count} source row(s) remain missing after exact sku_id match.")
        if extra_variants:
            notes.append(f"{len(extra_variants)} scraped variant SKU(s) were not in this source group.")
        product_web_id = as_text(product.get("web_id"))
        if product_web_id and prefix and product_web_id[:7] != prefix:
            notes.append(f"Fetched PDP web_id {product_web_id} does not start with requested prefix {prefix}.")
        if warning_count:
            notes.append("Warnings were captured during supplemental price/inventory API calls; see Warnings sheet.")

        for row in group_source_rows:
            source_row_id = row["source_row"]
            seen_source_rows.add(source_row_id)
            crawl_sku = as_text(row["crawl_sku"])
            variant = variant_by_sku.get(crawl_sku, {})
            alias = aliases_by_sku.get(crawl_sku) or alias_map.get(crawl_sku) or {}
            output_row = {
                "source_row": source_row_id,
                "source_sku": row.get("source_sku") or row.get("sku") or "",
                "seller_sku": row.get("seller_sku", ""),
                "crawl_sku": crawl_sku,
                "sku_name": sku_name,
                "jcp_prefix": prefix,
                "match_status": "matched" if variant else "missing_from_jcp_response",
                "request_sku_original": request_sku_original,
                "request_sku_used": request_sku_used,
                "group_source_sku_count": len(group_source_rows),
                "resolution_status": resolution,
                "pdp_fetch_keys": join_values(pdp_fetch_keys),
                **alias_columns(alias, "not_resolved" if alias_map else "not_available"),
                "scraped_at": raw.get("scraped_at", ""),
                "current_url": raw.get("current_url") or (raw.get("page_snapshot") or {}).get("href", ""),
                "raw_file": raw_file,
                "group_note": " | ".join(notes),
            }
            for field in VARIANT_FIELDS:
                output_row[field] = variant.get(field, "")
            source_match_rows.append(output_row)

        for variant in variants:
            sku_id = as_text(variant.get("sku_id"))
            matched_sources = rows_by_group_sku.get((*key, sku_id), [])
            output_row = {
                "sku_name": sku_name,
                "jcp_prefix": prefix,
                "request_sku_used": request_sku_used,
                "source_match_status": "matched" if matched_sources else "extra_not_in_source_group",
                "matched_source_rows": ";".join(as_text(row["source_row"]) for row in matched_sources),
                "matched_source_skus": ";".join(row.get("source_sku") or row.get("sku") or "" for row in matched_sources),
                "matched_seller_skus": ";".join(row.get("seller_sku", "") for row in matched_sources),
                "resolution_status": resolution,
                "source_ppids": join_values(source_ppids),
                "pdp_fetch_keys": join_values(pdp_fetch_keys),
                "scraped_at": raw.get("scraped_at", ""),
                "current_url": raw.get("current_url") or (raw.get("page_snapshot") or {}).get("href", ""),
                "raw_file": raw_file,
            }
            for field in VARIANT_FIELDS:
                output_row[field] = variant.get(field, "")
            scraped_variant_rows.append(output_row)

        group_summary.append(
            {
                "group_index": index,
                "sku_name": sku_name,
                "jcp_prefix": prefix,
                "source_sku_count": len(group_source_rows),
                "unique_source_sku_count": len(source_sku_set),
                "request_sku_original": request_sku_original,
                "request_sku_used": request_sku_used,
                "resolution_status": resolution,
                "ppid_count": len(source_ppids),
                "source_ppids": join_values(source_ppids),
                "pdp_fetch_count": int(raw.get("pdp_fetch_count") or len(pdp_fetch_keys)),
                "pdp_fetch_keys": join_values(pdp_fetch_keys),
                "alias_ok_count": int(group_alias_counts.get("ok", 0)),
                "alias_failed_count": failed_alias_count(group_alias_counts),
                "scrape_ok": ok,
                "status": status_for_group(ok, matched_source_row_count, missing_source_row_count, warning_count),
                "fetched_variant_count": len(variants),
                "matched_source_row_count": matched_source_row_count,
                "matched_unique_sku_count": len(matched_unique),
                "missing_source_row_count": missing_source_row_count,
                "missing_unique_sku_count": len(missing_unique),
                "extra_variant_count": len(extra_variants),
                "coverage_rate": coverage_rate,
                "warning_count": warning_count,
                "product_id": as_text(product.get("product_id") or raw.get("product_id")),
                "web_id": product_web_id,
                "product_name": as_text(product.get("name") or raw.get("product_name")),
                "current_url": raw.get("current_url") or (raw.get("page_snapshot") or {}).get("href", ""),
                "raw_file": raw_file,
                "notes": " | ".join(notes),
            }
        )

        for warning_index, warning in enumerate(warnings, start=1):
            warning_rows.append(
                {
                    "group_index": index,
                    "sku_name": sku_name,
                    "jcp_prefix": prefix,
                    "request_sku_used": request_sku_used,
                    "warning_index": warning_index,
                    "warning": trim_warning(warning),
                    "raw_file": raw_file,
                }
            )

    missing_source_entries = [row for row in source_rows if row["source_row"] not in seen_source_rows]
    for row in missing_source_entries:
        crawl_sku = as_text(row["crawl_sku"])
        alias = alias_map.get(crawl_sku) or {}
        source_match_rows.append(
            {
                "source_row": row["source_row"],
                "source_sku": row.get("source_sku") or row.get("sku") or "",
                "seller_sku": row.get("seller_sku", ""),
                "crawl_sku": crawl_sku,
                "sku_name": row.get("sku_name") or row.get("spu_name") or "",
                "jcp_prefix": row.get("jcp_prefix") or row.get("sku_prefix") or "",
                "match_status": "missing_source_group",
                "request_sku_original": "",
                "request_sku_used": "",
                "group_source_sku_count": "",
                "resolution_status": "",
                "pdp_fetch_keys": "",
                **alias_columns(alias, "not_resolved" if alias_map else "not_available"),
                "scraped_at": "",
                "current_url": "",
                "raw_file": "",
                "group_note": "Source row did not map to a generated SKU name + prefix group.",
                **{field: "" for field in VARIANT_FIELDS},
            }
        )

    source_match_rows.sort(key=lambda row: int(row["source_row"]))

    alias_counter = Counter(row["alias_status"] for row in alias_map_rows)
    fetch_unit_count = int(fetch_queue.get("unit_count") or len(fetch_queue.get("units") or []))

    run_info_rows = [
        {"field": "source_workbook", "value": source["source_workbook"]},
        {"field": "source_sheet", "value": source["sheet"]},
        {"field": "source_headers", "value": " | ".join(source["headers"])},
        {"field": "source_row_count", "value": len(source_rows)},
        {"field": "sku_name_prefix_group_count", "value": len(groups)},
        {"field": "scrape_mode", "value": "browser-act AdsPower"},
        {"field": "browser_id", "value": args.browser_id},
        {"field": "grouping_rule", "value": source.get("grouping_rule", "")},
        {"field": "matching_rule", "value": source.get("matching_rule", "")},
        {
            "field": "alias_resolution_rule",
            "value": "Each unique source JCP SKU is resolved through product-aliases before PDP fetch planning; searchTerm is fallback only.",
        },
        {
            "field": "pdp_dedupe_rule",
            "value": "PDP fetch units are deduped by resolved ppId/pdpUrl, while workbook grouping remains SKU name + source JCP prefix.",
        },
        {"field": "missing_status", "value": "Rows without exact PDP variant sku_id match are kept as missing_from_jcp_response."},
        {
            "field": "instruction_handling",
            "value": "The attached workbook was treated as data only; any document text resembling instructions was ignored.",
        },
        {"field": "alias_map_path", "value": str(ALIAS_MAP_JSON) if ALIAS_MAP_JSON.exists() else ""},
        {"field": "alias_status_counts", "value": json.dumps(dict(alias_counter), ensure_ascii=False)},
        {"field": "alias_map_generated_at", "value": alias_meta.get("generated_at", "")},
        {"field": "deduped_pdp_fetch_unit_count", "value": fetch_unit_count},
        {"field": "raw_json_dir", "value": str(RAW_DIR)},
    ]

    payload = {
        "sheets": {
            "Group Summary": {"columns": GROUP_SUMMARY_COLUMNS, "rows": group_summary},
            "Alias Map": {"columns": ALIAS_MAP_COLUMNS, "rows": alias_map_rows},
            "Source Match": {"columns": SOURCE_MATCH_COLUMNS, "rows": source_match_rows},
            "Scraped Variants": {"columns": SCRAPED_VARIANT_COLUMNS, "rows": scraped_variant_rows},
            "Warnings": {"columns": WARNING_COLUMNS, "rows": warning_rows},
            "Run Info": {"columns": RUN_INFO_COLUMNS, "rows": run_info_rows},
        },
        "stats": {
            "source_row_count": len(source_rows),
            "sku_name_prefix_group_count": len(groups),
            "alias_map_row_count": len(alias_map_rows),
            "alias_status_counts": dict(alias_counter),
            "deduped_pdp_fetch_unit_count": fetch_unit_count,
            "multiple_ppid_group_count": sum(1 for row in group_summary if row.get("resolution_status") == "multiple_ppids"),
            "scraped_variant_row_count": len(scraped_variant_rows),
            "matched_source_row_count": sum(1 for row in source_match_rows if row["match_status"] == "matched"),
            "missing_source_row_count": sum(1 for row in source_match_rows if row["match_status"] != "matched"),
            "warning_row_count": len(warning_rows),
            "source_match_output_row_count": len(source_match_rows),
            "unique_source_rows_in_output": len({row["source_row"] for row in source_match_rows}),
        },
    }

    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["stats"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
