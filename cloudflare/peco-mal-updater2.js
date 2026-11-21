// Cloudflare Worker for Peco's MAL updater + transparent analytics test pixel.
// Keeps the existing design-customization workflow intact.
// Analytics Engine binding: ANALYTICS
// Dataset: mal_profile_visits
// The pixel records approximate country/region/city and network metadata only.
// It does not store raw IP addresses or fingerprint individual visitors.
// Telegram alerts are best-effort and use a short isolate-local duplicate cooldown.

const recentTelegramNotifications = new Map();

function escapeHtml(value) {
  return String(value || "unknown").replace(/[&<>]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[char]);
}

async function sendTelegramNotification(env, details) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_CHAT_ID) return;

  const dedupeKey = [details.country, details.region, details.city, details.organization, details.referer].join("|");
  const now = Date.now();
  const previous = recentTelegramNotifications.get(dedupeKey) || 0;
  if (now - previous < 120000) return;
  recentTelegramNotifications.set(dedupeKey, now);
  for (const [key, timestamp] of recentTelegramNotifications) {
    if (now - timestamp > 120000) recentTelegramNotifications.delete(key);
  }

  const time = new Intl.DateTimeFormat("es-AR", {
    timeZone: "America/Argentina/Buenos_Aires",
    dateStyle: "short",
    timeStyle: "medium"
  }).format(new Date(now));
  const message = [
    "<b>Nueva solicitud al píxel del perfil MAL</b>",
    "País: " + escapeHtml(details.country),
    "Provincia/región: " + escapeHtml(details.region),
    "Ciudad: " + escapeHtml(details.city),
    "Red: " + escapeHtml(details.organization),
    "Origen: " + escapeHtml(details.referer),
    "Hora (Argentina): " + escapeHtml(time),
    "<i>Es una solicitud al píxel; no confirma por sí sola una visita humana.</i>"
  ].join("\\n");

  try {
    await fetch("https://api.telegram.org/bot" + env.TELEGRAM_BOT_TOKEN + "/sendMessage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: env.TELEGRAM_CHAT_ID, text: message, parse_mode: "HTML", disable_web_page_preview: true })
    });
  } catch (error) {
    // Notification failures must not prevent analytics or pixel delivery.
  }
}

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
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin") || "*";
    const corsHeaders = {
      "Access-Control-Allow-Origin": origin,
      "Access-Control-Allow-Methods": "POST, OPTIONS, GET",
      "Access-Control-Allow-Headers": "Content-Type, X-Update-Secret",
      "Vary": "Origin"
    };

    if (request.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

    // External stylesheet endpoint: logs a browser request without relying on an image pixel.
    if (request.method === "GET" && url.pathname === "/tracker.css") {
      const cf = request.cf || {};
      const referer = request.headers.get("Referer") || "";
      let refererHost = "none";
      try {
        if (referer) refererHost = new URL(referer).hostname;
      } catch {
        refererHost = "unavailable";
      }

      try {
        if (env.ANALYTICS) {
          env.ANALYTICS.writeDataPoint({
            blobs: [
              cf.country || "unknown",
              cf.region || "unknown",
              cf.city || "unknown",
              cf.asOrganization || "unknown",
              refererHost
            ],
            doubles: [1],
            indexes: ["mal-profile-css"]
          });
        }
      } catch (error) {
        // Analytics failures must not prevent the stylesheet from loading.
      }

      return new Response("/* Peco MAL profile stylesheet check */\\n:root { --peco-tracker-loaded: 1; }", {
        status: 200,
        headers: {
          ...corsHeaders,
          "Content-Type": "text/css; charset=utf-8",
          "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
          "Pragma": "no-cache",
          "Expires": "0",
          "X-Content-Type-Options": "nosniff"
        }
      });
    }

    // Transparent 1x1 pixel endpoint for aggregate location analytics.
    if (request.method === "GET" && url.pathname === "/pixel.gif") {
      const cf = request.cf || {};
      const referer = request.headers.get("Referer") || "";
      let refererHost = "none";
      try {
        if (referer) refererHost = new URL(referer).hostname;
      } catch {
        refererHost = "unavailable";
      }

      try {
        if (env.ANALYTICS) {
          env.ANALYTICS.writeDataPoint({
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
        }
      } catch (error) {
        // Analytics failures must not prevent the pixel from loading.
      }

      if (ctx && typeof ctx.waitUntil === "function") {
        ctx.waitUntil(sendTelegramNotification(env, {
          country: cf.country || "unknown",
          region: cf.region || "unknown",
          city: cf.city || "unknown",
          organization: cf.asOrganization || "unknown",
          referer: refererHost
        }));
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
      return new Response(JSON.stringify({ status: "online", service: "Peco MAL Updater" }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405, headers: corsHeaders });
    }

    const secret = request.headers.get("X-Update-Secret");
    if (!secret || secret !== env.UPDATE_SECRET) {
      return new Response("Unauthorized", { status: 401, headers: corsHeaders });
    }

    let payload;
    try {
      payload = await request.json();
    } catch {
      return new Response("Invalid JSON body", { status: 400, headers: corsHeaders });
    }

    const design = payload?.design;
    const inputs = {};
    if (design && typeof design === "object") {
      const width = Number(design.width);
      const height = Number(design.height);
      const imageInset = Number(design.imageInset ?? 5);
      const borderWidth = Number(design.borderWidth);
      const radius = Number(design.radius);
      const background = String(design.background || "");
      const borderColor = String(design.borderColor || "");

      if (!Number.isInteger(width) || width < 40 || width > 300 ||
          !Number.isInteger(height) || height < 60 || height > 450 ||
          !Number.isInteger(imageInset) || imageInset < 0 || imageInset > 40 ||
          width - 2 * imageInset < 8 || height - 2 * imageInset < 8 ||
          !Number.isFinite(borderWidth) || borderWidth < 0 || borderWidth > 10 ||
          !Number.isFinite(radius) || radius < 0 || radius > 30 ||
          !/^#[0-9a-fA-F]{6}$/.test(background) ||
          !/^#[0-9a-fA-F]{6}$/.test(borderColor)) {
        return new Response("Invalid design settings", { status: 400, headers: corsHeaders });
      }

      inputs.poster_width = String(width);
      inputs.poster_height = String(height);
      inputs.poster_image_inset = String(imageInset);
      inputs.background_color = background.toUpperCase();
      inputs.border_color = borderColor.toUpperCase();
      inputs.border_width = String(borderWidth);
      inputs.border_radius = String(radius);
    }

    const githubResponse = await fetch(
      "https://api.github.com/repos/vonpeco/mal-last5-completed/actions/workflows/update-covers.yml/dispatches",
      {
        method: "POST",
        headers: {
          "Authorization": "Bearer " + env.GITHUB_TOKEN,
          "Accept": "application/vnd.github+json",
          "Content-Type": "application/json",
          "X-GitHub-Api-Version": "2022-11-28",
          "User-Agent": "Peco-MAL-Updater"
        },
        body: JSON.stringify({ ref: "main", ...(Object.keys(inputs).length ? { inputs } : {}) })
      }
    );

    if (!githubResponse.ok) {
      const error = await githubResponse.text();
      return new Response(error, { status: githubResponse.status, headers: corsHeaders });
    }

    return new Response(JSON.stringify({ success: true, message: "Update triggered" }), {
      status: 202,
      headers: { ...corsHeaders, "Content-Type": "application/json" }
    });
  }
};