# MAL Last 6 Completed

Generates **six separate PNG cover images** for the six most recently updated anime in the **Completed** list of MyAnimeList user `VonPeco`. Each cover links to the corresponding anime entry. GitHub Pages publishes the generated images, redirects, BBCode, and preview page.

## Cover composition and design

Each cover is composed of two distinct layers:

- **Outer container:** 79 × 118 px, solid background `#1D1D1D`.
- **Inner image frame:** centered with a default 5 px inset on every side.
- **Image:** cropped proportionally to fill the inner frame (cover behavior); never stretched.
- **Image border:** 2 px, color `#F5364F`, with 5 px rounded corners.

The visual editor in the Peco's MAL Tools Chrome extension lets you adjust outer dimensions, inset, background color, image border color and thickness, and image corner radius. The editor sends the values to the Cloudflare Worker, which dispatches GitHub Actions to regenerate all six PNGs.

The workflow also accepts these `workflow_dispatch` inputs:

- `poster_width` (40–300 px)
- `poster_height` (60–450 px)
- `poster_image_inset` (0–40 px)
- `background_color` (hex)
- `border_color` (hex)
- `border_width` (0–10 px)
- `border_radius` (0–30 px)

## Classic MAL profile

After a successful workflow run, open:

`https://vonpeco.github.io/mal-last5-completed/profile-bbcode.txt`

Copy the complete BBCode into the classic MAL profile editor. It displays three covers per row (two rows). The image and redirect URLs remain stable, so the BBCode only needs to be pasted once.

## Initial setup

1. In **Settings → Secrets and variables → Actions**, create a repository secret named `MAL_CLIENT_ID` with the Client ID from the MyAnimeList application.
2. In **Settings → Pages**, select **Build and deployment → Source: GitHub Actions**.
3. The workflow runs on pushes to `main` and can also be started manually from **Actions**.

The repository must remain public to use GitHub Pages for free with GitHub Free. The MAL Client ID is stored as an Actions secret and is not written into repository files.

## Ordering

The API request uses `status=completed` and `sort=list_updated_at`, so ordering follows the most recently updated list entries and may differ from the exact date an anime was completed.

## Links

- Preview: `https://vonpeco.github.io/mal-last5-completed/`
- BBCode: `https://vonpeco.github.io/mal-last5-completed/profile-bbcode.txt`
- Cover 1: `https://vonpeco.github.io/mal-last5-completed/covers/anime-1.png`
- Redirect 1: `https://vonpeco.github.io/mal-last5-completed/go/1/`
