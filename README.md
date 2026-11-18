# MAL Last 6 Completed

Generates **six separate PNG cover images** for the six most recently updated anime in the **Completed** list of MyAnimeList user \`VonPeco\`. Each cover links to the corresponding anime entry. GitHub Pages publishes the generated images, redirects, BBCode, and preview page.

## Classic MAL profile

After a successful workflow run, open:

\`https://vonpeco.github.io/mal-last5-completed/profile-bbcode.txt\`

Copy the complete BBCode into the classic MAL profile editor. It displays three covers per row (two rows). The image and redirect URLs remain stable, so the BBCode only needs to be pasted once.

## Cover design

The default design is 79 × 118 px, background \`#1D1D1D\`, border 1.5 px in \`#F5364F\`, and 5 px rounded corners. The generator accepts these workflow-dispatch inputs:

- \`poster_width\` (40–300 px)
- \`poster_height\` (60–450 px)
- \`background_color\` (hex)
- \`border_color\` (hex)
- \`border_width\` (0–10 px)
- \`border_radius\` (0–30 px)

The Peco's MAL Tools Chrome extension includes a visual editor and sends these settings to the Cloudflare Worker, which dispatches the GitHub Actions workflow. The Worker must use the compatible code provided with extension v1.3 (\`CLOUDFLARE-WORKER-UPDATE.js\`). Keep the existing \`GITHUB_TOKEN\` and \`UPDATE_SECRET\` secrets in Cloudflare.

## Initial setup

1. In **Settings → Secrets and variables → Actions**, create a repository secret named \`MAL_CLIENT_ID\` with the Client ID from the MyAnimeList application.
2. In **Settings → Pages**, select **Build and deployment → Source: GitHub Actions**.
3. The workflow runs on pushes to \`main\` and can also be started manually from **Actions**.

The repository must remain public to use GitHub Pages for free with GitHub Free. The MAL Client ID is stored as an Actions secret and is not written into repository files.

## Ordering

The API request uses \`status=completed\` and \`sort=list_updated_at\`, so ordering follows the most recently updated list entries and may differ from the exact date an anime was completed.

## Links

- Preview: \`https://vonpeco.github.io/mal-last5-completed/\`
- BBCode: \`https://vonpeco.github.io/mal-last5-completed/profile-bbcode.txt\`
- Cover 1: \`https://vonpeco.github.io/mal-last5-completed/covers/anime-1.png\`
- Redirect 1: \`https://vonpeco.github.io/mal-last5-completed/go/1/\`
