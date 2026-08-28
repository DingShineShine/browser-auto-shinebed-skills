import argparse
import json
import sys


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-url", default="")
    parser.add_argument("--item-part-number", default="")
    parser.add_argument("--review-part-number", default="")
    parser.add_argument("--reviews-mode", choices=["all", "text-only"], default="all")
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument("--max-pages", type=int, default=200)
    parser.add_argument("--sort", default="NEWEST")
    args = parser.parse_args()

    config = {
        "productUrl": args.product_url,
        "itemPartNumber": args.item_part_number,
        "reviewPartNumber": args.review_part_number,
        "reviewsMode": args.reviews_mode,
        "pageSize": args.page_size,
        "maxPages": args.max_pages,
        "sort": args.sort,
    }

    js = r"""
    (async () => {
      const config = __CONFIG__;
      const reviewEndpoint = "https://www.chewy.com/api/api-router/graphql";
      const pdpEndpoint = "https://www.chewy.com/api/pdp/graphql";

      const reviewsQuery = `
        query SubgraphReviews($partNumber: ID!, $pageRequestInput: NumberedPageRequestInput, $filter: ReviewFiltersInput, $sort: ReviewSort, $includePetProfileSnapshots: Boolean!) {
          product(partNumber: $partNumber) {
            id
            reviewsPage(pageRequestInput: $pageRequestInput, filter: $filter, sort: $sort) {
              hasNextPage
              totalResults
              results {
                id
                contentId
                helpfulness
                rating
                submittedAt
                submittedBy
                contributorBadge
                isIncentivized
                text: reviewText
                title
                isVerified
                paginatedPhotos {
                  results {
                    __typename
                    caption
                    fullImage: normalUrl
                    thumbnail: thumbnailUrl
                  }
                  __typename
                }
                petProfileSnapshots @include(if: $includePetProfileSnapshots) {
                  id
                  age
                  breed
                  name
                  petType
                  petId
                  lifeStage
                  avatarUrl
                  __typename
                }
                __typename
              }
              __typename
            }
            __typename
          }
        }`;

      const itemCandidateQuery = `
        query ItemReviewCandidate($id: String!) {
          item(id: $id) {
            id
            partNumber
            product {
              id
              partNumber
              __typename
            }
            __typename
          }
        }`;

      function clean(value) {
        return value == null ? "" : String(value);
      }

      function normalizePartNumber(value) {
        const match = clean(value).match(/\d{5,}/);
        return match ? match[0] : "";
      }

      function parseItemPartNumberFromUrl(value) {
        const match = clean(value).match(/\/dp\/(\d{5,})(?:[/?#]|$)/i);
        return match ? match[1] : "";
      }

      function parseCompactCount(value) {
        const text = clean(value).replace(/,/g, "").trim();
        const match = text.match(/^(\d+(?:\.\d+)?)(k)?$/i);
        if (!match) return null;
        const base = Number(match[1]);
        if (!Number.isFinite(base)) return null;
        return Math.round(base * (match[2] ? 1000 : 1));
      }

      function parseVisibleRatingsCount() {
        const root = document.querySelector("#reviews") || document.body;
        const text = clean(root && root.innerText);
        const ratingMatch = text.match(/(\d[\d,.]*(?:\.\d+)?\s*k?)\s+Ratings\b/i);
        if (!ratingMatch) return null;
        return parseCompactCount(ratingMatch[1].replace(/\s+/g, ""));
      }

      function addCandidate(list, value, source) {
        const partNumber = normalizePartNumber(value);
        if (!partNumber) return;
        if (!list.some((candidate) => candidate.partNumber === partNumber)) {
          list.push({ partNumber, source });
        }
      }

      function collectCandidatesFromHtml(list) {
        const html = document.documentElement ? document.documentElement.innerHTML : "";
        const patterns = [
          /["']partNumber["']\s*:\s*["']?(\d{5,})["']?/gi,
          /["']productPartNumber["']\s*:\s*["']?(\d{5,})["']?/gi,
          /["']parentPartNumber["']\s*:\s*["']?(\d{5,})["']?/gi,
          /["']parentProductPartNumber["']\s*:\s*["']?(\d{5,})["']?/gi,
          /["']catalogEntryId["']\s*:\s*["']?(\d{5,})["']?/gi
        ];
        for (const pattern of patterns) {
          let match;
          let scanned = 0;
          while ((match = pattern.exec(html)) && scanned < 100) {
            addCandidate(list, match[1], "page-html");
            scanned += 1;
          }
        }
      }

      async function collectCandidatesFromPdpApi(list, itemPartNumber) {
        if (!itemPartNumber) return;
        const body = {
          operationName: "ItemReviewCandidate",
          variables: { id: itemPartNumber },
          extensions: {},
          query: itemCandidateQuery
        };
        try {
          const response = await fetch(pdpEndpoint, {
            method: "POST",
            headers: {
              "accept": "*/*",
              "content-type": "application/json",
              "apollo-require-preflight": "true"
            },
            body: JSON.stringify(body),
            credentials: "include"
          });
          const json = await response.json();
          const item = json && json.data && json.data.item;
          addCandidate(list, item && item.partNumber, "pdp-item.partNumber");
          addCandidate(list, item && item.product && item.product.partNumber, "pdp-item.product.partNumber");
        } catch (error) {
          addCandidate(list, itemPartNumber, "pdp-api-fallback");
        }
      }

      async function requestReviewsPage(partNumber, page, pageSize, sort) {
        const body = {
          operationName: "SubgraphReviews",
          variables: {
            partNumber,
            pageRequestInput: { size: pageSize, page },
            filter: {},
            sort,
            includePetProfileSnapshots: true
          },
          extensions: {},
          query: reviewsQuery
        };
        const response = await fetch(reviewEndpoint, {
          method: "POST",
          headers: {
            "accept": "*/*",
            "content-type": "application/json",
            "apollo-require-preflight": "true",
            "x-chewy-component-id": "pdp-page"
          },
          body: JSON.stringify(body),
          credentials: "include"
        });
        const text = await response.text();
        let json;
        try {
          json = JSON.parse(text);
        } catch (error) {
          throw new Error(`GraphQL returned non-JSON HTTP ${response.status}: ${text.slice(0, 240)}`);
        }
        if (!response.ok || json.errors) {
          throw new Error(`GraphQL failed HTTP ${response.status}: ${JSON.stringify(json.errors || json).slice(0, 500)}`);
        }
        const pageData = json.data && json.data.product && json.data.product.reviewsPage;
        if (!pageData || !Array.isArray(pageData.results)) {
          throw new Error(`Unexpected GraphQL response shape: ${JSON.stringify(json).slice(0, 500)}`);
        }
        return pageData;
      }

      async function resolveReviewPartNumber(itemPartNumber, pageSize, sort) {
        const candidates = [];
        addCandidate(candidates, config.reviewPartNumber, "argument.reviewPartNumber");
        addCandidate(candidates, itemPartNumber, "item-part-number");
        await collectCandidatesFromPdpApi(candidates, itemPartNumber);
        collectCandidatesFromHtml(candidates);

        const visibleRatingsCount = parseVisibleRatingsCount();
        const tested = [];
        let firstValid = null;
        for (const candidate of candidates.slice(0, 60)) {
          try {
            const page = await requestReviewsPage(candidate.partNumber, 0, Math.min(pageSize, 5), sort);
            const total = page.totalResults == null ? page.results.length : Number(page.totalResults);
            const entry = {
              part_number: candidate.partNumber,
              source: candidate.source,
              total_results: Number.isFinite(total) ? total : null,
              sample_count: page.results.length,
              matches_visible_ratings_count: visibleRatingsCount != null && total === visibleRatingsCount
            };
            tested.push(entry);
            if (!firstValid && total > 0) firstValid = entry;
            if (entry.matches_visible_ratings_count || config.reviewPartNumber) {
              return { partNumber: candidate.partNumber, source: candidate.source, visibleRatingsCount, tested };
            }
          } catch (error) {
            tested.push({
              part_number: candidate.partNumber,
              source: candidate.source,
              error: clean(error && error.message || error).slice(0, 300)
            });
          }
        }
        if (firstValid) {
          return { partNumber: firstValid.part_number, source: `${firstValid.source}:first-valid`, visibleRatingsCount, tested };
        }
        throw new Error(`Could not resolve a Chewy review part number. Tested candidates: ${JSON.stringify(tested).slice(0, 1200)}`);
      }

      function mapPhoto(photo) {
        return {
          caption: clean(photo && photo.caption),
          full_image: clean(photo && photo.fullImage),
          thumbnail: clean(photo && photo.thumbnail)
        };
      }

      function mapReview(review, sequence) {
        const photosPage = review && review.paginatedPhotos;
        return {
          sequence,
          id: clean(review && review.id),
          content_id: clean(review && review.contentId),
          rating: review && review.rating == null ? null : Number(review.rating),
          title: clean(review && review.title),
          review_text: clean(review && review.text),
          submitted_by: clean(review && review.submittedBy),
          submitted_at: clean(review && review.submittedAt),
          helpfulness: review && review.helpfulness == null ? null : Number(review.helpfulness),
          contributor_badge: review && review.contributorBadge == null ? null : review.contributorBadge,
          is_incentivized: review && review.isIncentivized == null ? null : Boolean(review.isIncentivized),
          is_verified: review && review.isVerified == null ? null : Boolean(review.isVerified),
          photos: Array.isArray(photosPage && photosPage.results) ? photosPage.results.map(mapPhoto) : [],
          pet_profile_snapshots: Array.isArray(review && review.petProfileSnapshots) ? review.petProfileSnapshots : []
        };
      }

      function hasReviewText(review) {
        return clean(review.title).trim().length > 0 || clean(review.review_text).trim().length > 0;
      }

      function ratingCounts(reviews) {
        const counts = {};
        for (const review of reviews) {
          const key = review.rating == null ? "null" : String(review.rating);
          counts[key] = (counts[key] || 0) + 1;
        }
        return counts;
      }

      try {
        const sourceUrl = config.productUrl || window.location.href;
        const itemPartNumber = normalizePartNumber(config.itemPartNumber) || parseItemPartNumberFromUrl(sourceUrl);
        const pageSize = Math.max(1, Math.min(50, Number(config.pageSize) || 50));
        const maxPages = Math.max(1, Number(config.maxPages) || 200);
        const sort = clean(config.sort || "NEWEST");
        const resolver = await resolveReviewPartNumber(itemPartNumber, pageSize, sort);
        const fetched = [];
        const pages = [];

        for (let page = 0; page < maxPages; page += 1) {
          const pageData = await requestReviewsPage(resolver.partNumber, page, pageSize, sort);
          const results = pageData.results || [];
          pages.push({
            page,
            requested_size: pageSize,
            count: results.length,
            total_results: pageData.totalResults == null ? null : Number(pageData.totalResults),
            has_next_page: Boolean(pageData.hasNextPage)
          });
          fetched.push(...results);
          if (!pageData.hasNextPage || results.length === 0) break;
        }

        const unique = new Map();
        for (const review of fetched) {
          if (review && review.id && !unique.has(review.id)) {
            unique.set(review.id, review);
          }
        }

        let reviews = Array.from(unique.values()).map((review, index) => mapReview(review, index + 1));
        const allReviewCount = reviews.length;
        const textReviewCount = reviews.filter(hasReviewText).length;
        if (config.reviewsMode === "text-only") {
          reviews = reviews.filter(hasReviewText).map((review, index) => ({ ...review, sequence: index + 1 }));
        }

        return JSON.stringify({
          ok: true,
          scraped_at: new Date().toISOString(),
          source_url: sourceUrl,
          current_url: window.location.href,
          endpoint: reviewEndpoint,
          item_part_number: itemPartNumber,
          review_part_number: resolver.partNumber,
          review_part_number_source: resolver.source,
          reviews_mode: config.reviewsMode,
          sort,
          visible_ratings_count: resolver.visibleRatingsCount,
          total_reviews_reported: pages.length ? pages[0].total_results : null,
          unique_reviews_scraped: reviews.length,
          all_reviews_scraped_before_mode_filter: allReviewCount,
          text_reviews_scraped: config.reviewsMode === "text-only" ? reviews.length : textReviewCount,
          rating_only_or_blank_scraped: reviews.filter((review) => !hasReviewText(review)).length,
          rating_counts: ratingCounts(reviews),
          max_pages: maxPages,
          pages,
          resolver: {
            candidates_tested: resolver.tested
          },
          reviews
        });
      } catch (error) {
        return JSON.stringify({
          ok: false,
          error: clean(error && error.message || error),
          stack: error && error.stack ? clean(error.stack).split("\n").slice(0, 5) : []
        });
      }
    })()
    """.replace("__CONFIG__", json.dumps(config))

    print(js)


if __name__ == "__main__":
    main()
