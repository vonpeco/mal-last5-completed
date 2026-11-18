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
        "image_inset": int(os.getenv("POSTER_IMAGE_INSET", "5")),
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


def get_entries():
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
    entries = response.json().get("data", [])[:6]
    for entry in entries:
        node = entry.get("node", {})
        if not isinstance(node.get("id"), int):
            raise ValueError(f"MyAnimeList no devolvió un ID válido para: {node.get('title', 'anime')}")
    return entries


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


def write_redirect(slot, destination, title):
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
    redirect_dir = DOCS / "go" / str(slot)
    redirect_dir.mkdir(parents=True, exist_ok=True)
    (redirect_dir / "index.html").write_text(page, encoding="utf-8")


def make_bbcode():
    def linked_cover(slot):
        image_url = f"{SITE}/covers/anime-{slot}.png"
        click_url = f"{SITE}/go/{slot}/"
        return f"[url={click_url}][img]{image_url}[/img][/url]"

    # Keep image tags directly adjacent so MAL does not render text-space gaps.
    row_one = "".join(linked_cover(i) for i in range(1, 4))
    row_two = "".join(linked_cover(i) for i in range(4, 7))
    return "[center]" + row_one + "[/center]\n[center]" + row_two + "[/center]"


def main():
    config = read_config()
    entries = get_entries()
    cover_dir = DOCS / "covers"
    cover_dir.mkdir(parents=True, exist_ok=True)

    for slot in range(1, 7):
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
        cover.save(cover_dir / f"anime-{slot}.png", format="PNG", optimize=True)
        write_redirect(slot, destination, title)
        print(f"Slot {slot}: {title} -> {destination}")

    (DOCS / "profile-bbcode.txt").write_text(make_bbcode() + "\n", encoding="utf-8")

    width, height = config["width"], config["height"]
    inset = config["image_inset"]
    preview = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VonPeco - latest 6 completed anime</title>
<style>
body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 30px auto; padding: 0 16px; }}
.anime-list {{ display:grid; grid-template-columns:repeat(3, {width}px); gap:8px; justify-content:center; padding:0; margin:24px auto; list-style:none; }}
.anime-list li {{ width:{width}px; height:{height}px; overflow:hidden; background:{config['background']}; }}
.anime-list img {{ display:block; width:{width}px; height:{height}px; }}
</style>
</head>
<body>
<h1>Latest 6 completed anime of VonPeco</h1>
<p>Each cover opens its corresponding MyAnimeList entry.</p>
<ul class="anime-list">
"""
    preview += "".join(
        f'<li><a href="go/{i}/"><img src="covers/anime-{i}.png" alt="Anime {i}"></a></li>'
        for i in range(1, 7)
    )
    preview += """
</ul>
<p><a href="profile-bbcode.txt">BBCode for the classic profile</a></p>
</body>
</html>
"""
    (DOCS / "index.html").write_text(preview, encoding="utf-8")
    print(f"Created 6 covers from {len(entries)} completed anime entries.")
    print(
        f"Outer container: {width}x{height}, {config['background']}; "
        f"inner image inset: {inset}px; border: {config['border_width']}px "
        f"{config['border_color']}; radius: {config['radius']}px."
    )


if __name__ == "__main__":
    main()
