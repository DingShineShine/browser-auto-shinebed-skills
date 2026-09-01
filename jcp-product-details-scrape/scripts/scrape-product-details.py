import argparse
import json
import sys


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    parser = argparse.ArgumentParser(
        description="Print browser-side JavaScript for scraping JCPenney PDP details and variants."
    )
    parser.add_argument(
        "--url",
        default="",
        help="JCPenney PDP URL, search URL, or numeric JCP SKU ID. If omitted, the current browser page is used.",
    )
    parser.add_argument(
        "--sku-id",
        default="",
        help="Numeric JCP SKU ID. When provided, resolve it through product-aliases before scraping the PDP.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Return JSON by default, or CSV rows for spreadsheet export.",
    )
    parser.add_argument(
        "--store-id",
        default="",
        help="Optional JCPenney store id override for availability/pricing API calls.",
    )
    parser.add_argument(
        "--zip-code",
        default="",
        help="Optional ZIP/geo ZIP override for availability/pricing API calls.",
    )
    parser.add_argument(
        "--fetch-timeout-ms",
        type=int,
        default=20000,
        help="Browser-side fetch timeout in milliseconds.",
    )
    parser.add_argument(
        "--offering-concurrency",
        type=int,
        default=8,
        help="Maximum concurrent browser-side sku-offerings API fetches.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Omit bulky product detail arrays and alternate images for large batch crawls.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output. Ignored for CSV.",
    )
    args = parser.parse_args()

    config = {
        "url": args.url,
        "skuId": args.sku_id,
        "format": args.format,
        "storeId": args.store_id,
        "zipCode": args.zip_code,
        "fetchTimeoutMs": args.fetch_timeout_ms,
        "offeringConcurrency": args.offering_concurrency,
        "compact": args.compact,
        "pretty": args.pretty,
    }

    js = r"""
    (async () => {
      try {
        const config = __CONFIG__;
        const scrapedAt = new Date().toISOString();

        function asString(value) {
          return value == null ? "" : String(value);
        }

        function asNumber(value) {
          if (value == null || value === "") return null;
          const number = Number(value);
          return Number.isFinite(number) ? number : null;
        }

        function isSkuIdInput(value) {
          return /^\d{7,}$/.test(String(value || "").trim());
        }

        function makeSkuSearchUrl(skuId) {
          return "https://www.jcpenney.com/s?searchTerm=" + encodeURIComponent(String(skuId || "").trim());
        }

        function normalizeJcpUrl(value) {
          const raw = String(value || "").trim();
          const fallback = window.location.href;
          const resolved = raw ? new URL(raw, fallback).href : fallback;
          const url = new URL(resolved);
          if (!/(^|\.)jcpenney\.com$/i.test(url.hostname)) {
            throw new Error("Expected a jcpenney.com URL, got: " + url.hostname);
          }
          return url.href;
        }

        function normalizeOptionalJcpUrl(value) {
          const raw = String(value || "").trim();
          if (!raw) return "";
          return normalizeJcpUrl(raw);
        }

        async function resolveSkuAlias(inputSkuId) {
          const skuId = String(inputSkuId || "").trim();
          const aliasUrl = "https://browse-api.jcpenney.com/v3/product-aliases/url/" + encodeURIComponent(skuId);
          const base = {
            input_sku_id: skuId,
            alias_url: aliasUrl,
            alias_id: "",
            ppId: "",
            pdpUrl: "",
            selectedSKUId: "",
            alias_status: "",
            http_status: "",
            message: ""
          };
          if (!skuId) {
            return { ...base, alias_status: "not_requested", message: "No SKU ID provided." };
          }
          try {
            const response = await fetchJson(aliasUrl, {
              headers: {
                "Accept": "application/json",
                "X-Client-Name": "PDPREGULAR",
                "x-client-source": "PDP",
                "jcp_version": "GREEN"
              }
            });
            const data = response.data || {};
            const pdpUrl = normalizeOptionalJcpUrl(data.pdpUrl);
            return {
              ...base,
              alias_id: asString(data.id),
              ppId: asString(data.ppId),
              pdpUrl,
              selectedSKUId: asString(data.selectedSKUId),
              alias_status: response.ok && pdpUrl ? "ok" : "http_" + response.status,
              http_status: asString(response.status),
              message: response.ok ? "" : "product-aliases returned HTTP " + response.status
            };
          } catch (error) {
            return {
              ...base,
              alias_status: "error",
              message: String(error && error.message || error)
            };
          }
        }

        function textFromHtml(html) {
          const node = document.createElement("div");
          node.innerHTML = html || "";
          return (node.textContent || "").replace(/\s+/g, " ").trim();
        }

        function extractJsonAfterAssignment(text, marker) {
          const markerIndex = text.indexOf(marker);
          if (markerIndex < 0) return null;
          let index = markerIndex + marker.length;
          while (index < text.length && /[\s=]/.test(text[index])) index += 1;
          if (text[index] !== "{") return null;
          let depth = 0;
          let inString = false;
          let escaped = false;
          for (let i = index; i < text.length; i += 1) {
            const ch = text[i];
            if (inString) {
              if (escaped) {
                escaped = false;
              } else if (ch === "\\") {
                escaped = true;
              } else if (ch === "\"") {
                inString = false;
              }
              continue;
            }
            if (ch === "\"") {
              inString = true;
            } else if (ch === "{") {
              depth += 1;
            } else if (ch === "}") {
              depth -= 1;
              if (depth === 0) return JSON.parse(text.slice(index, i + 1));
            }
          }
          return null;
        }

        function extractPreloadedStateFromDocument(documentNode) {
          for (const script of Array.from(documentNode.scripts || [])) {
            const text = script.textContent || "";
            if (!text.includes("__PRELOADED_STATE__")) continue;
            const state =
              extractJsonAfterAssignment(text, "window.__PRELOADED_STATE__") ||
              extractJsonAfterAssignment(text, "__PRELOADED_STATE__");
            if (state && state.productDetails) return state;
          }
          return null;
        }

        async function fetchJson(url, options = {}) {
          const controller = new AbortController();
          const timeout = setTimeout(() => controller.abort(), Math.max(1000, config.fetchTimeoutMs || 20000));
          try {
            const response = await fetch(url, {
              credentials: "include",
              signal: controller.signal,
              ...options,
              headers: {
                "X-JCP-Forwarded-Host": "www.jcpenney.com",
                "X-JCP-Forwarded-Proto": "https",
                "X-JCP-Forwarded-Channel": "large",
                ...(options.headers || {})
              }
            });
            const text = await response.text();
            let data = null;
            try {
              data = text ? JSON.parse(text) : null;
            } catch (error) {
              throw new Error("Expected JSON from " + url + " but got non-JSON response");
            }
            return { ok: response.ok, status: response.status, url: response.url || url, data };
          } finally {
            clearTimeout(timeout);
          }
        }

        async function fetchPageState(sourceUrl) {
          const response = await fetch(sourceUrl, { credentials: "include" });
          const html = await response.text();
          if (!response.ok) {
            throw new Error("JCPenney page request failed: HTTP " + response.status);
          }
          if (/Access Denied|edgesuite|captcha|verify you are human/i.test(html)) {
            throw new Error("JCPenney returned a bot or access-denied page. Use an AdsPower or proxied browser profile that can view the PDP.");
          }
          const documentNode = new DOMParser().parseFromString(html, "text/html");
          const state = extractPreloadedStateFromDocument(documentNode);
          return { state, responseUrl: response.url || sourceUrl };
        }

        function getLiveState() {
          const state = window.__PRELOADED_STATE__;
          return state && state.productDetails ? state : null;
        }

        function productIdFromUrl(value) {
          try {
            const url = new URL(value, window.location.href);
            const match = url.pathname.match(/\/((?:ppr|eob)[^/?#]+)/i);
            return match ? match[1] : "";
          } catch (error) {
            return "";
          }
        }

        function liveStateMatchesSource(state, sourceUrl) {
          if (!config.url && !config.skuId) return true;
          const productDetails = state && state.productDetails || {};
          const expectedProductId = productIdFromUrl(sourceUrl);
          if (expectedProductId) return asString(productDetails.id).toLowerCase() === expectedProductId.toLowerCase();
          try {
            const source = new URL(sourceUrl);
            const current = new URL(window.location.href);
            if (source.pathname === "/s" || source.searchParams.has("searchTerm")) {
              const searchTerm = source.searchParams.get("searchTerm") || "";
              const redirectTerm = current.searchParams.get("redirectTerm") || "";
              return current.pathname.includes("/p/") && (!searchTerm || !redirectTerm || searchTerm === redirectTerm);
            }
          } catch (error) {
          }
          return sourceUrl === window.location.href;
        }

        function getResourceUrls() {
          return performance.getEntriesByType("resource")
            .map((entry) => entry && entry.name)
            .filter((name) => typeof name === "string");
        }

        function inferApiParams(productDetails, lot) {
          const urls = getResourceUrls();
          const params = {};
          for (const name of urls) {
            if (!/browse-api\.jcpenney\.com\/v2\/(sku-offerings|product-aggregator)/i.test(name)) {
              continue;
            }
            try {
              const search = new URL(name).searchParams;
              for (const key of ["stores", "delivery", "subdivision", "occasionName", "zipCode", "bopisZipcode", "deliveryAvailabilityCheckRequired", "GPA", "warehouseClass", "geoZip"]) {
                const value = search.get(key);
                if (value && !params[key]) params[key] = value;
              }
            } catch (error) {
            }
          }
          const organization = lot.organization || {};
          params.stores = config.storeId || params.stores || "";
          params.delivery = params.delivery || "STANDARD";
          params.subdivision = params.subdivision || organization.subdivision || productDetails.subdivision || "";
          params.occasionName = params.occasionName || lot.occasionName || "";
          params.zipCode = config.zipCode || params.zipCode || params.geoZip || "";
          params.bopisZipcode = config.zipCode || params.bopisZipcode || params.zipCode || "";
          params.deliveryAvailabilityCheckRequired = params.deliveryAvailabilityCheckRequired || "false";
          params.GPA = params.GPA || "false";
          params.warehouseClass = params.warehouseClass || lot.warehouseClassCode || "";
          params.geoZip = config.zipCode || params.geoZip || params.zipCode || "";
          return params;
        }

        function buildQuery(params, keys) {
          const query = new URLSearchParams();
          for (const key of keys) {
            const value = params[key];
            if (value != null && value !== "") query.set(key, String(value));
          }
          return query.toString();
        }

        function additionalDetailsUrl(productDetails, params) {
          const href =
            productDetails.additionalDetails && productDetails.additionalDetails.url ||
            "/v2/product-aggregator/" + productDetails.id + "/additional-details";
          const url = new URL(href, "https://browse-api.jcpenney.com");
          const query = buildQuery(params, ["stores", "deliveryAvailabilityCheckRequired", "GPA", "geoZip"]);
          url.search = query;
          return url.href;
        }

        function offeringUrl(item, params) {
          const href = item.offering && item.offering.href;
          if (!href) return "";
          const url = new URL(href, "https://browse-api.jcpenney.com");
          const query = buildQuery(params, [
            "stores",
            "delivery",
            "subdivision",
            "occasionName",
            "zipCode",
            "bopisZipcode",
            "deliveryAvailabilityCheckRequired",
            "GPA",
            "warehouseClass",
            "geoZip"
          ]);
          url.search = query;
          return url.href;
        }

        function priceAmount(pricing, type) {
          return ((pricing && pricing.amounts) || []).find((amount) => amount && amount.type === type) || {};
        }

        function firstCoupon(pricing) {
          return ((pricing && pricing.couponInfo) || [])[0] || {};
        }

        function firstDeliveryOptions(offering) {
          const options =
            offering &&
            offering.promise &&
            Array.isArray(offering.promise.skuDeliveryOptions) &&
            offering.promise.skuDeliveryOptions[0] &&
            offering.promise.skuDeliveryOptions[0].deliveryOptions;
          return options || {};
        }

        function firstOptionValue(item, name) {
          return ((item && item.optionValues) || []).find((option) => option && option.name === name) || {};
        }

        function optionValueMap(item) {
          const values = {};
          for (const option of (item && item.optionValues) || []) {
            if (option && option.name) values[option.name] = option.value || "";
          }
          return values;
        }

        function collectProductImages(item, colorOption) {
          const itemImages = [];
          if (colorOption.productImage && colorOption.productImage.url) itemImages.push(colorOption.productImage.url);
          for (const image of colorOption.altImages || []) {
            if (image && image.url) itemImages.push(image.url);
          }
          return Array.from(new Set(itemImages));
        }

        async function mapLimit(items, limit, mapper) {
          const results = new Array(items.length);
          const workerCount = Math.max(1, Math.min(items.length, Number(limit) || 1));
          let nextIndex = 0;
          async function worker() {
            while (nextIndex < items.length) {
              const index = nextIndex;
              nextIndex += 1;
              results[index] = await mapper(items[index], index);
            }
          }
          await Promise.all(Array.from({ length: workerCount }, worker));
          return results;
        }

        function toCsv(rows) {
          const header = [
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
            "alt_image_urls",
            "offering_url"
          ];
          const escapeCell = (value) => "\"" + asString(value).replace(/"/g, "\"\"") + "\"";
          return [
            header.join(","),
            ...rows.map((row) => header.map((field) => escapeCell(Array.isArray(row[field]) ? row[field].join("|") : row[field])).join(","))
          ].join("\n");
        }

        const rawInputUrl = String(config.url || "").trim();
        const inputSkuId = String(config.skuId || (isSkuIdInput(rawInputUrl) ? rawInputUrl : "")).trim();
        const preWarnings = [];
        let alias = inputSkuId ? await resolveSkuAlias(inputSkuId) : {
          input_sku_id: "",
          alias_url: "",
          alias_id: "",
          ppId: "",
          pdpUrl: "",
          selectedSKUId: "",
          alias_status: "not_requested",
          http_status: "",
          message: ""
        };
        let sourceUrl = "";
        if (inputSkuId) {
          if (alias.alias_status === "ok" && alias.pdpUrl) {
            sourceUrl = alias.pdpUrl;
          } else {
            sourceUrl = makeSkuSearchUrl(inputSkuId);
            preWarnings.push("product-aliases for " + inputSkuId + " did not return a PDP URL; falling back to searchTerm. " + (alias.message || alias.alias_status));
          }
        } else {
          sourceUrl = normalizeJcpUrl(rawInputUrl);
        }
        const liveState = getLiveState();
        let sourceState = liveState && liveStateMatchesSource(liveState, sourceUrl) ? liveState : null;
        let sourceStatus = "live";
        let fetchedPageUrl = "";

        if (!sourceState && sourceUrl) {
          const fetched = await fetchPageState(sourceUrl);
          sourceState = fetched.state;
          fetchedPageUrl = fetched.responseUrl;
          sourceStatus = "fetched";
        }

        if (!sourceState || !sourceState.productDetails) {
          throw new Error("Could not find JCPenney productDetails in window.__PRELOADED_STATE__. Navigate to the PDP, wait stable, then retry.");
        }

        const productDetails = sourceState.productDetails;
        const lots = Array.isArray(productDetails.lots) ? productDetails.lots : [];
        if (!lots.length) {
          throw new Error("JCPenney productDetails did not include lots.");
        }

        const defaultLot = lots[0] || {};
        const params = inferApiParams(productDetails, defaultLot);
        const warnings = [...preWarnings];

        let additionalDetails = {};
        try {
          const detailsResponse = await fetchJson(additionalDetailsUrl(productDetails, params));
          additionalDetails = detailsResponse.data || {};
          if (!detailsResponse.ok) warnings.push("additional-details returned HTTP " + detailsResponse.status);
        } catch (error) {
          warnings.push("additional-details failed: " + String(error && error.message || error));
        }

        const inventoryMap = Object.fromEntries(((additionalDetails && additionalDetails.inventory) || []).map((entry) => [entry.id, entry]));
        const lotPriceData =
          additionalDetails &&
          additionalDetails.lotPrice &&
          Array.isArray(additionalDetails.lotPrice.data) &&
          additionalDetails.lotPrice.data[0] ||
          {};

        const rowInputs = [];
        for (const lot of lots) {
          const lotParams = inferApiParams(productDetails, lot);
          for (const item of lot.items || []) {
            rowInputs.push({ lot, lotParams, item });
          }
        }

        const rows = await mapLimit(rowInputs, config.offeringConcurrency, async ({ lot, lotParams, item }) => {
            const colorOption = firstOptionValue(item, "color");
            const allOptions = optionValueMap(item);
            const url = offeringUrl(item, lotParams);
            let offering = {};
            let offeringStatus = "";
            if (url) {
              try {
                const offeringResponse = await fetchJson(url, {
                  headers: {
                    "X-Client-Name": "PDPREGULAR",
                    "x-client-source": "PDP",
                    "jcp_version": "GREEN"
                  }
                });
                offering = offeringResponse.data || {};
                offeringStatus = offeringResponse.status;
                if (!offeringResponse.ok) {
                  warnings.push("sku-offerings for " + item.id + " returned HTTP " + offeringResponse.status);
                }
              } catch (error) {
                warnings.push("sku-offerings for " + item.id + " failed: " + String(error && error.message || error));
              }
            } else {
              warnings.push("No offering href found for SKU " + item.id);
            }

            const pricing = offering.pricing || lotPriceData || {};
            const original = priceAmount(pricing, "ORIGINAL");
            const sale = priceAmount(pricing, "SALE");
            const coupon = firstCoupon(pricing);
            const deliveryOptions = firstDeliveryOptions(offering);
            const bopusLocation =
              deliveryOptions.bopus &&
              Array.isArray(deliveryOptions.bopus.locationIds) &&
              deliveryOptions.bopus.locationIds[0] ||
              {};
            const images = collectProductImages(item, colorOption);
            const inventory = inventoryMap[item.id] || {};

            return {
              sku_id: asString(item.id),
              web_id: asString(productDetails.webId),
              product_id: asString(productDetails.id),
              product_name: asString(productDetails.name),
              brand: asString(productDetails.brand && productDetails.brand.name),
              lot_id: asString(lot.id),
              color: asString(colorOption.value || allOptions.color),
              color_family: asString(colorOption.family),
              color_option_id: asString(colorOption.id),
              size: asString(item.size || item.curatedSize || allOptions.size),
              primary_barcode: asString(item.primaryBarcode),
              secondary_barcode: asString(item.secondaryBarcode),
              itsa_status: asString(item.itsaStatus),
              source: asString(item.source),
              has_inventory: item.hasInventory == null ? "" : Boolean(item.hasInventory),
              atp: item.atp == null ? "" : Boolean(item.atp),
              inventory_atp: inventory.atp == null ? "" : Boolean(inventory.atp),
              inventory_quality: asString(inventory.quality),
              offering_status: asString(offeringStatus),
              actual_sku_id: asString(offering.actualSkuId),
              marketing_label: asString(pricing.marketingLabel),
              original_price_min: asNumber(original.min),
              original_price_max: asNumber(original.max),
              sale_price_min: asNumber(sale.min),
              sale_price_max: asNumber(sale.max),
              sale_percent_off_min: asNumber(sale.minPercentOff),
              sale_percent_off_max: asNumber(sale.maxPercentOff),
              coupon_code: asString(coupon.alphaId),
              coupon_price_min: asNumber(coupon.amount && coupon.amount.min),
              coupon_price_max: asNumber(coupon.amount && coupon.amount.max),
              pricing_inventory: asString(pricing.inventory),
              ship_to_home_status: asString(deliveryOptions.shipToHome && deliveryOptions.shipToHome.availabilityStatus),
              bopus_status: asString(bopusLocation.availabilityStatus),
              my_alert_indicator: offering.myAlertIndicator == null ? "" : Boolean(offering.myAlertIndicator),
              image_url: asString(images[0]),
              swatch_url: asString(colorOption.image && colorOption.image.url),
              alt_image_urls: config.compact ? [] : images.slice(1),
              offering_url: url
            };
        });

        const priceValues = {
          original: Array.from(new Set(rows.map((row) => row.original_price_min).filter((value) => value != null))).sort((a, b) => a - b),
          sale: Array.from(new Set(rows.map((row) => row.sale_price_min).filter((value) => value != null))).sort((a, b) => a - b),
          coupon: Array.from(new Set(rows.map((row) => row.coupon_price_min).filter((value) => value != null))).sort((a, b) => a - b)
        };

        const product = {
          product_id: asString(productDetails.id),
          web_id: asString(productDetails.webId),
          name: asString(productDetails.name),
          brand: asString(productDetails.brand && productDetails.brand.name),
          category: asString(productDetails.category && productDetails.category.name),
          pdp_url: productDetails.pdpURL ? new URL(productDetails.pdpURL, "https://www.jcpenney.com").href : ""
        };
        if (!config.compact) {
          product.description_text = textFromHtml(defaultLot.description);
          product.bulleted_attributes = (defaultLot.bulletedAttributes || []).map((entry) => entry.description).filter(Boolean);
          product.dimensions = productDetails.dimensions || [];
          product.color_sequences = productDetails.colorSequences || [];
          product.specifications = defaultLot.specifications && defaultLot.specifications.data || [];
          product.images = productDetails.images || [];
        }

        const result = {
          ok: true,
          scraped_at: scrapedAt,
          input_url: rawInputUrl,
          source_url: sourceUrl,
          current_url: window.location.href,
          fetched_page_url: fetchedPageUrl,
          state_source: sourceStatus,
          alias,
          api_params: params,
          product,
          lot_price_summary: config.compact ? {} : lotPriceData,
          variant_count: rows.length,
          price_values: priceValues,
          warning_count: warnings.length,
          warnings,
          variants: rows
        };

        if (config.format === "csv") {
          return toCsv(rows);
        }
        return JSON.stringify(result, null, config.pretty ? 2 : 0);
      } catch (error) {
        return JSON.stringify({
          error: true,
          message: String(error && error.message || error),
          stack: error && error.stack ? String(error.stack).split("\n").slice(0, 5) : []
        });
      }
    })()
    """.replace("__CONFIG__", json.dumps(config))

    print(" ".join(line.strip() for line in js.splitlines() if line.strip()))


if __name__ == "__main__":
    main()
