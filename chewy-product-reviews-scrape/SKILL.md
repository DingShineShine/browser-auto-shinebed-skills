---
name: chewy-product-reviews-scrape
description: "Chewy product review scraping through browser-act chrome mode and Chewy GraphQL. Use this skill when the user asks to scrape, collect, export, download, paginate, or save all Chewy product ratings or customer reviews for a Chewy product URL or part number. Outputs complete JSON review data including ratings-only reviews, text reviews, reviewer names, verification flags, helpful counts, photos, and pet profile snapshots."
metadata:
  requires:
    browser-auto-shinebed: ">=0.1.6"
    runtime: "Python 3.12, uv package manager, browser-act via browser-auto-shinebed"
---

# Chewy - Product Reviews Scrape

## Language

Reply in the user's language.

## Objective

Scrape all public Chewy product ratings and customer reviews for a Chewy product detail page by using `browser-act` chrome mode and Chewy's GraphQL review API.

## Prerequisites

- Target page pattern: `https://www.chewy.com/{product-slug}/dp/{itemPartNumber}`.
- Login or account state: not required for public product reviews. The visible confirmation is that the Chewy product page loads and the ratings or reviews section is visible.
- Browser runtime: use `browser-act` through the `browser-auto-shinebed` wrapper.
- Wrapper dependency: install or update `browser-auto-shinebed >= 0.1.6` before using this Skill.
- Browser mode: default to a `type=chrome` browser record from `browser-act browser list`, opened with `--headed` because Chewy can return a 403 from its GraphQL endpoint in headless chrome. Do not use `chrome-direct`, `stealth`, or `adspower:{user_id}` unless the user explicitly overrides this skill's chrome-mode default.

## Parameters

- `--product-url`: optional Chewy product URL. If omitted, the script uses the current browser page URL.
- `--item-part-number`: optional item part number from the URL `/dp/{itemPartNumber}`. If omitted, it is parsed from `--product-url` or the current page URL.
- `--review-part-number`: optional Chewy product review part number. Use this when automatic resolution fails. Chewy variant URLs can use an item part number that differs from the review product part number.
- `--reviews-mode`: optional. `all` by default, including ratings-only records. Use `text-only` to return only reviews with a title or review text.
- `--page-size`: optional. Default `50`; valid range is `1` to `50`.
- `--max-pages`: optional safety cap. Default `200`.
- `--sort`: optional GraphQL review sort enum. Default `NEWEST`, which was verified during exploration.

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

If there are multiple `type=chrome` records and none is clearly dedicated to Chewy review scraping, ask the user which chrome browser id to use.

3. Open the Chewy product page in chrome mode and wait for it to load. Use `--headed`; this is still chrome mode and avoids Chewy's observed headless GraphQL 403:

```bash
browser-act --session chewy-reviews browser open {chrome-browser-id} "{product-url}" --headed
browser-act --session chewy-reviews wait stable --timeout 60000
```

4. Run a small sample scrape:

```bash
browser-act --session chewy-reviews eval "$(python scripts/scrape-reviews.py --product-url "{product-url}" --page-size 5 --max-pages 1)"
```

The sample should return `ok: true`, a resolved `review_part_number`, and a non-empty `reviews` array when the product has public reviews.

## Capability Components

### API: Scrape All Product Ratings And Reviews

Command:

```bash
browser-act --session chewy-reviews eval "$(python scripts/scrape-reviews.py --product-url "{product-url}" --reviews-mode all)"
```

Save the JSON output when the task asks for a file:

```powershell
browser-act --session chewy-reviews eval "$(python scripts/scrape-reviews.py --product-url "{product-url}" --reviews-mode all)" |
  Set-Content -Path "chewy_reviews_{itemPartNumber}.json" -Encoding utf8
```

Output example:

```json
{
  "ok": true,
  "source_url": "https://www.chewy.com/example-product/dp/1234567",
  "item_part_number": "1234567",
  "review_part_number": "1234500",
  "reviews_mode": "all",
  "total_reviews_reported": 144,
  "unique_reviews_scraped": 144,
  "text_reviews_scraped": 70,
  "rating_only_or_blank_scraped": 74,
  "pages": [
    {
      "page": 0,
      "requested_size": 50,
      "count": 50,
      "total_results": 144,
      "has_next_page": true
    }
  ],
  "reviews": [
    {
      "sequence": 1,
      "id": "18233732",
      "content_id": "279225304",
      "rating": 5,
      "title": "Good Treat",
      "review_text": "My picky eater actually ate them...",
      "submitted_by": "Desiree",
      "submitted_at": "2026-08-22T20:44:57.000Z",
      "helpfulness": 0,
      "is_incentivized": false,
      "is_verified": true,
      "photos": [],
      "pet_profile_snapshots": []
    }
  ]
}
```

### API: Scrape Text Reviews Only

Use this when the user explicitly wants written customer reviews and wants to exclude ratings-only records.

Command:

```bash
browser-act --session chewy-reviews eval "$(python scripts/scrape-reviews.py --product-url "{product-url}" --reviews-mode text-only)"
```

Output differences:

```json
{
  "reviews_mode": "text-only",
  "unique_reviews_scraped": 70,
  "text_reviews_scraped": 70,
  "rating_only_or_blank_scraped": 0
}
```

### Network Capture: Verify Endpoint If Needed

Use network capture when Chewy changes the page or when the helper returns `ok: false`. Keep the session in chrome mode unless the user explicitly requests another mode. If the error is a GraphQL 403 from a headless chrome session, close the session and reopen it with `--headed`.

1. `navigate "{product-url}"`
2. `wait stable`
3. Scroll or click the rating link to show the reviews section.
4. `network requests --type xhr,fetch --filter graphql`
5. `network request <id>`

Endpoint characteristic: `https://www.chewy.com/api/api-router/graphql`

Expected stable request characteristics:

- Operation name: `SubgraphReviews` or `SubgraphReviewPhotos`.
- Query field: `product(partNumber: $partNumber) { reviewsPage(...) }`.
- Variables: `partNumber`, `pageRequestInput: { size, page }`, `filter`, `sort`, and `includePetProfileSnapshots`.
- Header: `x-chewy-component-id: pdp-page`.

## Enum Parameters

- `[API]` Review mode: `all` or `text-only`.
- `[API]` Sort: `NEWEST` was verified. Other Chewy UI sort labels should be recaptured before relying on their GraphQL enum values.
- `[DOM]` Filter and sort dropdown option labels can be discovered from the reviews section with `state` or a DOM `select` option scan.

## Pagination

API page-number pagination is verified. The script requests `page-size` records per page and increments `page` until `hasNextPage` is false, an empty page is returned, or `--max-pages` is reached.

## Success Criteria

- The helper returns `ok: true`.
- For `--reviews-mode all`, `unique_reviews_scraped` equals `total_reviews_reported` unless `--max-pages` intentionally caps the run.
- For `--reviews-mode text-only`, every returned review has a non-empty title or review text.
- The output includes stable review ids, rating, title/text fields, reviewer display name, submitted timestamp, verification and incentivized flags, helpful counts, photo URLs, and pet profile snapshots when present.
- Close the owned browser-act session at the end:

```bash
browser-act session close chewy-reviews
```

## Known Limitations

- Chewy can use different item and review product part numbers for product variants. The script attempts automatic resolution, but `--review-part-number` is available as a manual override.
- The helper depends on Chewy's current GraphQL schema for `reviewsPage`; use the Network Capture section to refresh the query if Chewy changes it.
- Data access is limited to public review data visible from the user's browser session.
- In validation, headless chrome received a Chewy GraphQL 403 while chrome headed succeeded.
