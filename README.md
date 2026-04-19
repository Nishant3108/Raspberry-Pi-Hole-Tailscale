# PI Project — Pi-hole + Tailscale

A self-hosted network security stack running on Raspberry Pi 5.  
Project for course CNIT 176 | Purdue University

---

## What is this project?

Network wide ad blocking (Pi-hole) and secure remote access (Tailscale) turns a Raspberry Pi 5 into a home network security system. It blocks ads and malicious domains at the DNS level, it provides us an encrypted VPN tunnel, and displays everything on a live real-time dashboard. All these are running on a Docker container.

---

## What problems does this solve?

- Ads and trackers load on every device on your network — Pi-hole blocks them at the DNS level before they even reach your device.
- Public Wi-Fi is unsafe — Tailscale VPN encrypts all your traffic so nobody can intercept it.
- No visibility into network traffic — the custom dashboard shows exactly what is happening on your network in real time, we can also access the Pi-hole dashboard. The custom dashboard is using Pi-hole API to fetch its data.

---

## Tech Stack

| Tool | Purpose |
|---|---|
| Raspberry Pi OS Lite 64-bit | Headless Linux server OS |
| Pi-hole | DNS-level ad and malware blocking |
| Tailscale | WireGuard-based encrypted VPN but does not require port forwarding |
| Docker + Docker Compose | Container for multiple applications |
| Python 3 + Flask | Backend API Dashboard |
| HTML + CSS + JavaScript | Frontend dashboard |
| UFW | Linux firewall |

---

## How DNS Blocking Works

Each time we enter a website on our device, it queries the DNS server first with a query of what is the IP address of this site. Normally this goes to Google (8.8.8.8) or your ISP. Pi-hole replaces your DNS server.

When your device requests the IP of a malicious or an ad domain such as doubleclick.net or yahoo.com, Pi-hole checks its blocklist of thousands (or more) of known domains. In case it finds a match, it returns 0.0.0.0, which implies that it is blocked. The ad never loads. This automatically works on all devices in your network phones, laptops, smart TVs and so on.

```
Your Device → Pi-hole DNS → Is this domain blocked?
                          → YES → Return 0.0.0.0 (blocked)
                          → NO  → Forward to upstream DNS
```

---

## How the VPN Works

Tailscale builds a tunnel using WireGuard protocol underneath and encrypts the tunnel across all devices. Every device gets a private 100.x.x.x IP address. Traffic between devices is encrypted end-to-end.

Unlike traditional VPNs, Tailscale does not require port forwarding or a static public IP. It uses NAT (Network Address Translation) traversal in order to link devices automatically. This means that it works even behind any home internet which does not support port forwarding.

```
Phone (mobile data) ──── Tailscale tunnel ──── Pi at home
         ↑                   encrypted              ↑
    100.x.x.x                                 100.xxx.xx.xx
```

---

## Project Structure

```
network-guardian/
├── docker-compose.yml          # Defines all services (Pi-hole + Dashboard)
├── dashboard/
│   ├── app.py                  # Flask backend — connects to Pi-hole API
│   ├── Dockerfile              # Dashboard container definition
│   ├── requirements.txt        # Python dependencies (flask, requests)
│   └── templates/
│       └── index.html          # Dashboard frontend (Matrix-style UI)
└── README.md                   # This file
```

---

## How to Set This Up

### Requirements
- Raspberry Pi 5 (4GB RAM)
- Raspberry Pi OS Lite 64-bit (headless)
- Docker and Docker Compose installed
- Tailscale account (free at tailscale.com)

### Step 1 — Clone this repo
```bash
git clone https://github.com/Nishant3108/Pi-hole-Tailscale.git
cd Pi-hole-Tailscale
```

### Step 2 — Set your Pi-hole password
Edit `docker-compose.yml` and change `WEBPASSWORD` to your own password.

### Step 3 — Start all services
```bash
docker compose up -d
```

### Step 4 — Install Tailscale VPN
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

### Step 5 — Configure UFW Firewall
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 53/tcp
sudo ufw allow 53/udp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 5000/tcp
sudo ufw allow 41641/udp
sudo ufw enable
```

### Step 6 — Access the dashboard
Open your browser and go to:
```
http://YOUR-PI-IP:5000
```

---

## Code Explained

### `app.py` — Flask Backend

```python
from flask import Flask, jsonify, render_template
import requests

app = Flask(__name__)
PIHOLE_URL = "http://localhost"
API_KEY = "[YOURPASSWORD]"
```
Flask is a lightweight Python web framework. We import `requests` to make HTTP calls to the Pi-hole API. `Flask(__name__)` creates the web application instance.

```python
@app.route('/')
def index():
    return render_template('index.html')
```
This route serves the dashboard HTML page when you visit the root URL in your browser. `render_template` looks in the `templates/` folder automatically.

```python
@app.route('/api/stats')
def stats():
    try:
        auth = requests.post(f"{PIHOLE_URL}/api/auth",
                            json={"password": API_KEY}, timeout=5)
        sid = auth.json().get("session", {}).get("sid")
        r = requests.get(f"{PIHOLE_URL}/api/stats/summary",
                        headers={"sid": sid}, timeout=5)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": str(e)})
```
This route first authenticates with Pi-hole's API using the password to get a session ID (sid). It then uses that session ID to fetch live stats from Pi-hole and returns them as JSON to the frontend. Every time the frontend asks for stats this runs fresh.

```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```
`host='0.0.0.0'` means accept connections from any device on the network, not just localhost. Port 5000 is where the dashboard is accessible.

---

### `index.html` — Frontend Dashboard

The frontend is a single HTML file with CSS and JavaScript. It uses a Matrix rain canvas animation for the background and fetches live data from Flask every 5 seconds.

```javascript
async function updateStats() {
    const res = await fetch('/api/stats');
    const d = await res.json();
    document.getElementById('total-today').textContent = d.queries.total;
}
setInterval(updateStats, 5000);
```
`fetch('/api/stats')` calls our Flask backend. `async/await` handles the asynchronous response. `setInterval` runs these every 5000 milliseconds (5 seconds) automatically, so the dashboard updates without any page refresh.

The Matrix rain animation uses HTML5 Canvas API:
```javascript
const canvas = document.getElementById('matrix-canvas');
const ctx = canvas.getContext('2d');
const chars = 'アイウエオカキクケコ01アBCDEF0123456789';
// Draws falling characters to create the Matrix effect
function drawMatrix() {
    ctx.fillStyle = 'rgba(0,0,0,0.05)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#00ff41';
    drops.forEach((y, i) => {
        ctx.fillText(chars[Math.floor(Math.random() * chars.length)], i * 14, y * 14);
        if (y * 14 > canvas.height && Math.random() > 0.975) drops[i] = 0;
        drops[i]++;
    });
}
setInterval(drawMatrix, 50);
```
The canvas fills with a semi-transparent black rectangle each frame — this creates the fading trail effect. Random Japanese and hex characters fall down each column.

---

### `docker-compose.yml` — Service for multiple applications

```yaml
services:
  pihole:
    image: pihole/pihole:latest
    network_mode: host
    environment:
      TZ: [COUNTRY]/[STATE]/[CITY]
      WEBPASSWORD: '[YOURPASSWORD]'
      FTLCONF_LOCAL_IPV4: '192.168.12.100'
      FTLCONF_webserver_api_max_sessions: '100'
    volumes:
      - './etc-pihole:/etc/pihole'
      - './etc-dnsmasq.d:/etc/dnsmasq.d'
    restart: unless-stopped

  dashboard:
    build: ./dashboard
    network_mode: host
    restart: unless-stopped
    depends_on:
      - pihole
```

- `network_mode: host` — containers share the Pi's network directly. Required for Pi-hole to intercept DNS traffic on port 53
- `volumes` — Pi-hole config files persist on the Pi's storage so settings survive container restarts
- `restart: unless-stopped` — both services start automatically every time the Pi boots
- `depends_on: pihole` — dashboard waits for Pi-hole to start first
- `build: ./dashboard` — Docker builds the dashboard image from the local Dockerfile

---

### `Dockerfile` — Dashboard Container

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python3", "app.py"]
```

- `FROM python:3.11-slim` — starts from a minimal Python image
- `WORKDIR /app` — sets the working directory inside the container
- `COPY requirements.txt` then `pip install` — installs dependencies before copying code (Docker layer caching)
- `EXPOSE 5000` — documents that port 5000 is used
- `CMD` — the command that runs when the container starts

---

## Raspberry Pi Architecture Connections

This project uses the Raspberry Pi 5 hardware in the following ways:

| Pi Component | Role in this project |
|---|---|
| ARM Cortex-A76 CPU | Executes all server processes — Pi-hole DNS, Flask web server, Tailscale VPN encryption |
| Networking hardware (Ethernet / WiFi) | Routes all DNS queries from network devices through Pi-hole, handles VPN routing |
| Storage (microSD card) | Stores Raspberry Pi OS, Docker images, Pi-hole database and blocklists |
| RAM (4GB) | Runs Pi-hole, Flask dashboard, and Tailscale simultaneously without swapping |

---

## Troubleshooting

**Pi-hole dashboard not loading**
```bash
docker ps                    # Check if container is running
docker logs pihole           # Check for errors
docker restart pihole        # Restart the container
```

**Dashboard showing dashes (-- everywhere)**
```bash
# API sessions exceeded — increase the limit
docker exec pihole sh -c "sed -i 's/max_sessions = [0-9]*/max_sessions = 100/' /etc/pihole/pihole.toml"
docker restart pihole
```

**SSH connection refused after reboot**
```bash
sudo systemctl restart ssh
sudo ufw allow 22/tcp
```

**Static IP not sticking**
```bash
sudo nmcli con mod "YourWiFiName" ipv4.addresses 192.168.12.100/24
sudo nmcli con mod "YourWiFiName" ipv4.gateway 192.168.12.1
sudo nmcli con mod "YourWiFiName" ipv4.dns 192.168.12.1
sudo nmcli con mod "YourWiFiName" ipv4.method manual
sudo nmcli con up "YourWiFiName"
```

**Tailscale not connecting**
```bash
sudo tailscale status        # Check connection status
sudo tailscale up            # Re-authenticate if needed
```

---

## Screenshots

<img width="975" height="538" alt="image" src="https://github.com/user-attachments/assets/d05c7d0b-267f-4ee1-b236-202189f48f24" />

**Figure 1: Pi-Hole dashboard** – We see this as soon as we setup Pi-hole and login to our dashboard.


<img width="975" height="525" alt="image" src="https://github.com/user-attachments/assets/1aa17fde-8b62-4e08-8ac1-4ca8dff3dfc8" />

**Figure 2: Pi-Hole dashboard** – This is after browsing for a while.


<img width="897" height="417" alt="image" src="https://github.com/user-attachments/assets/4a20b6d5-93ce-415f-a7ff-1d2356b82cc9" />

**Figure 3: TailScale** – This is the TailScale dashboard and shows all the machines that are connected to VPN.


<img width="975" height="585" alt="image" src="https://github.com/user-attachments/assets/755c6372-7839-41b0-8015-048a63994157" />

**Figure 4: UFW Firewall** – Shows our UFW status and all the ports that are allowed to pass through the network.


<img width="975" height="394" alt="image" src="https://github.com/user-attachments/assets/c8f98ef3-4e27-469c-bad8-d5712f906206" />

**Figure 5: Dashboard** – The initial dashboard which I set up, and this shows us that the API is working as intended.


<img width="842" height="464" alt="image" src="https://github.com/user-attachments/assets/5235b8ef-ad9e-4aa6-9876-1fac6b2e9bef" />

**Figure 6: Dashboard** – Updated dashboard with more CSS and other useful information (made with the help of AI).

---

## References

1. Pi-hole Documentation — https://docs.pi-hole.net
2. Pi-hole Docker GitHub — https://github.com/pi-hole/docker-pi-hole
3. Tailscale Documentation — https://tailscale.com/kb/1017/install
4. Tailscale + Pi-hole Guide — https://tailscale.com/kb/1114/pi-hole
5. Docker Install for Raspberry Pi — https://docs.docker.com/engine/install/raspberry-pi-os/
6. Flask Documentation — https://flask.palletsprojects.com
7. UFW Guide — https://help.ubuntu.com/community/UFW
8. Crosstalk Solutions Pi-hole Video — https://www.youtube.com/watch?v=cE21YjuaB6o
