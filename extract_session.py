# extract_session.py
# Use this if login_once.py keeps getting blocked.
# 
# HOW TO USE:
# 1. Open instagram.com in Chrome/Edge and log in normally
# 2. Press F12 → Application tab → Cookies → https://www.instagram.com
# 3. Find the cookie named "sessionid" — copy its value
# 4. Find the cookie named "ds_user_id" — copy its value
# 5. Paste them below and run: python extract_session.py

from instagrapi import Client
import json
import os

# ── PASTE YOUR VALUES HERE ────────────────────────────────────
SESSION_ID  = "25364045112%3AKS9fYqEjduFght%3A17%3AAYh-uaRxAiLZ4QBhPjz02Ubdye_3KRRug6UNZCakuA"
DS_USER_ID  = "25364045112"
CSRF_TOKEN  = "tG0ORettWi3D6SY6UfNEgd3XqwRAvx6w"
# ─────────────────────────────────────────────────────────────

SESSION_FILE = "session.json"

def build_session():
    if SESSION_ID == "PASTE_sessionid_COOKIE_VALUE_HERE":
        print("❌ Please paste your sessionid and ds_user_id values in the script first!")
        return

    cl = Client()

    # Load existing device settings if available
    if os.path.exists(SESSION_FILE):
        cl.load_settings(SESSION_FILE)

    # Inject the browser session cookies into instagrapi
    settings = cl.get_settings()
    settings["authorization_data"] = {
        "ds_user_id": DS_USER_ID,
        "sessionid": SESSION_ID
    }
    settings["cookies"] = {
        "sessionid": SESSION_ID,
        "ds_user_id": DS_USER_ID,
        "csrftoken": CSRF_TOKEN
    }
    settings["last_login"] = None

    cl.set_settings(settings)
    cl.dump_settings(SESSION_FILE)

    print("✅ session.json updated with browser session!")
    print(f"   ds_user_id : {DS_USER_ID}")
    print(f"   sessionid  : {SESSION_ID[:20]}...")
    print()
    print("Now run: python app.py")
    print("Then try posting an image.")

if __name__ == "__main__":
    build_session()
