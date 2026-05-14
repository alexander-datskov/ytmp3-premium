# ytmp3-premium

A Flask + Socket.IO web app that converts YouTube videos to audio using `yt-dlp` + `ffmpeg`.

## Run locally

1. Clone the repo:
   ```bash
   git clone https://github.com/alexander-datskov/ytmp3-premium && cd ytmp3-premium
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
   On Windows:
   ```bat
   venv\Scripts\activate.bat
   ```
3. Install dependencies and system packages:
   ```bash
   bash setup.sh
   ```
4. Start the app:
   ```bash
   python web-conv.py
   ```

## Add to your GitHub repo

If this code is already in your local folder and you want it on your own GitHub repo:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

If this repo already has git history, just update `origin` and push.

## Deploy on Render (recommended)

This repository includes:
- `Dockerfile` (installs Python deps + `ffmpeg`)
- `requirements.txt`
- `render.yaml`

### Option A: Blueprint deploy (render.yaml)
1. Push this repo to GitHub.
2. In Render, click **New +** → **Blueprint**.
3. Connect your repo and deploy.

### Option B: Manual web service
1. In Render, create a **Web Service** from this GitHub repo.
2. Choose **Environment: Docker**.
3. Deploy.

The app listens on port `1234` and binds to `0.0.0.0`.

## Notes

- Output files are stored in `OUTPUT_DIR` (defaults to `~/ytmp3-premium/music-output`).
- In container deploys, `OUTPUT_DIR` defaults to `/app/music-output` via Docker env.
- Cloudflare tunnel autostart is disabled by default in deployments.
  - To enable it: set `ENABLE_CLOUDFLARE_TUNNEL=true`.
