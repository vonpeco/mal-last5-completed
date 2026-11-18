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

    return validate_entries(entries)[:10]


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

    def rows(count, folder, redirect_path):
        blocks = []
        for start in range(1, count + 1, 3):
            row = "".join(
                linked_cover(folder, slot, redirect_path)
                for slot in range(start, min(start + 3, count + 1))
            )
            blocks.append("[center]" + row + "[/center]")
        return "\\n".join(blocks)

    completed = "[center][b]Últimos 6 animes completados[/b][/center]\\n" + rows(6, "covers", "go")
    seasonal_heading = "[center][b]Series que estoy viendo de la temporada actual[/b][/center]"
    seasonal = rows(seasonal_count, "seasonal-covers", "seasonal/go") if seasonal_count else "[center]No hay series en emisión en tu lista Watching.[/center]"
    return completed + "\\n\\n" + seasonal_heading + "\\n" + seasonal

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
    generate_covers(seasonal_entries, seasonal_cover_dir, "seasonal/go", 10)

    bbcode = make_bbcode(len(seasonal_entries))
    (DOCS / "profile-bbcode.txt").write_text(bbcode + "\\n", encoding="utf-8")

    width, height = config["width"], config["height"]
    preview = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VonPeco - MAL anime covers</title>
<style>
body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 30px auto; padding: 0 16px; }}
.anime-list {{ display:grid; grid-template-columns:repeat(3, {width}px); gap:8px; justify-content:center; padding:0; margin:16px auto 28px; list-style:none; }}
.anime-list li {{ width:{width}px; height:{height}px; overflow:hidden; background:{config['background']}; }}
.anime-list img {{ display:block; width:{width}px; height:{height}px; }}
h2 {{ text-align:center; }}
</style>
</head>
<body>
<h2>Últimos 6 animes completados</h2>
<ul class="anime-list">
"""
    preview += "".join(
        f'<li><a href="go/{i}/"><img src="covers/anime-{i}.png" alt="Completed anime {i}"></a></li>'
        for i in range(1, 7)
    )
    preview += """
</ul>
<h2>Series que estoy viendo de la temporada actual</h2>
<ul class="anime-list">
"""
    preview += "".join(
        f'<li><a href="seasonal/go/{i}/"><img src="seasonal-covers/anime-{i}.png" alt="Current seasonal anime {i}"></a></li>'
        for i in range(1, len(seasonal_entries) + 1)
    )
    preview += """
</ul>
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
