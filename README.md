# telegram-file-link-bot

Production-ready Telegram bot + FastAPI server that turns uploaded Telegram files into expiring:

- **Direct download links**
- **Streaming/player links** (video/audio)
- **Optional HLS output with FFmpeg**

---

## Features

- Async architecture (Pyrogram + FastAPI + aiosqlite)
- File indexing in SQLite (dedupe by Telegram unique file ID)
- Signed, expiring links with HMAC token verification
- Direct download endpoint with range support
- Streaming endpoint + browser player page
- Optional FFmpeg HLS endpoint for better playback compatibility
- Admin commands:
  - `/stats`
  - `/users`
  - `/broadcast <text>`
- User command:
  - `/expire <minutes|default>` for link expiration preference
- Basic in-memory user rate limiting
- Structured logging

---

## Project structure

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

## Bot flow

1. User uploads a file in Telegram chat.
2. Bot receives metadata and applies rate limits.
3. File is downloaded to local storage (or reused if already indexed).
4. Bot creates signed expiring token.
5. Bot returns:
   - `https://your-domain/d/<token>` (download)
   - `https://your-domain/player/<token>` (stream page)

---

## Requirements

- Python 3.11+
- Telegram bot token
- Telegram API ID / API HASH (from https://my.telegram.org)
- Public domain for production usage (optional for local testing)
- FFmpeg (optional but recommended)

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Environment variables

Use `.env.example` as reference:

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | Yes | Telegram bot token |
| `API_ID` | Yes | Telegram API ID |
| `API_HASH` | Yes | Telegram API hash |
| `PUBLIC_BASE_URL` | Yes (prod) | Public base URL sent inside links |
| `PORT` | No | FastAPI server port (default: 8080) |
| `SERVER_HOST` | No | Server bind host (default: 0.0.0.0) |
| `ADMIN_IDS` | No | Comma-separated admin user IDs |
| `LINK_SIGNING_SECRET` | Strongly recommended | Secret for signed links |
| `LINK_EXPIRY_SECONDS` | No | Default expiry for generated links |
| `RATE_LIMIT_REQUESTS` | No | Upload requests allowed in window |
| `RATE_LIMIT_WINDOW_SECONDS` | No | Rate-limit window duration |
| `MAX_FILE_SIZE_MB` | No | Maximum accepted upload size |
| `FFMPEG_ENABLED` | No | Enable/disable HLS endpoints |
| `DATABASE_PATH` | No | SQLite DB path |
| `STORAGE_PATH` | No | File storage directory |
| `HLS_PATH` | No | HLS output directory |
| `PYROGRAM_WORKDIR` | No | Pyrogram session/work directory |

---

## Local run

```bash
cp .env.example .env
# edit .env
python -m bot.main
```

Health check:

```bash
curl http://127.0.0.1:8080/health
```

---

## Commands

### User

- `/start` - Welcome + usage
- `/help` - Command help
- `/expire <minutes|default>` - Set personal link expiry

### Admin

- `/stats` - Show user/file/link metrics
- `/users` - List latest users
- `/broadcast <text>` - Send message to all known users

---

## Hosting

## 1) Heroku

This project includes:
- `Procfile`
- `runtime.txt`
- `requirements.txt`

### Heroku setup

1. Create app and connect repository.
2. Set config vars in Heroku dashboard:
   - `BOT_TOKEN`
   - `API_ID`
   - `API_HASH`
   - `PUBLIC_BASE_URL` (e.g. `https://your-app.herokuapp.com`)
   - `LINK_SIGNING_SECRET`
   - Optional vars from `.env.example`
3. Deploy.
4. Open app and verify `/health`.

> Note: Heroku ephemeral disk is not ideal for persistent file storage. Use an external storage backend for heavy production workloads.

---

## 2) VPS (Ubuntu)

### Installation guide

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg nginx git
sudo mkdir -p /opt/telegram-file-link-bot
sudo chown -R $USER:$USER /opt/telegram-file-link-bot
cd /opt/telegram-file-link-bot
git clone <your-repo-url> .
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env values
```

### systemd service

Copy service file:

```bash
sudo cp deploy/telegram-file-link-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable telegram-file-link-bot
sudo systemctl start telegram-file-link-bot
sudo systemctl status telegram-file-link-bot
```

### Nginx reverse proxy

Copy and enable:

```bash
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/telegram-file-link-bot
sudo ln -s /etc/nginx/sites-available/telegram-file-link-bot /etc/nginx/sites-enabled/telegram-file-link-bot
sudo nginx -t
sudo systemctl reload nginx
```

Then add TLS (recommended) with Certbot.

---

## 3) Google Colab

Use `colab_setup.ipynb`:

1. Prompts for bot token/API ID/API hash/domain/port
2. Installs dependencies
3. Creates environment file
4. Starts bot + API server
5. Prints status and URL

---

## Streaming page

`/player/<token>` includes:

- HTML5 video/audio player
- Download button
- Raw stream URL
- Optional HLS link

---

## Screenshots (placeholders)

- `docs/screenshots/bot-upload-response.png`
- `docs/screenshots/player-page.png`
- `docs/screenshots/admin-stats.png`

---

## Security notes

- Always set a strong `LINK_SIGNING_SECRET`
- Use HTTPS in production
- Restrict `ADMIN_IDS`
- Consider integrating antivirus scanning and external object storage for large-scale deployments

---

## License

MIT (or your preferred license).