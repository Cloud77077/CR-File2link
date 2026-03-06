# Telegram File Link Bot

Turn files sent to your Telegram bot into:

- Direct download links
- Streaming links
- A browser player page (video/audio)

This guide is written for both technical and non-technical users.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/kakarotoncloud/CR-F2L/blob/cursor/telegram-file-link-bot-99e0/colab_setup.ipynb)

---

## 1) What this project does

When a user sends a file to your bot:

1. Bot receives the file on Telegram.
2. Bot stores and indexes it in SQLite.
3. Bot generates a secure expiring token.
4. Bot sends back:
   - Download link
   - Stream/player link

Supported file types:

- Documents
- Videos
- Audio
- Photos
- Voice notes
- Animations

---

## 2) Main features

- Async stack (Pyrogram + FastAPI + aiosqlite)
- Signed expiring links
- Byte-range streaming support
- Optional HLS output with FFmpeg
- Admin commands:
  - `/stats`
  - `/users`
  - `/broadcast <message>`
- User command:
  - `/expire <minutes|default>`
- Basic rate limiting
- Logging

---

## 3) Project structure

```text
telegram-file-link-bot/
|
|-- bot/
|   |-- __init__.py
|   |-- main.py
|   |-- handlers.py
|   |-- config.py
|   `-- database.py
|
|-- server/
|   |-- __init__.py
|   |-- api.py
|   `-- streaming.py
|
|-- templates/
|   `-- player.html
|
|-- utils/
|   |-- __init__.py
|   `-- file_manager.py
|
|-- deploy/
|   |-- telegram-file-link-bot.service
|   `-- nginx.conf.example
|
|-- .env.example
|-- requirements.txt
|-- Procfile
|-- runtime.txt
|-- colab_setup.ipynb
`-- README.md
```

---

## 4) Before you start (important)

You need these 3 values from Telegram:

1. `BOT_TOKEN` (from BotFather)
2. `API_ID` (from my.telegram.org)
3. `API_HASH` (from my.telegram.org)

If you do not have them yet:

- Open Telegram and chat with **@BotFather**
- Create bot: `/newbot`
- Save the token
- Go to https://my.telegram.org -> API development tools
- Create app and copy API ID and API HASH

---

## 5) Environment variables (simple explanation)

Copy `.env.example` to `.env` and edit values.

Required:

- `BOT_TOKEN` -> your bot token
- `API_ID` -> your telegram API ID
- `API_HASH` -> your telegram API hash
- `PUBLIC_BASE_URL` -> public URL users will open (example: `https://files.example.com`)

Important optional:

- `ADMIN_IDS` -> your Telegram numeric user ID(s), comma-separated
- `LINK_SIGNING_SECRET` -> long random secret string
- `LINK_EXPIRY_SECONDS` -> default link expiry (86400 = 24h)
- `MAX_FILE_SIZE_MB` -> upload size limit

---

## 6) Fastest path for beginners: Google Colab

If you are non-technical, start here.

### One-click open

Click this direct link:

- https://colab.research.google.com/github/kakarotoncloud/CR-F2L/blob/cursor/telegram-file-link-bot-99e0/colab_setup.ipynb

### Steps

1. Click the **Open in Colab** button above.
2. Run cells from top to bottom.
3. Enter:
   - BOT TOKEN
   - API ID
   - API HASH
   - Public URL (optional)
   - Port
4. Notebook installs dependencies.
5. Notebook starts bot + API.
6. Notebook prints running status and URL.

### Note

If you want public links from Colab, use a tunnel (Cloudflare Tunnel or ngrok), then set that URL as `PUBLIC_BASE_URL`.

---

## 7) Local run (developer mode)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with your values
python -m bot.main
```

Health check:

```bash
curl http://127.0.0.1:8080/health
```

Expected:

```json
{"status":"ok"}
```

---

## 8) Bot commands

### User commands

- `/start` -> intro
- `/help` -> help menu
- `/expire <minutes>` -> custom expiry for your links
- `/expire default` -> return to default expiry

### Admin commands

- `/stats` -> total users/files/links/storage
- `/users` -> recent users list
- `/broadcast <message>` -> send message to all known users

---

## 9) Deploy to Heroku

This repo already includes:

- `Procfile`
- `runtime.txt`
- `requirements.txt`

### Step-by-step

1. Create a Heroku app.
2. Connect your GitHub repo.
3. Deploy branch.
4. In Heroku app settings -> Config Vars, add:
   - `BOT_TOKEN`
   - `API_ID`
   - `API_HASH`
   - `PUBLIC_BASE_URL` (example: `https://your-app.herokuapp.com`)
   - `LINK_SIGNING_SECRET`
   - Optional other vars from `.env.example`
5. Open: `https://your-app.herokuapp.com/health`

### Heroku warning

Heroku disk is ephemeral. Files may not persist after restart.  
For serious production usage, use external storage.

---

## 10) Deploy to VPS (Ubuntu)

### A) Install system packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg nginx git
```

### B) Clone and setup app

```bash
sudo mkdir -p /opt/telegram-file-link-bot
sudo chown -R $USER:$USER /opt/telegram-file-link-bot
cd /opt/telegram-file-link-bot
git clone <YOUR_REPO_URL> .
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env
```

### C) Run as background service (systemd)

```bash
sudo cp deploy/telegram-file-link-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable telegram-file-link-bot
sudo systemctl start telegram-file-link-bot
sudo systemctl status telegram-file-link-bot
```

### D) Nginx reverse proxy

```bash
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/telegram-file-link-bot
sudo ln -s /etc/nginx/sites-available/telegram-file-link-bot /etc/nginx/sites-enabled/telegram-file-link-bot
sudo nginx -t
sudo systemctl reload nginx
```

Then add SSL certificate (recommended) using Certbot.

---

## 11) How links work

- Download: `/d/<token>`
- Stream: `/s/<token>`
- Player page: `/player/<token>`
- HLS playlist (optional): `/hls/<token>/index.m3u8`

Tokens are signed and expire automatically.

---

## 12) Troubleshooting (for everyone)

### Bot does not start

Check:

- `BOT_TOKEN`, `API_ID`, `API_HASH` are correct
- Python version is 3.11+
- Dependencies installed with `pip install -r requirements.txt`

### Links are generated but not opening publicly

Check:

- `PUBLIC_BASE_URL` is correct and publicly reachable
- Domain/DNS points to your server
- Nginx reverse proxy is configured

### Streaming does not work for some files

Check:

- FFmpeg is installed (`ffmpeg -version`)
- `FFMPEG_ENABLED=true`
- Browser format compatibility (try HLS link)

### Admin commands not working

Check:

- Your Telegram numeric ID exists in `ADMIN_IDS`
- IDs are comma-separated without spaces issues

---

## 13) Security and production advice

- Use a strong random `LINK_SIGNING_SECRET`
- Use HTTPS in production
- Limit `ADMIN_IDS` to trusted users only
- Set reasonable `MAX_FILE_SIZE_MB`
- For large scale, move from local disk to object storage

---

## 14) Screenshot placeholders

- `docs/screenshots/01-upload-response.png`
- `docs/screenshots/02-player-page.png`
- `docs/screenshots/03-admin-stats.png`

---

## 15) Quick checklist before going live

- [ ] Bot token/API ID/API HASH set
- [ ] Public base URL correct
- [ ] Admin IDs added
- [ ] Health endpoint responds
- [ ] Upload test works
- [ ] Download link works
- [ ] Streaming page works
- [ ] Expiry behavior verified

---

## 16) License

Use MIT or your preferred license.
