import hashlib
import html
import os
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image, ImageDraw, ImageOps

USERNAME = "VonPeco"
CLIENT_ID = os.environ["MAL_CLIENT_ID"]
SITE = "https://vonpeco.github.io/mal-last5-completed"
API_URL = f"https://api.myanimelist.net/v2/users/{USERNAME}/animelist"
DOCS = Path("docs")
SCALE = 4


def read_config():
    config = {
        "width": int(os.getenv("POSTER_WIDTH", "79")),
        "height": int(os.getenv("POSTER_HEIGHT", "118")),
        "image_inset": int(os.getenv("POSTER_IMAGE_INSET", "3")),
        "background": os.getenv("POSTER_BG_COLOR", "#1D1D1D"),
        "border_color": os.getenv("POSTER_BORDER_COLOR", "#F5364F"),
        "border_width": float(os.getenv("POSTER_BORDER_WIDTH", "2")),
        "radius": float(os.getenv("POSTER_RADIUS", "5")),
    }
    if not 40 <= config["width"] <= 300 or not 60 <= config["height"] <= 450:
        raise ValueError("Outer container dimensions are outside the allowed range.")
    if not 0 <= config["image_inset"] <= 40:
        raise ValueError("Image inset must be between 0 and 40 px.")
    if config["width"] - 2 * config["image_inset"] < 8 or config["height"] - 2 * config["image_inset"] < 8:
        raise ValueError("The image frame is too small for the selected container and inset.")
    for key in ("background", "border_color"):
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", config[key]):
            raise ValueError(f"Invalid color for {key}: {config[key]}")
        config[key] = config[key].upper()
    if not 0 <= config["border_width"] <= 10:
        raise ValueError("Border width must be between 0 and 10 px.")
    if not 0 <= config["radius"] <= 30:
        raise ValueError("Corner radius must be between 0 and 30 px.")
    return config


def rgb(hex_color):
    value = hex_color.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def make_cover_frame(config, source=None):
    outer_w = config["width"] * SCALE
    outer_h = config["height"] * SCALE
    inset = config["image_inset"] * SCALE
    border = int(round(config["border_width"] * SCALE))
    radius = int(round(config["radius"] * SCALE))

    # The outside rectangle is a separate solid-color container.
    canvas = Image.new("RGBA", (outer_w, outer_h), rgb(config["background"]) + (255,))

    # The image frame is centered inside that container with an adjustable inset.
    x0, y0 = inset, inset
    x1, y1 = outer_w - inset, outer_h - inset
    frame_w, frame_h = x1 - x0, y1 - y0

    if config["border_width"] > 0:
        ImageDraw.Draw(canvas).rounded_rectangle(
            (x0, y0, x1 - 1, y1 - 1),
            radius=radius,
            outline=rgb(config["border_color"]) + (255,),
            width=border,
        )

    if source is not None:
        content_x0 = x0 + border
        content_y0 = y0 + border
        content_x1 = x1 - border
        content_y1 = y1 - border
        content_w = max(1, content_x1 - content_x0)
        content_h = max(1, content_y1 - content_y0)

        # Crop to fill the inner frame without distorting the original poster.
        fitted = ImageOps.fit(
            source.convert("RGB"),
            (content_w, content_h),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        ).convert("RGBA")

        inner_radius = max(0, radius - border)
        mask = Image.new("L", (content_w, content_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, content_w - 1, content_h - 1),
            radius=inner_radius,
            fill=255,
        )
        canvas.paste(fitted, (content_x0, content_y0), mask)

    return canvas.resize((config["width"], config["height"]), Image.Resampling.LANCZOS).convert("RGB")


def validate_entries(entries):
    for entry in entries:
        node = entry.get("node", {})
        if not isinstance(node.get("id"), int):
            raise ValueError(f"MyAnimeList no devolvió un ID válido para: {node.get('title', 'anime')}")
    return entries


def get_completed_entries():
    response = requests.get(
        API_URL,
        headers={"X-MAL-CLIENT-ID": CLIENT_ID},
        params={
            "status": "completed",
            "sort": "list_updated_at",
            "limit": 6,
            "fields": "main_picture",
        },
        timeout=30,
    )
    response.raise_for_status()
    return validate_entries(response.json().get("data", [])[:6])


def get_current_season_entries():
    headers = {"X-MAL-CLIENT-ID": CLIENT_ID}
    params = {
        "status": "watching",
        "sort": "list_updated_at",
        "limit": 100,
        "fields": "main_picture,status,media_type,start_season",
    }
    url = API_URL
    entries = []

    # Follow MAL pagination so the ten picks are selected from the full Watching list.
    while url:
        response = requests.get(url, headers=headers, params=params if url == API_URL else None, timeout=30)
        response.raise_for_status()
        payload = response.json()
        entries.extend(
            entry for entry in payload.get("data", [])
            if entry.get("node", {}).get("status") == "currently_airing"
        )
        url = (payload.get("paging") or {}).get("next")
        params = None

    return validate_entries(entries)[:12]


def get_cover(node):
    picture = node.get("main_picture") or {}
    url = picture.get("large") or picture.get("medium")
    if not url:
        return None
    response = requests.get(
        url,
        timeout=30,
        headers={"User-Agent": "MAL-Last6-Profile/1.0"},
    )
    response.raise_for_status()
    return Image.open(BytesIO(response.content)).convert("RGB")


def get_anime_url(node):
    anime_id = node["id"]
    title = node.get("title") or f"Anime {anime_id}"
    slug = title.replace(":", "_")
    slug = re.sub(r"[!?¡¿]+", "", slug)
    slug = re.sub(r"[^\w\s-]", "", slug, flags=re.UNICODE)
    slug = re.sub(r"\s+", "_", slug.strip())
    slug = quote(slug, safe="_-")
    return f"https://myanimelist.net/anime/{anime_id}/{slug}"


def write_redirect(slot, destination, title, redirect_root="go"):
    safe_destination = html.escape(destination, quote=True)
    safe_title = html.escape(title or "MyAnimeList", quote=True)
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="0;url={safe_destination}">
  <link rel="canonical" href="{safe_destination}">
  <title>Opening {safe_title}</title>
  <script>window.location.replace("{destination}");</script>
</head>
<body>
  <p>Opening <a href="{safe_destination}">{safe_title}</a> on MyAnimeList…</p>
</body>
</html>
"""
    redirect_dir = DOCS / redirect_root / str(slot)
    redirect_dir.mkdir(parents=True, exist_ok=True)
    (redirect_dir / "index.html").write_text(page, encoding="utf-8")


def make_bbcode(seasonal_count):
    def linked_cover(folder, slot, redirect_path):
        image_path = DOCS / folder / f"anime-{slot}.png"
        version = hashlib.sha256(image_path.read_bytes()).hexdigest()[:12]
        image_url = f"{SITE}/{folder}/anime-{slot}.png?v={version}"
        click_url = f"{SITE}/{redirect_path}/{slot}/"
        return f"[url={click_url}][img]{image_url}[/img][/url]"

    def image_row(folder, redirect_path, first, last):
        return "".join(
            linked_cover(folder, slot, redirect_path)
            for slot in range(first, last + 1)
        )

    def decorative(url):
        return f"[img]{url}[/img]"

    # Decorative artwork supplied for VonPeco's custom profile layout.
    decor = {
        "a": "https://i.imgur.com/HoVhMNY.jpeg",
        "b": "https://i.imgur.com/VsBHp2E.jpeg",
        "c": "https://i.imgur.com/cjuv0aE.jpeg",
        "d": "https://i.imgur.com/Pf3PIRa.jpeg",
        "e": "https://i.imgur.com/wQk0089.jpeg",
        "f": "https://i.imgur.com/9uQJipM.jpeg",
        "g": "https://i.imgur.com/n65xxAu.jpeg",
        "h": "https://i.imgur.com/U0d3jk5.jpeg",
        "i": "https://i.imgur.com/h1r5SVW.jpeg",
        "j": "https://i.imgur.com/u3VUcHi.jpeg",
    }

    # Two continuous rows, with decorative images framing the seasonal
    # and completed covers. Cache-busted cover URLs are regenerated each run.
    first_line = (
        decorative(decor["a"]) + decorative(decor["b"]) + decorative(decor["c"])
        + image_row("seasonal-covers", "seasonal/go", 1, min(6, seasonal_count))
        + decorative(decor["d"])
        + image_row("covers", "go", 1, 3)
        + decorative(decor["e"])
    )

    second_line = (
        decorative(decor["f"]) + decorative(decor["g"])
        + image_row("seasonal-covers", "seasonal/go", 7, min(12, seasonal_count))
        + decorative(decor["h"])
        + image_row("covers", "go", 4, 6)
        + decorative(decor["i"])
    )

    # Keep the final decorative footer image on its own line, matching
    # the user's supplied BBCode composition.
    return first_line + "\\n" + second_line + "\\n" + decorative(decor["j"])


def main():
    config = read_config()
    completed_entries = get_completed_entries()
    seasonal_entries = get_current_season_entries()
    cover_dir = DOCS / "covers"
    seasonal_cover_dir = DOCS / "seasonal-covers"
    cover_dir.mkdir(parents=True, exist_ok=True)
    seasonal_cover_dir.mkdir(parents=True, exist_ok=True)

    def generate_covers(entries, folder, redirect_root, slots):
        for slot in range(1, slots + 1):
            destination = f"https://myanimelist.net/profile/{USERNAME}"
            title = "Sin anime"
            source = None
            if slot <= len(entries):
                node = entries[slot - 1].get("node", {})
                anime_id = node["id"]
                title = node.get("title") or f"Anime {anime_id}"
                destination = get_anime_url(node)
                try:
                    source = get_cover(node)
                except Exception as exc:
                    raise RuntimeError(f"No se pudo descargar la portada de {title}: {exc}") from exc

            cover = make_cover_frame(config, source)
            cover.save(folder / f"anime-{slot}.png", format="PNG", optimize=True)
            write_redirect(slot, destination, title, redirect_root)
            print(f"{redirect_root} {slot}: {title} -> {destination}")

    generate_covers(completed_entries, cover_dir, "go", 6)
    generate_covers(seasonal_entries, seasonal_cover_dir, "seasonal/go", 12)

    bbcode = make_bbcode(len(seasonal_entries))
    (DOCS / "profile-bbcode.txt").write_text(bbcode + "\n", encoding="utf-8")

    width, height = config["width"], config["height"]
    decor_urls = [
        "https://i.imgur.com/HoVhMNY.jpeg",
        "https://i.imgur.com/VsBHp2E.jpeg",
        "https://i.imgur.com/cjuv0aE.jpeg",
        "https://i.imgur.com/Pf3PIRa.jpeg",
        "https://i.imgur.com/wQk0089.jpeg",
        "https://i.imgur.com/9uQJipM.jpeg",
        "https://i.imgur.com/n65xxAu.jpeg",
        "https://i.imgur.com/U0d3jk5.jpeg",
        "https://i.imgur.com/h1r5SVW.jpeg",
        "https://i.imgur.com/u3VUcHi.jpeg",
    ]

    def preview_img(src, alt=""):
        return f'<img src="{html.escape(src, quote=True)}" alt="{html.escape(alt, quote=True)}">'

    def preview_cover(folder, redirect, slot):
        return (
            f'<a href="{redirect}/{slot}/">'
            + preview_img(f"{folder}/anime-{slot}.png", f"Anime {slot}")
            + '</a>'
        )

    preview = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VonPeco - MAL anime covers</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; padding: 0; }}
.profile-layout {{ line-height: 0; white-space: nowrap; overflow-x: auto; }}
.profile-layout img {{ display: inline-block; vertical-align: middle; }}
.profile-layout a {{ display: inline-block; vertical-align: middle; }}
.profile-layout .decor {{ }}
.profile-layout .cover {{ width:{width}px; height:{height}px; }}
.profile-row {{ margin: 0; padding: 0; }}
</style>
</head>
<body>
<div class="profile-layout">
<div class="profile-row">
{preview_img(decor_urls[0], "Decorative image")}
{preview_img(decor_urls[1], "Decorative image")}
{preview_img(decor_urls[2], "Decorative image")}
"""
    preview += "".join(
        f'<a href="seasonal/go/{i}/">{preview_img(f"seasonal-covers/anime-{i}.png", f"Seasonal anime {i}")}</a>'
        for i in range(1, min(6, len(seasonal_entries)) + 1)
    )
    preview += preview_img(decor_urls[3], "Decorative image")
    preview += "".join(
        f'<a href="go/{i}/">{preview_img(f"covers/anime-{i}.png", f"Completed anime {i}")}</a>'
        for i in range(1, 4)
    )
    preview += preview_img(decor_urls[4], "Decorative image")
    preview += """</div>
<div class="profile-row">
"""
    preview += preview_img(decor_urls[5], "Decorative image")
    preview += preview_img(decor_urls[6], "Decorative image")
    preview += "".join(
        f'<a href="seasonal/go/{i}/">{preview_img(f"seasonal-covers/anime-{i}.png", f"Seasonal anime {i}")}</a>'
        for i in range(7, min(12, len(seasonal_entries)) + 1)
    )
    preview += preview_img(decor_urls[7], "Decorative image")
    preview += "".join(
        f'<a href="go/{i}/">{preview_img(f"covers/anime-{i}.png", f"Completed anime {i}")}</a>'
        for i in range(4, 7)
    )
    preview += preview_img(decor_urls[8], "Decorative image")
    preview += """</div>
<div class="profile-row">
"""
    preview += preview_img(decor_urls[9], "Decorative image")
    preview += """</div>
</div>
<p><a href="profile-bbcode.txt">BBCode para el perfil clásico de MAL</a></p>
</body>
</html>
"""
    (DOCS / "index.html").write_text(preview, encoding="utf-8")
    print(f"Created 6 completed covers and {len(seasonal_entries)} current-season covers.")
    print(
        f"Cover design: {width}x{height}, background {config['background']}; "
        f"inset {config['image_inset']}px; border {config['border_width']}px "
        f"{config['border_color']}; radius {config['radius']}px."
    )

if __name__ == "__main__":
    main()
