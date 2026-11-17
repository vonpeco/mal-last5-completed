# MAL Last 5 Completed

Automatically creates a PNG containing the five most recently updated anime entries in the public **Completed** list for `VonPeco`.

- Layout: three covers in the first row, two centered below.
- No labels or captions.
- Refresh: every six hours (plus manual run).
- Public image: `https://vonpeco.github.io/mal-last5-completed/covers.png`

## One-time setup

1. In **Settings → Secrets and variables → Actions**, create a repository secret named `MAL_CLIENT_ID` and paste the Client ID from your MyAnimeList API application.
2. In **Settings → Pages**, set **Build and deployment → Source** to **GitHub Actions**.
3. Open **Actions → Update MAL cover image → Run workflow** for the first run.

The repository must remain public for free GitHub Pages hosting. The Client ID is stored as an Actions secret and is not written into the source files.

The image is based on MAL's `list_updated_at` sort order. Editing an existing list entry can therefore move it up the list; this is not necessarily the same as sorting by the original finish date.

## Troubleshooting

If the action fails, open its run under **Actions** and inspect the failed step. Check that the secret is named exactly `MAL_CLIENT_ID`, that its value is copied correctly, and that the MAL list is public.
