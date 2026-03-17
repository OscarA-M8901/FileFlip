# FileFlip.pro — File Converter

Free, fast file conversions. No signup required.

## Supported Conversions
- JPG ↔ PNG (images)
- PDF ↔ DOCX (documents)
- PDF → JPG (pdf to image, multi-page = zip)
- MP4 → MP3 (audio extraction)

## Files in this project
- `index.html` — Frontend (the website)
- `server.py` — Python backend (handles conversions)
- `requirements.txt` — Python packages
- `railway.toml` — Railway deployment config
- `nixpacks.toml` — System dependencies (LibreOffice, ffmpeg, poppler)

## Deploying to Railway

1. Go to railway.app and open your project
2. Click "New Service" → "GitHub Repo"
3. Connect your GitHub account and push these files to a new repo
4. Railway will auto-detect and deploy
5. Go to Settings → Networking → Add a custom domain → type fileflip.pro

## Connecting your domain (Cloudflare)
After Railway gives you a deployment URL:
1. Go to Cloudflare → DNS
2. Add a CNAME record:
   - Name: @ (or www)
   - Target: your Railway URL (e.g. fileflip-production.up.railway.app)
   - Proxied: ON

## System dependencies (auto-installed by nixpacks.toml)
- LibreOffice — PDF ↔ DOCX conversion
- poppler_utils — PDF → JPG (pdftoppm)
- ffmpeg — MP4 → MP3 audio extraction
