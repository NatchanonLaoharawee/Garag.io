# Garag.io

A self-hosted garage door opener. Open your garage from anywhere via a web browser or mobile app — no cloud subscriptions, no open router ports.

## Architecture

```
Phone / Browser
      │
      ▼
Cloudflare Tunnel
      │
      ▼
Windows Laptop  ← Flask web app  (auth + proxy)
      │  local network only
      ▼
Raspberry Pi Zero W  ← Flask API  (GPIO control)
      │
      ▼
Relay → Glidermatic GTS
```

- **Pi Zero W** — sits on the local network, never internet-facing. Pulses a relay on GPIO 17 when it receives an authenticated request.
- **Windows Laptop** — runs the web app behind a Cloudflare Tunnel. Handles login, validates the shared token, and proxies toggle requests to the Pi over LAN.
- **Cloudflare Tunnel** — routes your public domain to the laptop with no port-forwarding required.

## Repository Structure

```
app/
├── rpi-zero/
│   ├── main.py          # Pi Flask API (GPIO control)
│   └── .env.example + garage.service.example
└── web/
    ├── main.py          # Laptop Flask app (auth + proxy)
    ├── templates/
    │   ├── login.html
    │   └── index.html
    ├── Dockerfile
    ├── docker-compose.yml
    └── .env.example
```

## Setup

### 1. Raspberry Pi Zero W
### Required files to change
[.env.example](./app/rpi-zero/.env.example)

[garage.service.example](./app/rpi-zero/garage.service.example)
```bash
cd app/rpi-zero
# Make changes to .env file, and then create it
cp .env.example .env
pip install flask waitress python-dotenv RPi.GPIO # Probably already installed, but these are the required dependencies

# Make changes to .service file, and then create it
sudo cp garage.service.example /etc/systemd/system/garage.service

# Reload systemd so it picks up the new unit
sudo systemctl daemon-reload

# Enable it to start on boot
sudo systemctl enable garage

# [Optional] start it, or reboot
sudo systemctl start garage
```

The Pi API listens on port `8000`. It is reachable on the local network as `rpi-zero.local` (mDNS).

### 2. Web App (Windows Laptop)
### Required files to change
[.env.example](./app/web/.env.example)

```bash
cd app/web
cp .env.example .env   # fill in FLASK_SECRET_KEY, SECRET_TOKEN, PI_BASE_URL
```

**.env values:**

| Key | Description |
|---|---|
| `FLASK_SECRET_KEY` | Any long random string for signing session cookies |
| `SECRET_TOKEN` | Shared password — must match the Pi's `SECRET_TOKEN` |
| `PI_BASE_URL` | `http://rpi-zero.local:8000` (or the Pi's static LAN IP) |

**Run with Docker (recommended):**

```bash
# Development — live reload
docker compose up web-dev

# Production — Waitress WSGI server
docker compose up web-prod
```

**Run without Docker:**

```bash
pip install -r requirements.txt
python main.py
```

The web app listens on `http://0.0.0.0:8080`.

### 3. Cloudflare Tunnel

Install `cloudflared` and point a tunnel at `localhost:8080` or `localhost:6868` depending on how you deployed the app. See the [Cloudflare Tunnel docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/).

## Authentication

Users visit the site and enter the shared `SECRET_TOKEN`. On success a signed session cookie is issued. "Remember me" keeps the session alive for 7 days; unchecked sessions expire when the browser closes.

Login attempts are rate-limited (10/min, 30/hr) to prevent brute-force. Changing `SECRET_TOKEN` in `.env` and restarting the web app invalidates all existing sessions.
