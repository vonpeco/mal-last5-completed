import os
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageDraw

USERNAME = "VonPeco"
CLIENT_ID = os.environ["MAL_CLIENT_ID"]
API_URL = f"https://api.myanimelist.net/v2/users/{USERNAME}/animelist"
POSTER_W, POSTER_H = 240, 340
GAP, MARGIN = 18, 18
BG = (17, 19, 24)
FRAME = (48, 53, 63)
PLACEHOLDER = (35, 40, 49)
OUT = Path("docs/covers.png")


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
    return response.json().get("data", [])[:5]


def get_cover(node):
    picture = node.get("main_picture") or {}
    url = picture.get("large") or picture.get("medium")
    if not url:
        return None
    response = requests.get(url, timeout=30, headers={"User-Agent": "MAL-Last5-Profile/1.0"})
    response.raise_for_status()
    image = Image.open(BytesIO(response.content)).convert("RGB")
    image.thumbnail((POSTER_W, POSTER_H), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (POSTER_W, POSTER_H), PLACEHOLDER)
    x = (POSTER_W - image.width) // 2
    y = (POSTER_H - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def main():
    entries = get_entries()
    width = MARGIN * 2 + POSTER_W * 3 + GAP * 2
    height = MARGIN * 2 + POSTER_H * 2 + GAP
    canvas = Image.new("RGB", (width, height), BG)

    positions = [
        (MARGIN, MARGIN),
        (MARGIN + POSTER_W + GAP, MARGIN),
        (MARGIN + (POSTER_W + GAP) * 2, MARGIN),
        ((width - (POSTER_W * 2 + GAP)) // 2, MARGIN + POSTER_H + GAP),
        ((width - (POSTER_W * 2 + GAP)) // 2 + POSTER_W + GAP, MARGIN + POSTER_H + GAP),
    ]

    for index in range(5):
        x, y = positions[index]
        cover = None
        if index < len(entries):
            node = entries[index].get("node", {})
            try:
                cover = get_cover(node)
            except Exception as exc:
                print(f"Could not download cover for {node.get('title', 'unknown')}: {exc}")
        if cover is None:
            cover = Image.new("RGB", (POSTER_W, POSTER_H), PLACEHOLDER)
        canvas.paste(cover, (x, y))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((x - 1, y - 1, x + POSTER_W, y + POSTER_H), outline=FRAME, width=2)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT, format="PNG", optimize=True)
    print(f"Created {OUT} with {len(entries)} completed anime entries.")


if __name__ == "__main__":
    main()
