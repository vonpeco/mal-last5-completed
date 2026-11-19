// Cloudflare Worker for Peco's MAL updater + privacy-conscious location test pixel.
// Configure an Analytics Engine binding named ANALYTICS with dataset mal_profile_visits.
// This first test records aggregate request metadata only. It does NOT store IP addresses
// or attempt to identify individual visitors. Recurrence will be added only after verifying
// that MAL sends requests from visitors' browsers rather than an image proxy/cache.

const TRANSPARENT_GIF = new Uint8Array([
  0x47, 0x49, 0x46, 0x38, 0x39, 0x61,
  0x01, 0x00, 0x01, 0x00, 0x80, 0x00,
  0x00, 0x00, 0x00, 0x00, 0xff, 0xff,
  0xff, 0x21, 0xf9, 0x04, 0x01, 0x00,
  0x00, 0x00, 0x00, 0x2c, 0x00, 0x00,
  0x00, 0x00, 0x01, 0x00, 0x01, 0x00,
  0x00, 0x02, 0x02, 0x44, 0x01, 0x00, 0x3b
]);

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin") || "*";
    const corsHeaders = {
      "Access-Control-Allow-Origin": origin,
      "Access-Control-Allow-Methods": "POST, OPTIONS, GET",
      "Access-Control-Allow-Headers": "Content-Type, X-Update-Secret",
      "Vary": "Origin"
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    // Invisible 1x1 test pixel. Only coarse location/provider metadata is recorded.
    if (request.method === "GET" && url.pathname === "/pixel.gif") {
      const cf = request.cf || {};
      const referer = request.headers.get("Referer") || "";
      const refererHost = (() => {
        try { return referer ? new URL(referer).hostname : "none"; }
        catch { return "unavailable"; }
      })();

      try {
        env.ANALYTICS?.writeDataPoint({
          blobs: [
            cf.country || "unknown",
            cf.region || "unknown",
            cf.city || "unknown",
            cf.asOrganization || "unknown",
            refererHost
          ],
          doubles: [1],
          indexes: ["mal-profile-pixel"]
        });
      } catch (error) {
        // A failed analytics write must never prevent the pixel from loading.
      }

      return new Response(TRANSPARENT_GIF, {
        status: 200,
        headers: {
          ...corsHeaders,
          "Content-Type": "image/gif",
          "Content-Length": String(TRANSPARENT_GIF.byteLength),
          "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
          "Pragma": "no-cache",
          "Expires": "0"
        }
      });
    }

    if (request.method === "GET") {
      return new Response(JSON.stringify({
        status: "online",
        service: "Peco MAL Updater",
        analyticsPixel: "/pixel.gif"
      }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    if (request.method !== "POST") {
      return new Response("Method not allowed", {
        status: 405,
        headers: corsHeaders
      });
    }

    const secret = request.headers.get("X-Update-Secret");
    if (!secret || secret !== env.UPDATE_SECRET) {
      return new Response("Unauthorized", {
        status: 401,
        headers: corsHeaders
      });
    }

    const response = await fetch(
      "https://api.github.com/repos/vonpeco/mal-last5-completed/actions/workflows/update-covers.yml/dispatches",
      {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
          "Accept": "application/vnd.github+json",
          "X-GitHub-Api-Version": "2022-11-28",
          "User-Agent": "Peco-MAL-Updater"
        },
        body: JSON.stringify({ ref: "main" })
      }
    );

    if (!response.ok) {
      const error = await response.text();
      return new Response(error, {
        status: response.status,
        headers: corsHeaders
      });
    }

    return new Response(JSON.stringify({
      success: true,
      message: "Update triggered"
    }), {
      status: 202,
      headers: { ...corsHeaders, "Content-Type": "application/json" }
    });
  }
};
