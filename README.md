# jrepp.com (Jekyll)

## Local dev

- `bundle install`
- `./scripts/serve.py`

## Publishing (local build for nginx)

Build the site into an out-of-source directory (git ignored) so nginx can serve it:

- `bundle install`
- `JEKYLL_ENV=production bundle exec jekyll build --destination build/site`

For RST-enabled builds, include the extra config:

- `JEKYLL_ENV=production bundle exec jekyll build --destination build/site --config _config.yml,_config.rst.yml`

Point nginx at `build/site` as the site root.

## reStructuredText (RST)

This site can support `.rst` via `jekyll-rst` (self-hosted builds).

- Install Ruby deps: `bundle install`
- System dependency: you may need `docutils` available on the host (package name varies by distro)
- Enable for serve/build:
  - `JEKYLL_ENABLE_RST=1 bundle install`
  - `JEKYLL_ENABLE_RST=1 bundle exec jekyll build --config _config.yml,_config.rst.yml`

## Dev via nginx (proxy to local Jekyll)

If you want `https://t1.jrepp.com/` to proxy to a local Jekyll dev server (instead of serving `_site/`), this repo includes:

- systemd unit template: `vendor/t1-hosting/systemd/jekyll-serve.service` (runs `./scripts/serve.py` on `127.0.0.1:4000`)
- nginx vhost template: `vendor/t1-hosting/nginx/gateway.https.conf` (routes `/` to static site by default; `X-Env: dev` → `127.0.0.1:4000`)
- gateway helper (requires sudo): `vendor/t1-hosting/svc` (`sudo ./svc bootstrap`)

LiveReload is enabled by default in `./scripts/serve.py` (disable with `JEKYLL_LIVERELOAD=0`).

To restart the server-side systemd unit (sudo-required), use: `sudo ./vendor/t1-hosting/scripts/restart_jekyll_serve.sh`

## Wayback archive restores

This repo includes a small script to restore historical snapshots of `jrepp.com` from the Internet Archive (Wayback Machine) into `archive/<timestamp>/`, and track restores in `archive/manifest.json`.

- List snapshots (root URL):
  - `python3 scripts/wayback_restore.py list --url jrepp.com/ --from-year 2025 --to-year 2025 --limit 200`
- Restore the first (earliest) snapshot automatically:
  - `python3 scripts/wayback_restore.py restore-auto --pick first --base-url http://jrepp.com/ --max-pages 250 --sleep-ms 200`
- Restore a sequence of snapshots (deduped + throttled):
  - `python3 scripts/wayback_restore.py restore-series --base-url http://jrepp.com/ --from-year 2002 --max-snapshots 50 --sleep-ms 250 --snapshot-sleep-ms 1500`
- Restore one snapshot:
  - `python3 scripts/wayback_restore.py restore --timestamp 20250101000000 --base-url http://jrepp.com/ --max-pages 250 --sleep-ms 200`
- Browse restores locally:
  - Start Jekyll and open `http://localhost:4000/archive/`

Notes:
- The script uses only the Python standard library (no install required).
- `scripts/requirements-wayback.txt` is optional if you want to use `waybackpy` for other Wayback workflows.

## Asset mirroring (make images local)

To avoid serving images/CSS/JS from remote `web.archive.org` URLs (or other third-party hosts), use these stdlib-only tools:

- Blogger export → Jekyll backup (mirrors images by default):
  - `python3 scripts/blogger_export_to_jekyll.py --blog-id 21851275` (disable with `--no-mirror-assets`)
- Blogspot Wayback restore → Jekyll `_blogspot` collection (mirrors static assets by default):
  - `python3 scripts/blogspot_to_jekyll.py --restore-dir <restore>/<14digits>` (disable with `--no-mirror-assets`)
- Existing Wayback snapshot under `archive/<timestamp>/`:
  - `python3 scripts/wayback_localize_assets.py --timestamp <timestamp>` (downloads `web.archive.org` asset URLs into `archive/<timestamp>/_assets/` and rewrites references)

All of the above require network access when mirroring is enabled.

### Blogspot restores (jacobrepp.blogspot.com)

- List snapshots:
  - `python3 scripts/wayback_restore.py list --url https://jacobrepp.blogspot.com/ --limit 50`
- Restore a snapshot to a separate output root:
  - `python3 scripts/wayback_restore.py restore --timestamp <14digits> --base-url https://jacobrepp.blogspot.com/ --out-root archive-blogspot --manifest archive-blogspot/manifest.json`
- Retry transient (non-404) failures from the manifest:
  - `python3 scripts/wayback_restore.py retry-failures --manifest archive-blogspot/manifest.json --timestamp <14digits> --sleep-ms 200`
- Convert restored post HTML into a Jekyll collection under `_blogspot/`:
  - `python3 scripts/blogspot_to_jekyll.py --restore-dir archive-blogspot/<14digits> --out-dir _blogspot`

## Full Blogger export (API-based)

For a complete export of `jacobrepp.blogspot.com` (including downloading images), this repo vendors `mrkmcnamee/blogger-export` under `tools/blogger-export/`.

1. Create OAuth credentials for the Blogger API and save JSON to `secrets/blogger/client_secret.json` (this path is gitignored).
2. Find the Blog ID from the Blogger dashboard URL (it appears as `blogID=...`).
3. Install `uv` (used to manage deps for `tools/blogger-export/`).
4. Run a full export:
   - `./scripts/blogger_full_export.py <BLOG_ID>`

Output is written to `exports/blogger/blogs/<BLOG_ID>/` (also gitignored). OAuth tokens are stored in `secrets/blogger/token.json`. By default the exporter uses a console-based auth flow; set `BLOGGER_EXPORT_AUTH=local` if you want the local-server/browser flow.

If you want to authorize from another device (e.g. your laptop) and have the callback hit this host over Tailscale, run with a fixed callback port and an externally reachable redirect URI (and ensure your OAuth client allows that exact redirect URI):

- `BLOGGER_EXPORT_AUTH=local ./scripts/blogger_full_export.py <BLOG_ID> --callback-host 0.0.0.0 --callback-port 8765 --redirect-uri http://100.83.36.123:8765/`

## OAuth via HTTPS (nginx + LetsEncrypt)

If you want secure Google OAuth redirects via `https://t1.jrepp.com/...`, this repo includes:

- Web helper app: `scripts/blogger_export_web.py` (FastAPI; stores token in `secrets/blogger/token.json`)
- nginx vhost templates: `vendor/t1-hosting/nginx/gateway.http.conf` and `vendor/t1-hosting/nginx/gateway.https.conf` (proxies `/blogger-export/` → `127.0.0.1:8787`)
- systemd unit template: `vendor/t1-hosting/systemd/blogger-export-web.service`
- gateway helper: `vendor/t1-hosting/svc`

Install (on the server):

- `sudo ./vendor/t1-hosting/svc bootstrap`

## t1-hosting repo

All hosting artifacts live under `vendor/t1-hosting/` (a dedicated git repo vendored into this site repo).

Then:

- Visit `https://t1.jrepp.com/blogger-export/` → “Authorize with Google”
- Run export via the UI link or `https://t1.jrepp.com/blogger-export/export?blog_id=21851275&full=1`

Google OAuth setup notes:

- For HTTPS redirects on a real domain, use an OAuth client of type **Web application** (Desktop/Installed clients typically only allow `http://localhost` redirects).
- Add this exact Authorized redirect URI (must match byte-for-byte): `https://t1.jrepp.com/blogger-export/oauth/callback`
- The app derives its redirect URI from `BLOGGER_WEB_BASE_URL` (default: `https://t1.jrepp.com/blogger-export`); if you change the public URL/path, update that env var in `vendor/t1-hosting/systemd/blogger-export-web.service`.
- If you use a separate OAuth client for the web flow, point `BLOGGER_WEB_CLIENT_SECRET` at it (this repo defaults to `secrets/blogger/blogger-export-web-secret.json`).
