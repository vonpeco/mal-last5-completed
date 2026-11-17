import html
import os
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image

USERNAME = "VonPeco"
CLIENT_ID = os.environ["MAL_CLIENT_ID"]
SITE = "https://vonpeco.github.io/mal-last5-completed"
API_URL = f"https://api.myanimelist.net/v2/users/{USERNAME}/animelist"
POSTER_H = 112
POSTER_W = 72
BG = (35, 40, 49)
DOCS = Path("docs")


def get_entries():
    response = requests.get(
        API_URL,
        headers={"X-MAL-CLIENT-ID": CLIENT_ID},
        params={
            "status": "completed",
            "sort": "list_updated_at",
            "limit": 5,
            "fields": "main_picture",
        },
        timeout=30,
    )
    response.raise_for_status()
    entries = response.json().get("data", [])[:5]
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
        headers={"User-Agent": "MAL-Last5-Profile/1.0"},
    )
    response.raise_for_status()

    image = Image.open(BytesIO(response.content)).convert("RGB")

    # Resize proportionally to fit inside a 72x112 canvas.
    image.thumbnail((POSTER_W, POSTER_H), Image.Resampling.LANCZOS)

    # Center the image on a fixed 72x112 canvas.
    canvas = Image.new("RGB", (POSTER_W, POSTER_H), BG)
    x = (POSTER_W - image.width) // 2
    y = (POSTER_H - image.height) // 2
    canvas.paste(image, (x, y))

    return canvas


def get_anime_url(node):
    anime_id = node["id"]
    title = node.get("title") or f"Anime {anime_id}"

    # Build the title part of MAL's detail URL from the exact title returned by MAL.
    # Spaces become underscores; punctuation such as ":" becomes an underscore,
    # while exclamation marks are removed, matching the example URL format.
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

    row_one = " ".join(linked_cover(i) for i in range(1, 4))
    row_two = " ".join(linked_cover(i) for i in range(4, 6))
    return (
        "[center]\n"
        + row_one
        + "\n[/center]\n"
        + "[center]\n"
        + row_two
        + "\n[/center]"
    )


def main():
    entries = get_entries()
    cover_dir = DOCS / "covers"
    cover_dir.mkdir(parents=True, exist_ok=True)

    for slot in range(1, 6):
        destination = f"https://myanimelist.net/profile/{USERNAME}"
        title = "Sin anime"
        cover = Image.new("RGB", (POSTER_W, POSTER_H), BG)

        if slot <= len(entries):
            node = entries[slot - 1].get("node", {})
            anime_id = node["id"]
            title = node.get("title") or f"Anime {anime_id}"
            destination = get_anime_url(node)
            try:
                downloaded = get_cover(node)
                if downloaded is not None:
                    cover = downloaded
            except Exception as exc:
                raise RuntimeError(f"No se pudo descargar la portada de {title}: {exc}") from exc

        image_path = cover_dir / f"anime-{slot}.png"
        cover.save(image_path, format="PNG", optimize=True)
        write_redirect(slot, destination, title)
        print(f"Slot {slot}: {title} -> {destination}")

    bbcode = make_bbcode()
    (DOCS / "profile-bbcode.txt").write_text(bbcode + "\n", encoding="utf-8")
    (DOCS / "index.html").write_text(
        """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VonPeco - últimos 5 animes completados</title>
<style>
body {
    font-family: Arial, sans-serif;
    max-width: 900px;
    margin: 30px auto;
    padding: 0 16px;
}

.anime-list {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    align-content: flex-start;
    width: 236px;
    height: 176px;
    padding: 0;
    margin: 0 auto;
    list-style: none;
    border: 1px solid #bebebe;
    border-radius: 4px;
    box-sizing: border-box;
    overflow: visible;
}

.anime-list li {
    width: 72px;
    height: 112px;
    box-sizing: border-box;
}

.anime-list li:nth-child(n+4) {
    margin: -24px 10px 0 0;
}

.anime-list img {
    display: block;
    width: 72px;
    height: 112px;
}
</style>
</head>
<body>
<h1>Últimos 5 animes completados de VonPeco</h1>
<p>Cada portada abre el anime correspondiente en MyAnimeList.</p>
<ul class="anime-list">
""" + "".join(
            f'<li><a href="go/{i}/"><img src="covers/anime-{i}.png" alt="Anime {i}"></a></li>'
            for i in range(1, 6)
        ) + """
</ul>
<p><a href="profile-bbcode.txt">Ver el BBCode para pegar en el perfil clásico</a></p>
</body>
</html>
""",
        encoding="utf-8",
    )
    print(f"Created 5 individual covers and redirect links from {len(entries)} completed anime entries.")


if __name__ == "__main__":
    main()
