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
│   └── .env.example
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

```bash
cd app/rpi-zero
cp .env.example .env   # fill in SECRET_TOKEN and RELAY_PIN
pip install flask python-dotenv RPi.GPIO
python main.py
```

The Pi API listens on port `5000`. It is reachable on the local network as `rpi-zero.local` (mDNS).

### 2. Web App (Windows Laptop)

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

Install `cloudflared` and point a tunnel at `localhost:8080` or `localhost:6767` depending on how you deployed the app. See the [Cloudflare Tunnel docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/).

## Authentication

Users visit the site and enter the shared `SECRET_TOKEN`. On success a signed session cookie is issued. "Remember me" keeps the session alive for 7 days; unchecked sessions expire when the browser closes.

Login attempts are rate-limited (10/min, 30/hr) to prevent brute-force. Changing `SECRET_TOKEN` in `.env` and restarting the web app invalidates all existing sessions.

## Notes

- The Pi should have a reserved DHCP lease (static LAN IP) so `rpi-zero.local` always resolves correctly.
- Docker uses `network_mode: host` so the container can resolve mDNS hostnames via the host's Bonjour stack.
- All toggle events are logged to `garage.log` in the web app directory.
