---
name: pinterest-search-pins
description: "Scrape Pinterest search-result image pins with browser-act using a logged-in local Chrome browser. Use when the user needs parameterized Pinterest keyword scraping with pin detail enrichment, including descriptions, image metadata, creator data, destinations, and visible engagement counts while excluding comment text."
metadata:
  author: Shinebed
  version: "0.1.0"
  requires:
    browser-auto-shinebed: ">=0.1.6"
    runtime: "Python 3.12, uv package manager, browser-act via browser-auto-shinebed, local Chrome"
  data-privacy:
    local-only: "Runs in the user's selected local Chrome browser. Login credentials must not be passed to the script or stored in Skill files."
---

# Pinterest Search Pins Scraper

## Objective

Scrape a requested number of image pins from a Pinterest keyword search using a logged-in local Chrome browser. Enrich each result from its pin detail page without collecting comment text.

## Parameters

- `--keyword` (required): Pinterest search keyword, for example `Bedding Sheets`.
- `--count` (required): Number of pin posts to collect, for example `200`.
- `--detail-concurrency` (optional): Concurrent pin detail fetches. Default `3`; maximum `8`.

## Pre-Execution Checks

1. Confirm that the Shinebed wrapper owns the `browser-act` command:

```bash
browser-act doctor
```

If the command is unavailable or the wrapper check fails, install or update it:

```bash
uv tool install --force --refresh browser-auto-shinebed==0.1.6 --python 3.12
browser-act doctor
```

2. List browsers and choose a `type=chrome` local browser record:

```bash
browser-act browser list
```

If several local Chrome records exist and none is clearly intended for Pinterest, ask the user which browser id to use. Do not place browser ids or profile ids in this Skill.

3. Open Pinterest in headed mode so the user can complete login or verification manually when needed:

```bash
browser-act --session pinterest-search browser open {chrome-browser-id} "https://www.pinterest.com/search/pins/?q={url-encoded-keyword}&rs=filter" --headed
browser-act --session pinterest-search wait stable --timeout 60000
```

Use an existing Pinterest login session. Never request, save, or pass Pinterest credentials on the command line. If the script reports `login_required: true`, ask the user to log in in the visible Chrome window, then rerun it.

## Run

Generate browser-side JavaScript and pipe it to `browser-act`:

```bash
python scripts/scrape-pinterest-pins.py --keyword "Bedding Sheets" --count 200 \
  | browser-act --session pinterest-search eval --stdin
```

PowerShell:

```powershell
python .\scripts\scrape-pinterest-pins.py --keyword "Bedding Sheets" --count 200 |
  browser-act --session pinterest-search eval --stdin
```

The eval result is a JSON string. Parse it before saving when the caller needs structured JSON rather than the CLI result envelope.

## Output

Top-level fields include `ok`, `keyword`, `requested_count`, `collected_count`, `enriched_count`, `source_url`, `logged_in_hint`, and `pins`.

Each item in `pins` may include:

- Pin identity: `id`, `url`, `title`, `description`, `detail_description`.
- Image data: `image_url`, `image_alt`, `image_width`, `image_height`.
- Attribution and destination: `domain`, `link`, `pinner_name`, `pinner_username`, `creator_name`.
- Engagement counts: `like_count`, `comment_count`, `share_count`, `repin_count`, `save_count`.
- Detail status: `detail_found`, `detail_error`.

The Skill intentionally excludes comment text. It captures only comment counts when Pinterest exposes them in the pin detail payload.

## Success Criteria

- The helper returns `ok: true`.
- `collected_count` equals `requested_count`, unless Pinterest stops loading new results.
- `pins` contains unique numeric pin ids and the requested keyword.
- Detail failures remain in the output with `detail_found: false` and a diagnostic `detail_error`.
- Close the owned session after saving or returning the result:

```bash
browser-act session close pinterest-search
```

## Known Limitations

- Pinterest can change its waterfall DOM and embedded pin-detail payloads. Re-explore the page if collection or enrichment drops sharply.
- Some pins may be deleted, promoted-only, unavailable, or missing an extractable detail payload.
- Keep the browser visible during the run; this workflow is designed for local Chrome headed mode and an existing user login session.
