import argparse
import json
import sys


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-url", default="")
    parser.add_argument("--video-id", default="")
    parser.add_argument("--main-count", type=int, default=20)
    parser.add_argument("--reply-count", type=int, default=50)
    parser.add_argument("--max-main-pages", type=int, default=250)
    parser.add_argument("--max-reply-pages", type=int, default=50)
    parser.add_argument("--delay-ms", type=int, default=160)
    parser.add_argument("--region", default="US")
    parser.add_argument("--skip-replies", action="store_true")
    parser.add_argument("--omit-raw", action="store_true")
    args = parser.parse_args()

    config = {
        "videoUrl": args.video_url,
        "videoId": args.video_id,
        "mainCount": args.main_count,
        "replyCount": args.reply_count,
        "maxMainPages": args.max_main_pages,
        "maxReplyPages": args.max_reply_pages,
        "delayMs": args.delay_ms,
        "region": args.region,
        "skipReplies": args.skip_replies,
        "includeRaw": not args.omit_raw,
    }

    js = r"""
    (async () => {
      const config = __CONFIG__;
      const commentEndpoint = "https://www.tiktok.com/api/comment/list/";
      const replyEndpoint = "https://www.tiktok.com/api/comment/list/reply/";
      const signatureParams = ["X-Dynosaur", "msToken", "X-Bogus", "X-Gnarly"];

      function clean(value) {
        return value == null ? "" : String(value);
      }

      function clampInt(value, min, max, fallback) {
        const number = Number(value);
        if (!Number.isFinite(number)) return fallback;
        return Math.max(min, Math.min(max, Math.trunc(number)));
      }

      function sleep(ms) {
        return new Promise((resolve) => setTimeout(resolve, ms));
      }

      function parseVideoId(value) {
        const text = clean(value);
        const fromPath = text.match(/\/video\/(\d{10,})/);
        if (fromPath) return fromPath[1];
        const fromQuery = text.match(/[?&](?:aweme_id|item_id)=([0-9]{10,})/);
        return fromQuery ? fromQuery[1] : "";
      }

      function inferOs() {
        const platform = clean(navigator.platform).toLowerCase();
        const userAgent = clean(navigator.userAgent).toLowerCase();
        if (platform.includes("win") || userAgent.includes("windows")) return "windows";
        if (platform.includes("mac") || userAgent.includes("mac os")) return "mac";
        if (platform.includes("linux") || userAgent.includes("linux")) return "linux";
        return "web";
      }

      function appLanguage() {
        const language = clean(navigator.language || "en-US");
        return language.toLowerCase().startsWith("zh") ? "zh-Hans" : language;
      }

      function boolText(value) {
        return value ? "true" : "false";
      }

      function urlCandidatesFromPerformance() {
        if (!performance || typeof performance.getEntriesByType !== "function") return [];
        return performance
          .getEntriesByType("resource")
          .map((entry) => clean(entry && entry.name))
          .filter((url) => url.includes("/api/comment/list/"));
      }

      function removeSignatureParams(url) {
        for (const name of signatureParams) {
          url.searchParams.delete(name);
        }
        return url;
      }

      function findTemplateUrl(kind) {
        const candidates = urlCandidatesFromPerformance().reverse();
        const isReply = kind === "reply";
        for (const candidate of candidates) {
          if (isReply && candidate.includes("/api/comment/list/reply/")) {
            return removeSignatureParams(new URL(candidate, location.origin));
          }
          if (!isReply && candidate.includes("/api/comment/list/") && !candidate.includes("/api/comment/list/reply/")) {
            return removeSignatureParams(new URL(candidate, location.origin));
          }
        }
        if (isReply) {
          const topTemplate = findTemplateUrl("main");
          if (topTemplate) {
            topTemplate.pathname = "/api/comment/list/reply/";
            return removeSignatureParams(topTemplate);
          }
        }
        return null;
      }

      function fallbackTemplate(endpoint) {
        const sourceUrl = config.videoUrl || location.href;
        const url = new URL(endpoint, location.origin);
        const language = clean(navigator.language || "en-US");
        const common = {
          WebIdLastTime: String(Math.floor(Date.now() / 1000)),
          aid: "1988",
          app_language: appLanguage(),
          app_name: "tiktok_web",
          browser_language: language,
          browser_name: "Mozilla",
          browser_online: boolText(navigator.onLine),
          browser_platform: clean(navigator.platform),
          browser_version: clean(navigator.userAgent),
          channel: "tiktok_web",
          cookie_enabled: boolText(navigator.cookieEnabled),
          data_collection_enabled: "true",
          device_platform: "web_pc",
          focus_state: boolText(document.hasFocus()),
          from_page: "video",
          history_len: String((history && history.length) || 1),
          is_fullscreen: boolText(Boolean(document.fullscreenElement)),
          is_page_visible: boolText(document.visibilityState === "visible"),
          os: inferOs(),
          priority_region: clean(config.region || "US"),
          referer: sourceUrl,
          region: clean(config.region || "US"),
          root_referer: sourceUrl,
          screen_height: String((screen && screen.height) || innerHeight || ""),
          screen_width: String((screen && screen.width) || innerWidth || ""),
          tz_name: (Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"),
          user_is_login: "true",
          webcast_language: appLanguage()
        };
        for (const [key, value] of Object.entries(common)) {
          if (value !== "") url.searchParams.set(key, value);
        }
        return url;
      }

      function buildRequestUrl(template, endpoint, videoId, params) {
        const url = template ? new URL(template.toString()) : fallbackTemplate(endpoint);
        url.pathname = new URL(endpoint).pathname;
        removeSignatureParams(url);
        url.searchParams.set("aweme_id", videoId);
        url.searchParams.set("item_id", videoId);
        for (const [key, value] of Object.entries(params)) {
          url.searchParams.set(key, String(value));
        }
        return url.toString();
      }

      async function fetchJson(url) {
        const response = await fetch(url, { credentials: "include" });
        const text = await response.text();
        if (!text.trim()) {
          throw new Error(`TikTok returned an empty body for ${url.slice(0, 180)}`);
        }
        let json;
        try {
          json = JSON.parse(text);
        } catch (error) {
          throw new Error(`TikTok returned non-JSON HTTP ${response.status}: ${text.slice(0, 300)}`);
        }
        if (!response.ok || json.status_code) {
          throw new Error(`TikTok API failed HTTP ${response.status}: ${JSON.stringify(json).slice(0, 500)}`);
        }
        return json;
      }

      function detectLoginState() {
        const text = clean(document.body && document.body.innerText);
        return {
          has_upload_nav: text.includes("Upload") || text.includes("\u4e0a\u4f20"),
          has_messages_nav: text.includes("Messages") || text.includes("\u6d88\u606f"),
          has_login_prompt: text.includes("Log in") || text.includes("\u767b\u5f55")
        };
      }

      function convertComment(comment, kind, sequence) {
        const user = (comment && comment.user) || {};
        const item = {
          sequence,
          kind,
          cid: clean(comment && comment.cid),
          aweme_id: clean(comment && comment.aweme_id),
          parent_cid: kind === "reply" ? clean(comment && comment.reply_id) : null,
          reply_to_reply_id: clean(comment && comment.reply_to_reply_id),
          text: clean(comment && comment.text),
          create_time: comment && comment.create_time == null ? null : Number(comment.create_time),
          create_time_iso: comment && comment.create_time ? new Date(Number(comment.create_time) * 1000).toISOString() : null,
          digg_count: comment && comment.digg_count == null ? null : Number(comment.digg_count),
          reply_comment_total: comment && comment.reply_comment_total == null ? null : Number(comment.reply_comment_total),
          user_uid: clean(user.uid),
          user_unique_id: clean(user.unique_id),
          user_nickname: clean(user.nickname),
          user_sec_uid: clean(user.sec_uid)
        };
        if (config.includeRaw) item.raw = comment;
        return item;
      }

      async function scrapeMainComments(videoId, template, pageSize, maxPages, delayMs) {
        const commentsByCid = new Map();
        const pages = [];
        let cursor = 0;
        let reportedTotal = null;

        for (let pageIndex = 0; pageIndex < maxPages; pageIndex += 1) {
          const requestUrl = buildRequestUrl(template, commentEndpoint, videoId, {
            count: pageSize,
            cursor
          });
          const json = await fetchJson(requestUrl);
          const comments = Array.isArray(json.comments) ? json.comments : [];
          const nextCursor = Number(json.cursor || 0);
          const hasMore = Number(json.has_more || 0);
          if (json.total != null) reportedTotal = Number(json.total);

          pages.push({
            requested_cursor: cursor,
            requested_count: pageSize,
            next_cursor: nextCursor,
            has_more: hasMore,
            count: comments.length,
            total: json.total == null ? null : Number(json.total)
          });

          for (const comment of comments) {
            if (comment && comment.cid && !commentsByCid.has(comment.cid)) {
              commentsByCid.set(comment.cid, comment);
            }
          }

          if (!hasMore || comments.length === 0 || nextCursor === cursor) break;
          cursor = nextCursor;
          await sleep(delayMs);
        }

        return {
          rawComments: Array.from(commentsByCid.values()),
          pages,
          reportedTotal
        };
      }

      async function scrapeReplies(videoId, template, parentComments, pageSize, maxPages, delayMs) {
        const repliesByCid = new Map();
        const pages = [];
        const parents = parentComments.filter((comment) => Number(comment && comment.reply_comment_total || 0) > 0);

        for (const parent of parents) {
          let cursor = 0;
          const seenCursors = new Set();
          for (let pageIndex = 0; pageIndex < maxPages; pageIndex += 1) {
            const requestUrl = buildRequestUrl(template, replyEndpoint, videoId, {
              comment_id: parent.cid,
              count: pageSize,
              cursor
            });
            const json = await fetchJson(requestUrl);
            const comments = Array.isArray(json.comments) ? json.comments : [];
            const nextCursor = Number(json.cursor || 0);
            const hasMore = Number(json.has_more || 0);

            pages.push({
              parent_cid: clean(parent.cid),
              requested_cursor: cursor,
              requested_count: pageSize,
              next_cursor: nextCursor,
              has_more: hasMore,
              count: comments.length,
              total: json.total == null ? null : Number(json.total)
            });

            for (const reply of comments) {
              if (reply && reply.cid && !repliesByCid.has(reply.cid)) {
                repliesByCid.set(reply.cid, reply);
              }
            }

            if (!hasMore || comments.length === 0 || nextCursor === cursor || seenCursors.has(String(nextCursor))) break;
            seenCursors.add(String(cursor));
            cursor = nextCursor;
            await sleep(delayMs);
          }
          await sleep(delayMs);
        }

        return {
          rawReplies: Array.from(repliesByCid.values()),
          pages,
          parentCount: parents.length
        };
      }

      try {
        const sourceUrl = config.videoUrl || location.href;
        const videoId = clean(config.videoId) || parseVideoId(sourceUrl) || parseVideoId(location.href);
        if (!videoId) {
          throw new Error("Could not parse TikTok video id. Provide --video-url or --video-id.");
        }

        const mainCount = clampInt(config.mainCount, 1, 50, 20);
        const replyCount = clampInt(config.replyCount, 1, 50, 50);
        const maxMainPages = clampInt(config.maxMainPages, 1, 1000, 250);
        const maxReplyPages = clampInt(config.maxReplyPages, 1, 300, 50);
        const delayMs = clampInt(config.delayMs, 0, 5000, 160);
        const loginState = detectLoginState();
        const mainTemplate = findTemplateUrl("main");
        const replyTemplate = findTemplateUrl("reply") || mainTemplate;

        const mainResult = await scrapeMainComments(videoId, mainTemplate, mainCount, maxMainPages, delayMs);
        const replyResult = config.skipReplies
          ? { rawReplies: [], pages: [], parentCount: 0 }
          : await scrapeReplies(videoId, replyTemplate, mainResult.rawComments, replyCount, maxReplyPages, delayMs);

        const mainComments = mainResult.rawComments.map((comment, index) => convertComment(comment, "main", index + 1));
        const replyComments = replyResult.rawReplies.map((comment, index) => convertComment(comment, "reply", index + 1));
        const expectedReplyCountFromMain = mainResult.rawComments.reduce(
          (sum, comment) => sum + Number(comment && comment.reply_comment_total || 0),
          0
        );
        const replyApiTotalByParent = new Map();
        for (const page of replyResult.pages) {
          if (page.total != null) replyApiTotalByParent.set(page.parent_cid, Number(page.total));
        }
        const replyApiTotalSum = Array.from(replyApiTotalByParent.values()).reduce((sum, total) => sum + total, 0);

        return JSON.stringify({
          ok: true,
          scraped_at: new Date().toISOString(),
          source_url: sourceUrl,
          current_url: location.href,
          video_id: videoId,
          browser_mode_default: "chrome-direct",
          login_state: loginState,
          endpoints: {
            comments: commentEndpoint,
            replies: replyEndpoint
          },
          templates_found: {
            main: Boolean(mainTemplate),
            reply: Boolean(replyTemplate)
          },
          reported_total: mainResult.reportedTotal,
          main_comment_count: mainComments.length,
          parents_with_replies: replyResult.parentCount,
          expected_reply_count_from_main: expectedReplyCountFromMain,
          reply_api_total_sum: replyApiTotalSum || null,
          scraped_reply_count: replyComments.length,
          combined_comment_count: mainComments.length + replyComments.length,
          visible_reply_shortfall_from_main_count: Math.max(0, expectedReplyCountFromMain - replyComments.length),
          display_total_gap: mainResult.reportedTotal == null ? null : Number(mainResult.reportedTotal) - (mainComments.length + replyComments.length),
          main_pages: mainResult.pages,
          reply_pages: replyResult.pages,
          comments: mainComments.concat(replyComments)
        });
      } catch (error) {
        return JSON.stringify({
          ok: false,
          error: clean(error && error.message || error),
          stack: error && error.stack ? clean(error.stack).split("\n").slice(0, 6) : [],
          current_url: location.href,
          hint: "Open the TikTok video in a logged-in chrome-direct browser session, wait for comments to load, then run the helper again."
        });
      }
    })()
    """.replace("__CONFIG__", json.dumps(config))

    print(js)


if __name__ == "__main__":
    main()
