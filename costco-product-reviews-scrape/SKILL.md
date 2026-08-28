---
name: costco-product-reviews-scrape
description: "Costco product review scraping through browser-act chrome mode and the Bazaarvoice review API. Use this skill when the user asks to scrape, collect, export, download, paginate, or save Costco Member Reviews for a Costco product URL or product id using a chrome browser record. Outputs complete JSON review data including ratings-only reviews, text reviews, reviewer metadata, helpful counts, and media URLs."
metadata:
  requires:
    browser-auto-shinebed: ">=0.1.6"
    runtime: "Python 3.12, uv package manager, browser-act via browser-auto-shinebed"
---

# Costco - Product Reviews Scrape

## Language

Reply in the user's language.

## Objective

Scrape all Costco Member Reviews for a Costco product by using `browser-act` chrome mode and the Bazaarvoice review data API through `browser-act eval`.

## Prerequisites

- Target page pattern: `https://www.costco.com/p/-/{slug}/{productId}` or another Costco product page with a Bazaarvoice review widget.
- Login or account state: not required for public product reviews. The visible confirmation is that the Costco product page loads and the rating summary or Member Reviews section is visible.
- Browser runtime: use `browser-act` through the `browser-auto-shinebed` wrapper.
- Wrapper dependency: install or update `browser-auto-shinebed >= 0.1.6` before using this Skill.
- Browser mode: default to a `type=chrome` browser record from `browser-act browser list`. Do not use `chrome-direct`, `stealth`, or `adspower:{user_id}` unless the user explicitly overrides this skill's chrome-mode default.

## Parameters

- `--product-url`: optional. Costco product URL. If omitted, the script uses the current browser page URL.
- `--product-id`: optional. Bazaarvoice/Costco product id. If omitted, the script uses `BV.swat_reviews.config.productId` or parses the last 8+ digit id from the product URL.
- `--reviews-mode`: optional. `all` by default. Use `text-only` to add the Bazaarvoice `isratingsonly:false` filter.
- `--limit`: optional. API page size. Default `100`; valid range is `1` to `100`.
- `--max-reviews`: optional. Default `0`, meaning no cap. Use a positive number for sampling or validation.
- `--sort`: optional. Default `relevancy:a1`, matching the observed Costco UI default.
- `--content-locales`: optional. Default `en_CA,fr_CA,en_US,en_US`, matching the observed Costco deployment.

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

2. List browser records and choose a `type=chrome` browser id:

```bash
browser-act browser list
```

If there are multiple `type=chrome` records and none is clearly dedicated to Costco review scraping, ask the user which chrome browser id to use.

3. Open a chrome-mode session to the Bazaarvoice deployment resource. This gives the scraper a same-origin browser context for the Bazaarvoice BFD API and avoids depending on Costco PDP transport behavior in a particular Chrome profile:

```bash
browser-act --session costco-reviews browser open {chrome-browser-id} "https://apps.bazaarvoice.com/deployments/costco/native_review_form/production/en_US/bv.js"
browser-act --session costco-reviews wait stable --timeout 60000
browser-act --session costco-reviews eval "$(python scripts/scrape-reviews.py --product-url "{product-url}" --max-reviews 2)"
```

PowerShell form:

```powershell
$js = python scripts/scrape-reviews.py --product-url "{product-url}" --max-reviews 2
browser-act --session costco-reviews eval "$js"
```

The sample scrape should return `ok: true`, `total_reviews_reported`, and `unique_reviews_scraped` equal to the requested sample size unless the product has fewer reviews.

4. Optional visual verification: if the user specifically asks to open the Costco PDP, click `Member Reviews`, or compare against the visible page, navigate the same chrome session to the product page and inspect the review widget:

```bash
browser-act --session costco-reviews navigate "{product-url}"
browser-act --session costco-reviews wait stable --timeout 60000
browser-act --session costco-reviews eval "$(python scripts/inspect-costco-review-page.py --product-url "{product-url}")"
browser-act --session costco-reviews state
browser-act --session costco-reviews click <Member Reviews index>
browser-act --session costco-reviews wait stable --timeout 60000
```

If the chrome profile cannot load the Costco PDP and shows a browser transport error such as `ERR_HTTP2_PROTOCOL_ERROR`, continue with the primary Bazaarvoice deployment resource path when the product URL or product id is known:

```bash
browser-act --session costco-reviews navigate "https://apps.bazaarvoice.com/deployments/costco/native_review_form/production/en_US/bv.js"
browser-act --session costco-reviews wait stable --timeout 60000
browser-act --session costco-reviews eval "$(python scripts/scrape-reviews.py --product-url "{product-url}" --max-reviews 2)"
```

## Capability Components

### API: Scrape All Product Reviews

Command:

```bash
browser-act --session costco-reviews eval "$(python scripts/scrape-reviews.py --product-url "{product-url}" --reviews-mode all)"
```

PowerShell form:

```powershell
$js = python scripts/scrape-reviews.py --product-url "{product-url}" --reviews-mode all
browser-act --session costco-reviews eval "$js"
```

Save the JSON output when the task asks for a file:

```powershell
browser-act --session costco-reviews eval "$(python scripts/scrape-reviews.py --product-url "{product-url}" --reviews-mode all)" |
  Set-Content -Path "costco_reviews_{productId}.json" -Encoding utf8
```

Output example:

```json
{
  "ok": true,
  "source_url": "https://www.costco.com/p/-/example-product/4000000000",
  "product_id": "4000000000",
  "reviews_mode": "all",
  "total_reviews_reported": 274,
  "unique_reviews_scraped": 274,
  "text_reviews_scraped": 178,
  "rating_only_reviews_scraped": 93,
  "pages": [
    {
      "offset": 0,
      "requested_limit": 100,
      "count": 100,
      "total": 274
    }
  ],
  "reviews": [
    {
      "sequence": 1,
      "id": "245123713",
      "rating": 5,
      "is_ratings_only": false,
      "title": "Great purchase",
      "review_text": "Comfortable and cute bed...",
      "user_nickname": "Christel",
      "verified_purchaser": true,
      "is_recommended": true,
      "total_positive_feedback_count": 35,
      "photos": []
    }
  ]
}
```

### API: Scrape Text Reviews Only

Use this only when the user explicitly wants written reviews and wants to exclude ratings-only records.

Command:

```bash
browser-act --session costco-reviews eval "$(python scripts/scrape-reviews.py --product-url "{product-url}" --reviews-mode text-only)"
```

PowerShell form:

```powershell
$js = python scripts/scrape-reviews.py --product-url "{product-url}" --reviews-mode text-only
browser-act --session costco-reviews eval "$js"
```

Output differences:

```json
{
  "reviews_mode": "text-only",
  "total_reviews_reported": 181,
  "rating_only_reviews_scraped": 0
}
```

### Network Capture: Verify Endpoint If Needed

Use network capture when Costco or Bazaarvoice changes and the API helper returns `error: true`. Keep the session in chrome mode; do not switch to chrome-direct just to capture the endpoint.

1. `navigate "{product-url}"`
2. `wait stable`
3. Click or scroll to `Member Reviews`.
4. `network requests --type xhr,fetch --filter bazaarvoice`
5. `network request <id>`

Endpoint characteristic: `apps.bazaarvoice.com/bfd/v1/clients/Costco/api-products/cv2/resources/data/reviews.json`

Expected stable request characteristics:

- Header: `Bv-Bfd-Token: 2070_2_0,native_review_form,en_US`
- Query fields: `resource=reviews`, `action=REVIEWS_N_STATS`, `filter=productid:eq:{productId}`, `include=authors,products,comments`, `Stats=Reviews`, `limit`, `offset`, `sort=relevancy:a1`, `apiversion=5.5`, `displaycode=2070_2_0-en_us`

## Enum Parameters

- `[API]` Review mode: `all` or `text-only`.
- `[API]` Sort: `relevancy:a1` was verified from Costco's default UI. Other Bazaarvoice sort values may work but must be verified before relying on them.
- `[API]` Content locales: default is `en_CA,fr_CA,en_US,en_US`, as observed on Costco's deployment.

## Pagination

API offset pagination is verified. The script requests `limit` records per page and increments `offset` until it reaches `TotalResults`, receives an empty page, or reaches `--max-reviews`.

## Success Criteria

- The helper returns `ok: true`.
- `unique_reviews_scraped` equals `total_reviews_reported` unless `--max-reviews` intentionally caps the run.
- The output includes `reviews` with stable review ids, ratings, text fields, reviewer metadata, helpful counts, and media URLs when present.
- For full collection, `reviews_mode` is `all` so ratings-only records are included.
- Close the owned browser-act session at the end:

```bash
browser-act session close costco-reviews
```

## Known Limitations

- The helper depends on Costco's current Bazaarvoice deployment values: client `Costco`, site `native_review_form`, display code `2070_2_0-en_us`, and API version `5.5`.
- Costco or Bazaarvoice may change the endpoint, token header, locale filters, or response shape. Use the Network Capture section to refresh the helper if that happens.
- Run the helper from a chrome-mode browser session. The primary execution context is the Bazaarvoice deployment resource page. A Costco product page context is useful for visual verification when it loads successfully, but it is not required when the product URL or product id is supplied.
