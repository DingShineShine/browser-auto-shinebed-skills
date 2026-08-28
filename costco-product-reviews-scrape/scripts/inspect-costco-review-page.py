import argparse
import json
import sys


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-url", default="")
    parser.add_argument("--product-id", default="")
    args = parser.parse_args()

    config = {
        "productUrl": args.product_url,
        "productId": args.product_id,
    }

    js = r"""
    (() => {
      try {
        const config = __CONFIG__;

        function textOf(node) {
          return String((node && (node.innerText || node.textContent)) || "").trim();
        }

        function parseProductId(value) {
          const matches = String(value || "").match(/\d{8,}/g) || [];
          return matches.length ? matches[matches.length - 1] : "";
        }

        const currentUrl = window.location.href;
        const suppliedUrl = config.productUrl || "";
        const bvProductId = window.BV &&
          window.BV.swat_reviews &&
          window.BV.swat_reviews.config &&
          window.BV.swat_reviews.config.productId || "";
        const resolvedProductId = config.productId || bvProductId || parseProductId(suppliedUrl) || parseProductId(currentUrl);
        const reviewHost = document.querySelector("#CostcoBVContainer");
        const reviewRoot = reviewHost && reviewHost.shadowRoot;
        const ratingHost = document.querySelector("#CostcoBVReviewContainer");
        const ratingRoot = ratingHost && ratingHost.shadowRoot;
        const memberReviewsButton = Array.from(document.querySelectorAll("button,a,[role='button']"))
          .find((element) => /Member Reviews|Read\s+\d+\s+Reviews/i.test(textOf(element) + " " + (element.getAttribute("aria-label") || "")));
        const shadowText = textOf(reviewRoot);
        const visibleRangeMatch = shadowText.match(/(\d+)\s+(?:to|[\u2013-])\s+(\d+)\s+of\s+(\d+)\s+Reviews/i);

        return JSON.stringify({
          ok: true,
          url: currentUrl,
          supplied_url: suppliedUrl,
          title: document.title,
          resolved_product_id: resolvedProductId,
          bv_product_id: bvProductId,
          has_rating_summary_host: Boolean(ratingHost),
          has_rating_summary_shadow_root: Boolean(ratingRoot),
          has_review_host: Boolean(reviewHost),
          has_review_shadow_root: Boolean(reviewRoot),
          member_reviews_control_visible: Boolean(memberReviewsButton),
          visible_review_range: visibleRangeMatch ? {
            start: Number(visibleRangeMatch[1]),
            end: Number(visibleRangeMatch[2]),
            total: Number(visibleRangeMatch[3])
          } : null
        });
      } catch (error) {
        return JSON.stringify({ error: true, message: String(error && error.message || error) });
      }
    })()
    """.replace("__CONFIG__", json.dumps(config))

    print(js)


if __name__ == "__main__":
    main()
