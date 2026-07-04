# Run this to find the correct user ID for gensnap_ap321
# Uses the web (not mobile API) so no IP block issue

import requests

username = "gensnap_ap321"

try:
    url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "x-ig-app-id": "936619743392459"
    }
    r = requests.get(url, headers=headers)
    data = r.json()
    user_id = data['data']['user']['id']
    print(f"✅ User ID for {username}: {user_id}")
except Exception as e:
    print(f"Error: {e}")
    print("Try visiting: https://www.instagram.com/{username}/?__a=1&__d=dis")
