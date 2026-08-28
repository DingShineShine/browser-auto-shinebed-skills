---
name: tiktok-video-comments-scrape
description: "TikTok video comment scraping through browser-act chrome-direct mode and TikTok web comment APIs. Use this skill when the user asks to scrape, collect, export, download, paginate, or save all visible comments and replies for a TikTok video URL using an already logged-in Chrome session. Outputs JSON comment data and can be saved to CSV by the caller."
metadata:
  requires:
    browser-auto-shinebed: ">=0.1.6"
    runtime: "Python 3.12, uv package manager, browser-act via browser-auto-shinebed"
---

# TikTok - Video Comments Scrape

## Language

Reply in the user's language.

## Objective

Scrape all visible TikTok video comments and replies through `browser-act` using the user's logged-in `chrome-direct` browser session.

## Prerequisites

- Target page pattern: `https://www.tiktok.com/@{user}/video/{videoId}`.
- Login or account state: required for reliable comment access. Visible confirmation is that the TikTok sidebar shows logged-in navigation such as Messages, Activity, Upload, or the user's profile controls.
- Browser runtime: use `browser-act` through the `browser-auto-shinebed` wrapper.
- Wrapper dependency: install or update `browser-auto-shinebed >= 0.1.6` before using this Skill.
- Browser mode: default to an existing `type=chrome-direct` browser record from `browser-act browser list`. Do not use `chrome`, `stealth`, or `adspower:{user_id}` unless the user explicitly overrides this skill's chrome-direct default.
- Direct mode impact: `chrome-direct` occupies the user's running Chrome while the task is active.

## Parameters

- `--video-url`: optional TikTok video URL. If omitted, the script uses the current browser page URL.
- `--video-id`: optional TikTok video id. Use this when automatic parsing from URL fails.
- `--main-count`: optional top-level comment page size. Default `20`, valid range `1` to `50`.
- `--reply-count`: optional reply page size. Default `50`, valid range `1` to `50`.
- `--max-main-pages`: optional top-level comment page safety cap. Default `250`.
- `--max-reply-pages`: optional reply page safety cap per parent comment. Default `50`.
- `--delay-ms`: optional pause between browser-side API requests. Default `160`.
- `--region`: optional TikTok request region hint. Default `US`.
- `--skip-replies`: optional. Return only top-level comments.
- `--omit-raw`: optional. Omit the original TikTok API payload from each comment for smaller files.

## Pre-Execution Checks

1. Confirm `browser-act` is available:

```bash
browser-act doctor
```

If `browser-act doctor` is unavailable or reports that `browser-act` is not owned by `browser-auto-shinebed`, install the wrapper first:

```bash
uv tool install --force --refresh browser-auto-shinebed==0.1.6 --python 3.12
browser-act doctor
```

2. List browser records and choose the existing `type=chrome-direct` browser id:

```bash
browser-act browser list
```

If there is no `type=chrome-direct` browser, follow the `browser-act get-skills advanced` chrome-direct creation Confirmation Gate before creating one. If there are multiple plausible direct sessions or the direct browser purpose is unclear, ask the user which browser id to use.

3. Open the TikTok video in chrome-direct mode and wait for the page to load:

```bash
browser-act --session tiktok-comments browser open {chrome-direct-browser-id} "{video-url}"
browser-act --session tiktok-comments wait stable --timeout 60000
```

4. Confirm comments are available and the user is logged in:

```bash
browser-act --session tiktok-comments state
```

5. Run a small sample scrape:

```bash
browser-act --session tiktok-comments eval "$(python scripts/scrape-comments.py --video-url "{video-url}" --max-main-pages 1 --skip-replies --omit-raw)"
```

PowerShell form:

```powershell
$js = python scripts/scrape-comments.py --video-url "{video-url}" --max-main-pages 1 --skip-replies --omit-raw
browser-act --session tiktok-comments eval "$js"
```

The sample should return `ok: true`, a parsed `video_id`, `main_comment_count` greater than zero for videos with comments, and `templates_found.main: true` when TikTok has already loaded its comment API request.

## Capability Components

### API: Scrape All Visible Comments And Replies

Command:

```bash
browser-act --session tiktok-comments eval "$(python scripts/scrape-comments.py --video-url "{video-url}")"
```

PowerShell form:

```powershell
$js = python scripts/scrape-comments.py --video-url "{video-url}"
browser-act --session tiktok-comments eval "$js"
```

Save the JSON output when the task asks for a file:

```powershell
browser-act --session tiktok-comments eval "$(python scripts/scrape-comments.py --video-url "{video-url}")" |
  Set-Content -Path "output\tiktok_comments_{videoId}.json" -Encoding utf8
```

Output example:

```json
{
  "ok": true,
  "source_url": "https://www.tiktok.com/@example/video/7000000000000000000",
  "video_id": "7000000000000000000",
  "browser_mode_default": "chrome-direct",
  "reported_total": 120,
  "main_comment_count": 80,
  "parents_with_replies": 18,
  "expected_reply_count_from_main": 40,
  "scraped_reply_count": 38,
  "combined_comment_count": 118,
  "main_pages": [
    {
      "requested_cursor": 0,
      "requested_count": 20,
      "next_cursor": 20,
      "has_more": 1,
      "count": 20,
      "total": 120
    }
  ],
  "reply_pages": [
    {
      "parent_cid": "7000000000000000001",
      "requested_cursor": 0,
      "requested_count": 50,
      "next_cursor": 3,
      "has_more": 0,
      "count": 3,
      "total": 3
    }
  ],
  "comments": [
    {
      "sequence": 1,
      "kind": "main",
      "cid": "7000000000000000001",
      "parent_cid": null,
      "text": "Example comment",
      "create_time_iso": "2026-06-05T00:00:00.000Z",
      "digg_count": 10,
      "reply_comment_total": 3,
      "user_unique_id": "example_user",
      "user_nickname": "Example User"
    }
  ]
}
```

### API: Scrape Top-Level Comments Only

Use this when the user only needs parent comments and wants a faster run.

Command:

```bash
browser-act --session tiktok-comments eval "$(python scripts/scrape-comments.py --video-url "{video-url}" --skip-replies)"
```

PowerShell form:

```powershell
$js = python scripts/scrape-comments.py --video-url "{video-url}" --skip-replies
browser-act --session tiktok-comments eval "$js"
```

### Network Capture: Verify Endpoint If Needed

Use network capture when the helper returns `ok: false`, `templates_found.main: false`, or TikTok changes its signing behavior. Keep the session in `chrome-direct` mode unless the user explicitly overrides this skill's default.

1. `navigate "{video-url}"`
2. `wait stable --timeout 60000`
3. Open or scroll the comments panel so TikTok loads comments.
4. `network requests --type xhr,fetch --filter /api/comment/list/`
5. `network request <id>`

Endpoint characteristics:

- Top-level comments: `https://www.tiktok.com/api/comment/list/`
- Replies: `https://www.tiktok.com/api/comment/list/reply/`

Expected stable request characteristics:

- Business identifiers: `aweme_id` or `item_id` for the video, and `comment_id` for replies.
- Pagination: `cursor`, `count`, `has_more`, and next `cursor`.
- Browser/session fields: `device_id`, `odinId`, browser language, screen size, timezone, and login state may be present.
- Signature fields such as `X-Dynosaur`, `X-Bogus`, `X-Gnarly`, and `msToken` are one-use request decorations. The helper strips stale signature fields and lets TikTok's page-side code sign new requests.

## Enum Parameters

- `[API]` Comment scope: full comments with replies by default, or `--skip-replies` for top-level only.
- `[API]` Raw payload: included by default, or `--omit-raw` for smaller output.
- `[API]` Region hint: `--region`, default `US`. Use the logged-in account's visible region only when the user has a specific reason to override it.

## Pagination

API cursor pagination is verified. The helper requests top-level comments until `has_more` is false, an empty page is returned, the cursor stops advancing, or `--max-main-pages` is reached. For each parent comment with `reply_comment_total > 0`, it requests reply pages until `has_more` is false, an empty page is returned, the cursor stops advancing, or `--max-reply-pages` is reached.

## Success Criteria

- The helper returns `ok: true`.
- `main_comment_count` is non-zero for videos with visible comments.
- `combined_comment_count` equals the length of `comments`.
- Every returned item has `kind`, `cid`, `text`, `create_time_iso`, and user identity fields when TikTok provides them.
- `reply_pages` end with `has_more: 0` for completed reply pagination, unless an intentional page cap was used.
- Close the owned browser-act session at the end:

```bash
browser-act session close tiktok-comments
```

## Known Limitations

- TikTok's displayed total can include hidden, deleted, filtered, or otherwise unavailable comments. API `total` values may exceed the number of visible records actually returned by the logged-in browser session.
- The helper depends on TikTok web's current comment API and page-side request signing behavior. If TikTok stops signing browser-side `fetch` calls, use Network Capture to refresh the approach.
- Data access is limited to comments and replies visible to the logged-in Chrome account.
- Long videos with very large comment sections may require increasing `--max-main-pages`, `--max-reply-pages`, or `--delay-ms`.

## Experience Notes

Path: `browser-act-skill-forge-memories/tiktok-video-comments-scrape-comments.memory.md`

Read the file before execution if it exists. Append only unexpected execution discoveries, not task results.
