# Ai Bảo Hắn Tu Tiên — Web Reader

Static Vietnamese reader for **Ai Bảo Hắn Tu Tiên** (vol01). Chapter bodies live in `chapters/chuong-N.txt`; the browser loads `chapters.json` and fetches chapters on demand.

## Local preview

Serve the project root (required so `fetch()` works):

```bash
cd reader
python3 prepare_site.py   # rebuild from ../text/vol01
python3 -m http.server 8080
# open http://localhost:8080
```

## Rebuild chapters

```bash
python3 prepare_site.py
# repair metadata from deployed chapter files (no source needed):
python3 prepare_site.py --repair
# optional:
python3 prepare_site.py --source ../text/vol01 --out .
```

## Deploy to Vercel

Live: **https://ai-bao-han-tu-tien.vercel.app**

```bash
python3 prepare_site.py
git add chapters chapters.json cover.jpeg index.html vercel.json
git commit -m "Update reader content"
git push origin main
```

### CLI (optional)

```bash
npx vercel link --project ai-bao-han-reader   # once
npx vercel --prod
```

## Project layout

| Path | Role |
|------|------|
| `index.html` | Reader UI (lazy-load) |
| `chapters.json` | Metadata: `n`, `title`, `path`, `story` |
| `chapters/chuong-N.txt` | Chapter bodies |
| `cover.jpeg` | Cover image |
| `prepare_site.py` | Build script (not deployed) |
| `vercel.json` | Static site + cache headers |
