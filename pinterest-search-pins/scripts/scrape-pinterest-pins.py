#!/usr/bin/env python3
"""Emit browser-side JavaScript for scraping Pinterest search pins.

This script is intentionally small and side-effect free: it prints JavaScript for
`browser-act ... eval --stdin`. The generated JavaScript runs in the selected
local Chrome browser and returns one JSON string.
"""

from __future__ import annotations

import argparse
import json
import sys


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("count must be an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("count must be greater than 0")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Pinterest search-pin scraping JavaScript for browser-act."
    )
    parser.add_argument("--keyword", required=True, help="Pinterest search keyword.")
    parser.add_argument("--count", required=True, type=positive_int, help="Pin count to collect.")
    parser.add_argument(
        "--detail-concurrency",
        default=3,
        type=positive_int,
        help="Concurrent pin detail fetches.",
    )
    args = parser.parse_args()

    keyword = json.dumps(args.keyword)
    count = args.count
    detail_concurrency = max(1, min(args.detail_concurrency, 8))

    js = f"""
(async () => {{
  const keyword = {keyword};
  const targetCount = {count};
  const detailConcurrency = {detail_concurrency};
  const origin = 'https://www.pinterest.com';
  const searchUrl = origin + '/search/pins/?q=' + encodeURIComponent(keyword) + '&rs=filter';

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const cleanText = (value) => (value || '').replace(/\\s+/g, ' ').trim();

  async function waitForPageReady(timeoutMs = 30000) {{
    const started = Date.now();
    while (Date.now() - started < timeoutMs) {{
      if (document.readyState === 'complete' || document.readyState === 'interactive') {{
        return true;
      }}
      await sleep(250);
    }}
    return false;
  }}

  async function navigateToSearch() {{
    const current = new URL(location.href);
    const currentQ = current.searchParams.get('q') || '';
    if (!current.pathname.startsWith('/search/pins/') || currentQ !== keyword) {{
      location.href = searchUrl;
    }}
    await waitForPageReady(45000);
    await sleep(2500);
  }}

  function loginRequired() {{
    const emailInput = document.querySelector('input[name="id"], input[type="email"], #email, #streamlined-login-email');
    const passwordInput = document.querySelector('input[name="password"], input[type="password"], #password, #streamlined-login-password');
    return Boolean(emailInput && passwordInput);
  }}

  function pinIdFromHref(href) {{
    const match = String(href || '').match(/\\/pin\\/(\\d+)/);
    return match ? match[1] : '';
  }}

  function bestImageFromAnchor(anchor) {{
    const images = Array.from(anchor.querySelectorAll('img'));
    let best = null;
    for (const image of images) {{
      const src = image.currentSrc || image.src || image.getAttribute('src') || '';
      if (!src || src.startsWith('data:')) continue;
      const width = image.naturalWidth || image.width || 0;
      const height = image.naturalHeight || image.height || 0;
      if (!best || width * height > best.width * best.height) {{
        best = {{
          url: src,
          alt: cleanText(image.getAttribute('alt') || ''),
          width,
          height
        }};
      }}
    }}
    return best || {{ url: '', alt: '', width: 0, height: 0 }};
  }}

  function cardText(anchor) {{
    const card = anchor.closest('[data-test-id], [role="listitem"], div');
    const titleNode = card ? Array.from(card.querySelectorAll('[title], h1, h2, h3, span, div')).find((node) => {{
      const text = cleanText(node.getAttribute('title') || node.textContent || '');
      return text && text.length > 2 && text.length < 220 && !/save|\\u4fdd\\u5b58|more|\\u66f4\\u591a/i.test(text);
    }}) : null;
    return cleanText(
      (titleNode && (titleNode.getAttribute('title') || titleNode.textContent)) ||
      anchor.getAttribute('aria-label') ||
      anchor.getAttribute('title') ||
      ''
    );
  }}

  function collectVisiblePins(seen) {{
    const anchors = Array.from(document.querySelectorAll('a[href*="/pin/"]'));
    for (const anchor of anchors) {{
      const href = anchor.href || anchor.getAttribute('href') || '';
      const id = pinIdFromHref(href);
      if (!id || seen.has(id)) continue;
      const image = bestImageFromAnchor(anchor);
      const title = cardText(anchor) || image.alt;
      seen.set(id, {{
        id,
        url: origin + '/pin/' + id + '/',
        title,
        description: '',
        image_url: image.url,
        image_alt: image.alt,
        image_width: image.width,
        image_height: image.height,
        search_keyword: keyword
      }});
    }}
    return seen;
  }}

  async function collectSearchPins() {{
    const seen = new Map();
    window.scrollTo(0, 0);
    await sleep(1200);
    collectVisiblePins(seen);
    let stableRounds = 0;
    let lastSize = seen.size;
    const maxScrolls = Math.max(80, Math.ceil(targetCount / 3) + 30);
    for (let i = 0; i < maxScrolls && seen.size < targetCount; i++) {{
      window.scrollBy(0, Math.max(900, Math.floor(window.innerHeight * 0.9)));
      await sleep(900 + Math.min(i * 10, 500));
      collectVisiblePins(seen);
      if (seen.size === lastSize) {{
        stableRounds += 1;
      }} else {{
        stableRounds = 0;
        lastSize = seen.size;
      }}
      if (stableRounds >= 12) break;
    }}
    return Array.from(seen.values()).slice(0, targetCount);
  }}

  function walk(value, visitor) {{
    const stack = [value];
    const seen = new Set();
    while (stack.length) {{
      const current = stack.pop();
      if (!current || typeof current !== 'object' || seen.has(current)) continue;
      seen.add(current);
      visitor(current);
      if (Array.isArray(current)) {{
        for (const item of current) stack.push(item);
      }} else {{
        for (const item of Object.values(current)) stack.push(item);
      }}
    }}
  }}

  function extractJsonObjects(html) {{
    const docs = [];
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    for (const script of Array.from(doc.querySelectorAll('script'))) {{
      const type = script.getAttribute('type') || '';
      const text = script.textContent || '';
      if (!text.trim()) continue;
      if (type.includes('json') || text.includes('PinResource') || text.includes('"aggregated_stats"')) {{
        const candidates = [];
        if (text.trim().startsWith('{{') || text.trim().startsWith('[')) {{
          candidates.push(text.trim());
        }}
        const match = text.match(/\\{{"props":.*\\}}/s);
        if (match) candidates.push(match[0]);
        for (const candidate of candidates) {{
          try {{
            docs.push(JSON.parse(candidate));
          }} catch (_) {{}}
        }}
      }}
    }}
    return docs;
  }}

  function findPinRecord(root, pinId) {{
    let best = null;
    walk(root, (node) => {{
      if (best) return;
      const id = String(node.id || node.pin_id || node.grid_title_pin_id || '');
      const resourceName = String(node.resource_name || node.name || '');
      if (id === String(pinId) && (
        node.aggregated_stats ||
        node.closeup_description ||
        node.description ||
        node.comment_count !== undefined ||
        resourceName.includes('PinResource')
      )) {{
        best = node;
      }}
    }});
    return best;
  }}

  function numberFrom(value) {{
    if (value === null || value === undefined || value === '') return 0;
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    const text = String(value).trim().toLowerCase().replace(/,/g, '');
    const match = text.match(/([0-9]+(?:\\.[0-9]+)?)([kmb])?/);
    if (!match) return 0;
    const base = Number(match[1]);
    const mult = match[2] === 'k' ? 1000 : match[2] === 'm' ? 1000000 : match[2] === 'b' ? 1000000000 : 1;
    return Math.round(base * mult);
  }}

  function firstString(...values) {{
    for (const value of values) {{
      const text = cleanText(value);
      if (text) return text;
    }}
    return '';
  }}

  function bestImageFromPin(pin) {{
    const images = pin.images || pin.image || {{}};
    const candidates = [];
    walk(images, (node) => {{
      if (node.url) candidates.push(String(node.url));
    }});
    return candidates.find((url) => /pinimg\\.com/.test(url)) || candidates[0] || '';
  }}

  function normalizeDetail(pin, base) {{
    const stats = pin.aggregated_stats || {{}};
    const reactionCounts = pin.reaction_counts || {{}};
    const likeCount = Object.values(reactionCounts).reduce((sum, value) => sum + numberFrom(value), 0);
    const pinner = pin.pinner || pin.owner || pin.user || {{}};
    const creator = pin.native_creator || pin.creator || {{}};
    const detailImage = bestImageFromPin(pin);
    return {{
      ...base,
      title: firstString(base.title, pin.title, pin.grid_title, pin.rich_summary?.display_name),
      description: firstString(base.description, pin.description, pin.grid_description),
      detail_description: firstString(pin.closeup_description, pin.description, pin.grid_description, base.description),
      image_url: base.image_url || detailImage,
      image_alt: firstString(base.image_alt, pin.alt_text, pin.image_signature),
      domain: firstString(pin.domain, pin.link_domain?.official_name, pin.rich_summary?.site_name),
      link: firstString(pin.link, pin.link_url, pin.rich_summary?.url),
      pinner_name: firstString(pinner.full_name, pinner.name),
      pinner_username: firstString(pinner.username),
      creator_name: firstString(creator.full_name, creator.name, creator.username),
      like_count: likeCount,
      comment_count: numberFrom(pin.comment_count ?? stats.comment_count ?? stats.comments),
      share_count: numberFrom(pin.share_count ?? stats.share_count ?? stats.shares),
      repin_count: numberFrom(pin.repin_count ?? stats.repin_count ?? stats.repins),
      save_count: numberFrom(pin.save_count ?? stats.saves ?? stats.save_count),
      detail_found: true,
      detail_error: ''
    }};
  }}

  async function fetchPinDetail(base) {{
    if (!base.id) {{
      return {{ ...base, detail_found: false, detail_error: 'missing id' }};
    }}
    const pinUrl = origin + '/pin/' + base.id + '/';
    for (let attempt = 1; attempt <= 3; attempt++) {{
      try {{
        const response = await fetch(pinUrl, {{
          credentials: 'include',
          headers: {{ accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' }}
        }});
        if (!response.ok) throw new Error('HTTP ' + response.status);
        const html = await response.text();
        for (const root of extractJsonObjects(html)) {{
          const record = findPinRecord(root, base.id);
          if (record) return normalizeDetail(record, base);
        }}
        return {{ ...base, detail_found: false, detail_error: 'pin detail payload not found' }};
      }} catch (error) {{
        if (attempt === 3) {{
          return {{ ...base, detail_found: false, detail_error: String(error && error.message || error) }};
        }}
        await sleep(600 * attempt);
      }}
    }}
    return {{ ...base, detail_found: false, detail_error: 'unknown detail error' }};
  }}

  async function enrichPins(pins) {{
    const output = new Array(pins.length);
    let cursor = 0;
    const workers = Array.from({{ length: Math.min(detailConcurrency, pins.length) }}, async () => {{
      while (cursor < pins.length) {{
        const index = cursor++;
        output[index] = await fetchPinDetail(pins[index]);
      }}
    }});
    await Promise.all(workers);
    return output;
  }}

  try {{
    await navigateToSearch();
    if (loginRequired()) {{
      return JSON.stringify({{
        ok: false,
        login_required: true,
        message: 'Pinterest login is required. Log in manually in the visible Chrome window, then run the scraper again.'
      }});
    }}
    const pins = await collectSearchPins();
    const enrichedPins = await enrichPins(pins);
    return JSON.stringify({{
      ok: true,
      keyword,
      requested_count: targetCount,
      collected_count: pins.length,
      enriched_count: enrichedPins.filter((pin) => pin.detail_found).length,
      source_url: searchUrl,
      logged_in_hint: true,
      pins: enrichedPins
    }});
  }} catch (error) {{
    return JSON.stringify({{
      ok: false,
      keyword,
      requested_count: targetCount,
      message: String(error && error.message || error),
      stack: String(error && error.stack || '')
    }});
  }}
}})()
""".strip()

    sys.stdout.write(js)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
