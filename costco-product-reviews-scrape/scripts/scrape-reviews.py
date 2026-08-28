import argparse
import json
import sys


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-url", default="")
    parser.add_argument("--product-id", default="")
    parser.add_argument("--reviews-mode", choices=["all", "text-only"], default="all")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--max-reviews", type=int, default=0)
    parser.add_argument("--sort", default="relevancy:a1")
    parser.add_argument("--content-locales", default="en_CA,fr_CA,en_US,en_US")
    args = parser.parse_args()

    config = {
        "productUrl": args.product_url,
        "productId": args.product_id,
        "reviewsMode": args.reviews_mode,
        "limit": args.limit,
        "maxReviews": args.max_reviews,
        "sort": args.sort,
        "contentLocales": args.content_locales,
    }

    js = r"""
    (async () => {
      try {
        const config = __CONFIG__;
        const endpoint = "https://apps.bazaarvoice.com/bfd/v1/clients/Costco/api-products/cv2/resources/data/reviews.json";
        const displayCode = "2070_2_0-en_us";
        const bfdToken = "2070_2_0,native_review_form,en_US";

        function parseProductId(value) {
          const matches = String(value || "").match(/\d{8,}/g) || [];
          return matches.length ? matches[matches.length - 1] : "";
        }

        function asCleanString(value) {
          return value == null ? "" : String(value);
        }

        function normalizeLimit(value) {
          const parsed = Number(value);
          if (!Number.isFinite(parsed)) return 100;
          return Math.max(1, Math.min(100, Math.floor(parsed)));
        }

        function normalizeMaxReviews(value) {
          const parsed = Number(value);
          if (!Number.isFinite(parsed)) return 0;
          return Math.max(0, Math.floor(parsed));
        }

        function mapPhoto(photo) {
          const sizes = photo && photo.Sizes || {};
          return {
            id: asCleanString(photo && photo.Id),
            caption: asCleanString(photo && photo.Caption),
            normal: asCleanString(sizes.normal && sizes.normal.Url),
            thumbnail: asCleanString(sizes.thumbnail && sizes.thumbnail.Url),
            large: asCleanString(sizes.large && sizes.large.Url)
          };
        }

        function mapReview(review, index, fallbackProductName) {
          return {
            sequence: index + 1,
            id: asCleanString(review.Id),
            cid: asCleanString(review.CID),
            product_id: asCleanString(review.ProductId),
            product_name: asCleanString(review.OriginalProductName || fallbackProductName),
            rating: review.Rating == null ? null : Number(review.Rating),
            rating_range: review.RatingRange == null ? null : Number(review.RatingRange),
            is_ratings_only: review.IsRatingsOnly === true,
            title: asCleanString(review.Title),
            review_text: asCleanString(review.ReviewText),
            user_nickname: asCleanString(review.UserNickname),
            user_location: asCleanString(review.UserLocation),
            author_id: asCleanString(review.AuthorId),
            content_locale: asCleanString(review.ContentLocale),
            submission_time: asCleanString(review.SubmissionTime),
            last_moderated_time: asCleanString(review.LastModeratedTime),
            last_modification_time: asCleanString(review.LastModificationTime),
            verified_purchaser: Boolean(review.Badges && review.Badges.verifiedPurchaser),
            badges_order: Array.isArray(review.BadgesOrder) ? review.BadgesOrder : [],
            is_recommended: review.IsRecommended === undefined ? null : review.IsRecommended,
            total_feedback_count: review.TotalFeedbackCount == null ? null : Number(review.TotalFeedbackCount),
            total_positive_feedback_count: review.TotalPositiveFeedbackCount == null ? null : Number(review.TotalPositiveFeedbackCount),
            total_negative_feedback_count: review.TotalNegativeFeedbackCount == null ? null : Number(review.TotalNegativeFeedbackCount),
            helpfulness: review.Helpfulness == null ? null : Number(review.Helpfulness),
            total_comment_count: review.TotalCommentCount == null ? null : Number(review.TotalCommentCount),
            total_client_response_count: review.TotalClientResponseCount == null ? null : Number(review.TotalClientResponseCount),
            total_inappropriate_feedback_count: review.TotalInappropriateFeedbackCount == null ? null : Number(review.TotalInappropriateFeedbackCount),
            photos: Array.isArray(review.Photos) ? review.Photos.map(mapPhoto) : [],
            videos: Array.isArray(review.Videos) ? review.Videos : [],
            campaign_id: asCleanString(review.CampaignId),
            source_client: asCleanString(review.SourceClient),
            moderation_status: asCleanString(review.ModerationStatus),
            submission_id: asCleanString(review.SubmissionId),
            is_syndicated: review.IsSyndicated === true,
            pros: review.Pros == null ? null : review.Pros,
            cons: review.Cons == null ? null : review.Cons,
            context_data_values: review.ContextDataValues || {},
            secondary_ratings: review.SecondaryRatings || {},
            tag_dimensions: review.TagDimensions || {},
            comment_ids: Array.isArray(review.CommentIds) ? review.CommentIds : [],
            product_recommendation_ids: Array.isArray(review.ProductRecommendationIds) ? review.ProductRecommendationIds : []
          };
        }

        const bvProductId = window.BV &&
          window.BV.swat_reviews &&
          window.BV.swat_reviews.config &&
          window.BV.swat_reviews.config.productId || "";
        const sourceUrl = config.productUrl || window.location.href;
        const productId = config.productId || bvProductId || parseProductId(sourceUrl);
        if (!productId) {
          return JSON.stringify({
            error: true,
            message: "Could not resolve Costco product id. Provide --product-id or run from a Costco product page."
          });
        }

        const reviewsMode = config.reviewsMode || "all";
        const limit = normalizeLimit(config.limit);
        const maxReviews = normalizeMaxReviews(config.maxReviews);
        const contentLocales = config.contentLocales || "en_CA,fr_CA,en_US,en_US";
        const sort = config.sort || "relevancy:a1";
        const fetched = [];
        const pages = [];
        let offset = 0;
        let total = null;
        let productName = "";

        async function requestPage(pageOffset, pageLimit) {
          const params = new URLSearchParams();
          params.set("resource", "reviews");
          params.set("action", "REVIEWS_N_STATS");
          params.append("filter", "productid:eq:" + productId);
          params.append("filter", "contentlocale:eq:" + contentLocales);
          if (reviewsMode === "text-only") {
            params.append("filter", "isratingsonly:eq:false");
          }
          params.set("filter_reviews", "contentlocale:eq:" + contentLocales);
          params.set("include", "authors,products,comments");
          params.set("filteredstats", "reviews");
          params.set("Stats", "Reviews");
          params.set("limit", String(pageLimit));
          params.set("offset", String(pageOffset));
          params.set("limit_comments", "3");
          params.set("sort", sort);
          params.set("apiversion", "5.5");
          params.set("displaycode", displayCode);

          const url = endpoint + "?" + params.toString();
          const response = await fetch(url, { headers: { "Bv-Bfd-Token": bfdToken } });
          const contentType = response.headers.get("content-type") || "";
          if (!response.ok) {
            const body = await response.text().catch(() => "");
            throw new Error("Bazaarvoice request failed: HTTP " + response.status + " " + body.slice(0, 240));
          }
          if (!/json/i.test(contentType)) {
            const body = await response.text().catch(() => "");
            throw new Error("Bazaarvoice response was not JSON: " + contentType + " " + body.slice(0, 240));
          }

          const json = await response.json();
          const data = json.response || json;
          if (!data || !Array.isArray(data.Results)) {
            throw new Error("Bazaarvoice response shape changed. Top-level keys: " + Object.keys(json || {}).join(","));
          }
          return { url, data };
        }

        while (total === null || offset < total) {
          const remaining = maxReviews > 0 ? maxReviews - fetched.length : limit;
          if (maxReviews > 0 && remaining <= 0) break;
          const requestLimit = Math.min(limit, remaining);
          const page = await requestPage(offset, requestLimit);
          const results = page.data.Results || [];
          total = page.data.TotalResults == null ? results.length : Number(page.data.TotalResults);
          if (!productName && results[0] && results[0].OriginalProductName) {
            productName = results[0].OriginalProductName;
          }
          pages.push({
            offset,
            requested_limit: requestLimit,
            response_limit: page.data.Limit == null ? null : Number(page.data.Limit),
            count: results.length,
            total,
            url: page.url
          });
          fetched.push(...results);
          if (results.length === 0) break;
          offset += results.length;
        }

        const unique = new Map();
        for (const review of fetched) {
          if (review && review.Id && !unique.has(review.Id)) {
            unique.set(review.Id, review);
          }
        }

        const fallbackProductName = productName || document.title.replace(/\s*\|\s*Costco\s*$/i, "");
        const reviews = Array.from(unique.values()).map((review, index) => mapReview(review, index, fallbackProductName));
        const textReviews = reviews.filter((review) => review.review_text.trim().length > 0).length;
        const ratingOnlyReviews = reviews.filter((review) => review.is_ratings_only).length;

        return JSON.stringify({
          ok: true,
          scraped_at: new Date().toISOString(),
          source_url: sourceUrl,
          current_url: window.location.href,
          api_endpoint: endpoint,
          product_id: productId,
          product_name: fallbackProductName,
          reviews_mode: reviewsMode,
          sort,
          content_locales: contentLocales,
          total_reviews_reported: total,
          unique_reviews_scraped: reviews.length,
          text_reviews_scraped: textReviews,
          rating_only_reviews_scraped: ratingOnlyReviews,
          max_reviews: maxReviews,
          pages,
          reviews
        });
      } catch (error) {
        return JSON.stringify({
          error: true,
          message: String(error && error.message || error),
          stack: error && error.stack ? String(error.stack).split("\n").slice(0, 5) : []
        });
      }
    })()
    """.replace("__CONFIG__", json.dumps(config))

    print(js)


if __name__ == "__main__":
    main()
