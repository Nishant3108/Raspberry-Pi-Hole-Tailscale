from flask import Flask, jsonify, render_template
import requests
import time

app = Flask(__name__)

PIHOLE_URL = "http://localhost"
API_KEY = "[YOURPASSWORD]"  # needs to be updated!

# Reuse the same session instead of creating a new one every request
session_cache = {"sid": None, "expires": 0}

def get_sid():
    now = time.time()
    # Only get a new session if current one is expired (validity is 1800 seconds)
    if session_cache["sid"] is None or now > session_cache["expires"]:
        try:
            r = requests.post(f"{PIHOLE_URL}/api/auth",
                            json={"password": API_KEY}, timeout=5)
            data = r.json()
            sid = data.get("session", {}).get("sid")
            validity = data.get("session", {}).get("validity", 1800)
            session_cache["sid"] = sid
            session_cache["expires"] = now + validity - 60  # refresh 60s early
        except:
            return None
    return session_cache["sid"]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def stats():
    try:
        sid = get_sid()
        r = requests.get(f"{PIHOLE_URL}/api/stats/summary",
                        headers={"sid": sid}, timeout=5)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
