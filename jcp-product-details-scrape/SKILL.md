---
name: jcp-product-details-scrape
description: "JCPenney product detail and variant extraction through browser-act AdsPower or proxied browser sessions. Use this skill when the user asks to scrape, collect, export, or save JCP/JCPenney PDP details, redirected search-term product pages, prices, coupon prices, colors, sizes, SKUs, UPC/barcodes, inventory, shipping availability, images, or product specifications. Outputs JSON, CSV, or batch XLSX workbook rows for all variants exposed by the loaded JCPenney product page."
metadata:
  requires:
    browser-auto-shinebed: ">=0.1.7"
    runtime: "Python 3.12, uv package manager, browser-act via browser-auto-shinebed, Node.js for XLSX workbook export"
---

# JCPenney - Scrape Product Details

## Language

Reply in the user's language.

## Objective

Scrape JCPenney PDP product details and all exposed SKU variants by using `browser-act` through the `browser-auto-shinebed` wrapper. When the input is a numeric JCP SKU id, first resolve it through the JCPenney product-aliases API to find the canonical PDP, then read `window.__PRELOADED_STATE__.productDetails` and join variant rows with the PDP's `additional-details` and `sku-offerings` API responses.

## Prerequisites

- Target input pattern: a numeric JCP SKU id, a PDP URL such as `https://www.jcpenney.com/p/{slug}/{productId}?pTmplType=regular`, or a JCPenney search URL such as `https://www.jcpenney.com/s?searchTerm={sku-or-keyword}`.
- Numeric SKU ids should use product-aliases first: `https://browse-api.jcpenney.com/v3/product-aliases/url/{sku_id}`. Use the returned `pdpUrl` as the PDP target. Use searchTerm redirect only as fallback when alias resolution fails or returns no PDP URL.
- Login or account state: not required for public PDP data, but JCPenney may block plain HTTP requests with Akamai. Use a browser profile/proxy context that can manually view the PDP.
- Browser runtime: use `browser-act` through the `browser-auto-shinebed` wrapper.
- Browser mode: prefer an AdsPower profile such as `adspower:{user_id}` when the user provides one or mentions ADS/AdsPower. Otherwise choose an existing browser record from `browser-act browser list` only when its description clearly matches JCPenney scraping; if none clearly matches, ask the user which browser id to use.

## Parameters

- `--url`: optional JCPenney PDP URL, search URL, or numeric JCP SKU id. If omitted, the script uses the current browser page URL and live page state.
- `--sku-id`: optional numeric JCP SKU id. When present, resolve product-aliases first and scrape the returned PDP URL.
- `--format`: optional. `json` by default. Use `csv` for spreadsheet-ready export.
- `--store-id`: optional. Overrides the store id inferred from the loaded PDP network requests.
- `--zip-code`: optional. Overrides the ZIP/geo ZIP inferred from the loaded PDP network requests.
- `--fetch-timeout-ms`: optional. Defaults to `20000`.
- `--compact`: optional. Omit bulky description/specification/dimension/image arrays and alternate variant image lists; use this for large batch price crawls.
- `--pretty`: optional. Pretty-print JSON output. Ignored for CSV.

Packaged helper scripts:

- Primary Forge capability: `scripts/scrape-product-details.py` prints browser-side JavaScript for one PDP/SKU/search extraction. The other scripts are support orchestration for bulk workbook runs and should not be treated as atomic browser `eval` components.
- `scripts/scrape-product-details.py`: browser-side PDP extractor generator for one SKU/PDP/search URL.
- `scripts/prepare-source.py`: builds `source_rows.json` from the source workbook and groups by SKU/SPU name + source JCP SKU prefix.
- `scripts/run-jcp-batch.py`: resolves every source SKU through product-aliases, dedupes PDP fetches by `ppId/pdpUrl`, and writes raw group JSON. It opens one browser-act session and closes that owned session by default.
- `scripts/prepare-workbook-data.py`: builds `workbook_data.json`, including `Alias Map`, exact-match rows, warnings, and run metadata.
- `scripts/build-workbook.mjs`: exports the final XLSX workbook from `workbook_data.json`.

## Pre-Execution Checks

1. Confirm `browser-act` is available:

```bash
browser-act doctor
```

2. Open a JCPenney page in a browser profile that can pass JCPenney's bot checks. If the user gave an AdsPower user id, use it directly only in the open step. Opening `about:blank` first and then navigating is acceptable when JCPenney page load is slow:

```bash
browser-act --session jcp-details browser open adspower:{user_id} about:blank
browser-act --session jcp-details navigate "https://www.jcpenney.com/"
browser-act --session jcp-details wait stable --timeout 60000
```

If the user did not provide an AdsPower id, inspect browser records:

```bash
browser-act browser list
```

Use a clearly relevant existing browser. If none is clearly relevant, show the candidate browser ids, names, types, descriptions, and proxy values, then ask the user to choose.

3. For a numeric SKU id, first verify alias resolution in the JCP browser context:

```bash
browser-act --session jcp-details eval "fetch('https://browse-api.jcpenney.com/v3/product-aliases/url/{sku-id}',{credentials:'include',headers:{Accept:'application/json','X-Client-Name':'PDPREGULAR','x-client-source':'PDP',jcp_version:'GREEN'}}).then(r=>r.text())"
```

The result should include `ppId`, `pdpUrl`, and `selectedSKUId`. Navigate to the returned `pdpUrl`, wait for the PDP to stabilize, then run extraction:

```bash
browser-act --session jcp-details navigate "{pdpUrl}"
browser-act --session jcp-details wait stable --timeout 60000
browser-act --session jcp-details eval "$(python scripts/scrape-product-details.py --sku-id {sku-id} --pretty)"
```

The result should return `ok: true`, `alias.alias_status: "ok"`, `alias.ppId`, `product.product_id`, and `variant_count` greater than zero. If the returned variants do not include the input SKU id, keep the row as `missing_from_jcp_response`; do not replace the source SKU with `selectedSKUId`.

4. For a PDP URL or search fallback, confirm the loaded page is a PDP or redirected from a search URL to a PDP:

```bash
browser-act --session jcp-details eval "location.href"
browser-act --session jcp-details get title
```

The URL should usually contain `/p/` and a product id like `ppr...`. If the page shows `Access Denied`, retry with a working AdsPower/proxied profile.

5. Run a sample JSON extraction:

```bash
browser-act --session jcp-details eval "$(python scripts/scrape-product-details.py --pretty)"
```

The result should return `ok: true`, a `product.product_id`, and `variant_count` greater than zero.

## Capability Components

### DOM + API: Extract PDP Variants

Alias-first command for a numeric JCP SKU id when the browser is already on the resolved PDP:

```bash
browser-act --session jcp-details eval "$(python scripts/scrape-product-details.py --sku-id {sku-id} --pretty)"
```

For unattended batch runs, use the batch wrapper to resolve aliases, navigate to each deduped PDP, and then run the PDP extractor:

```bash
python scripts/prepare-source.py --source-xlsx "{source-xlsx}" --output-dir "{run-output-dir}"
python scripts/run-jcp-batch.py --source-json "{run-output-dir}/source_rows.json" --skill-dir "." --session jcp-details --browser-id "adspower:{user_id}" --output-dir "{run-output-dir}"
python scripts/prepare-workbook-data.py --base-dir "{run-output-dir}" --browser-id "adspower:{user_id}"
node scripts/build-workbook.mjs --base-dir "{run-output-dir}" --output-path "{final-xlsx}"
```

Command:

```bash
browser-act --session jcp-details eval "$(python scripts/scrape-product-details.py --url '{jcp-url}')"
```

For batch price crawls or large variant families, use compact JSON:

```bash
browser-act --session jcp-details eval "$(python scripts/scrape-product-details.py --compact)"
```

For redirected search URLs, use only as fallback when product-aliases fails or when the input is truly a keyword rather than a SKU id. Navigate first and let the browser land on the PDP before running the helper:

```bash
browser-act --session jcp-details navigate "https://www.jcpenney.com/s?searchTerm={sku-or-keyword}"
browser-act --session jcp-details wait stable --timeout 60000
browser-act --session jcp-details eval "$(python scripts/scrape-product-details.py --pretty)"
```

Save CSV output when the user asks for a file:

```powershell
$csv = browser-act --session jcp-details eval "$(python scripts/scrape-product-details.py --format csv)"
Set-Content -LiteralPath "output\jcp_product_variants.csv" -Value $csv -Encoding utf8
```

CSV columns:

```text
sku_id,web_id,product_id,product_name,brand,lot_id,color,color_family,color_option_id,size,primary_barcode,secondary_barcode,itsa_status,source,has_inventory,atp,inventory_atp,inventory_quality,offering_status,actual_sku_id,marketing_label,original_price_min,original_price_max,sale_price_min,sale_price_max,sale_percent_off_min,sale_percent_off_max,coupon_code,coupon_price_min,coupon_price_max,pricing_inventory,ship_to_home_status,bopus_status,my_alert_indicator,image_url,swatch_url,alt_image_urls,offering_url
```

JSON output example:

```json
{
  "ok": true,
  "source_url": "https://www.jcpenney.com/p/example-product/ppr1234567890?pTmplType=regular",
  "current_url": "https://www.jcpenney.com/p/example-product/ppr1234567890?pTmplType=regular",
  "alias": {
    "input_sku_id": "12345670018",
    "alias_id": "12345670018",
    "ppId": "ppr1234567890",
    "pdpUrl": "https://www.jcpenney.com/p/example-product/ppr1234567890?pTmplType=regular&selectedSKUId=12345670018",
    "selectedSKUId": "12345670018",
    "alias_status": "ok"
  },
  "product": {
    "product_id": "ppr1234567890",
    "web_id": "1234567",
    "name": "Example Product",
    "brand": "Example Brand",
    "category": "Blankets & Throws"
  },
  "variant_count": 4,
  "price_values": {
    "original": ["40"],
    "sale": ["27.99"],
    "coupon": ["18.19"]
  },
  "variants": [
    {
      "sku_id": "12345670018",
      "color": "Black",
      "size": "One Size",
      "primary_barcode": "810000000000",
      "original_price_min": 40,
      "sale_price_min": 27.99,
      "coupon_code": "CODE",
      "coupon_price_min": 18.19,
      "ship_to_home_status": "AH",
      "atp": true
    }
  ]
}
```

### Network Capture: Refresh Endpoint Details

Use this if the helper returns `error: true`, `variant_count: 0`, or JCPenney changes the PDP state shape.

1. `navigate "{jcp-url}"`
2. `wait stable --timeout 60000`
3. `network requests --type xhr,fetch --filter product-aggregator`
4. `network requests --type xhr,fetch --filter sku-offerings`
5. `network request <id>`

Endpoint characteristics:

```text
https://browse-api.jcpenney.com/v2/product-aggregator/{productId}/additional-details
https://browse-api.jcpenney.com/v2/sku-offerings/{webId}/{encodedSkuOfferingId}
```

Observed `additional-details` response includes `inventory[]` and `lotPrice.data[]`. Observed `sku-offerings` response includes `pricing`, `promise.skuDeliveryOptions[]`, `actualSkuId`, and `myAlertIndicator`.

## Enum Parameters

- `[DOM]` Product id, web id, lots, SKU ids, color names, color families, size values, barcodes, images, specs, and initial inventory flags come from `window.__PRELOADED_STATE__.productDetails`.
- `[DOM]` Current PDP ZIP/store query values are inferred from `performance.getEntriesByType("resource")` URLs for `sku-offerings` and `additional-details`.
- `[API]` Numeric SKU id inputs are resolved through `https://browse-api.jcpenney.com/v3/product-aliases/url/{sku_id}` before PDP scraping. The alias result is metadata only; final variant matching still uses PDP `variants[].sku_id`.
- `[API]` SKU-level prices and shipping availability come from each item's `offering.href`, resolved against `https://browse-api.jcpenney.com`.
- `[API]` Lot-level price and inventory fallback comes from `productDetails.additionalDetails.url` or `/v2/product-aggregator/{productId}/additional-details`.

## Pagination

No pagination. JCPenney PDP variants are exposed in a single loaded product state. The helper fetches one `additional-details` response and one `sku-offerings` response per SKU variant.

## Success Criteria

- The helper returns `ok: true`.
- For numeric SKU id input, the helper returns an `alias` object with `input_sku_id`, `alias_id`, `ppId`, `pdpUrl`, `selectedSKUId`, and `alias_status`.
- `product.product_id`, `product.web_id`, and `product.name` are present.
- `variant_count` is greater than zero.
- Every variant row includes `sku_id`; color and size are present when exposed by JCPenney.
- Price fields are populated from SKU-level `sku-offerings` or lot-level fallback.
- Close the owned browser-act session at the end:

```bash
browser-act session close jcp-details
```

## Known Limitations

- JCPenney may block non-browser HTTP access with Akamai. Use an AdsPower/proxied profile that can view the PDP.
- Direct local requests to product-aliases can return HTTP 403. Resolve aliases from a working JCPenney browser page context.
- Search URLs are now fallback for SKU ids. They are usually client-side redirected after the search API resolves a single product. Navigate and wait first, then run the helper on the resulting PDP.
- Store and ZIP affect delivery availability. The helper infers them from the loaded page's resource URLs when possible; pass `--store-id` and `--zip-code` if a specific location is required.
- Some variants may expose no swatch/product image in the PDP payload. The helper leaves variant image fields blank rather than inventing URLs from another color; product-level images remain available in JSON at `product.images`.
