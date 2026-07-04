import os
import json
from PIL import Image
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired, BadPassword

# ── Credentials (must match login_once.py) ────────────────────────────────────
USERNAME = "gensnap37"
PASSWORD = "GenSnap@26"
SESSION_FILE = "session.json"


class InstagramBot:
    def __init__(self):
        self.client = None
        self._logged_in = False

    def _build_client(self):
        """Create a fresh Client loaded with session.json settings"""
        cl = Client()
        if os.path.exists(SESSION_FILE):
            cl.load_settings(SESSION_FILE)
            settings = cl.get_settings()
            auth = settings.get("authorization_data", {})
            cookies = settings.get("cookies", {})
            sessionid = auth.get("sessionid", "")
            ds_user_id = auth.get("ds_user_id", "")
            csrftoken = cookies.get("csrftoken", "")
            if sessionid:
                cl.private.cookies.set("sessionid", sessionid, domain=".instagram.com")
            if ds_user_id:
                cl.private.cookies.set("ds_user_id", ds_user_id, domain=".instagram.com")
            if csrftoken:
                cl.private.cookies.set("csrftoken", csrftoken, domain=".instagram.com")
        return cl

    def login(self, username, password):
        """Full login — called from the UI 'Update Instagram' page"""
        try:
            cl = Client()
            cl.login(username, password)
            cl.dump_settings(SESSION_FILE)
            self.client = cl
            self._logged_in = True
            print("✅ Instagram login successful!")
            return True
        except Exception as e:
            print(f"❌ Instagram login failed: {str(e)}")
            return False

    def ensure_logged_in(self):
        """
        Load session.json and use it directly without re-logging in.
        Only falls back to login() if the session has no auth data.
        """
        if not os.path.exists(SESSION_FILE):
            print("⚠️ session.json not found. Please run login_once.py first.")
            return False

        try:
            print("🔄 Loading session...")
            cl = self._build_client()   # loads device fingerprint + auth token
            self.client = cl
            self._logged_in = True
            print("✅ Instagram session loaded!")
            return True

        except Exception as e:
            print(f"❌ Failed to load session: {type(e).__name__}: {e}")
            return False

    def prepare_image(self, input_path, output_path):
        """Resize + crop to 1080×1080 JPEG for Instagram"""
        img = Image.open(input_path).convert("RGB")
        w, h = img.size

        # Centre-crop to square
        if w > h:
            left = (w - h) // 2
            img = img.crop((left, 0, left + h, h))
        elif h > w:
            top = (h - w) // 2
            img = img.crop((0, top, w, top + w))

        img = img.resize((1080, 1080), Image.Resampling.LANCZOS)
        img.save(output_path, format="JPEG", quality=95)
        return output_path

    def post_image(self, image_path, caption):
        """Prepare and post an image to Instagram"""
        temp_image = None
        try:
            # Step 1 — ensure we are logged in
            if not self.ensure_logged_in():
                return False

            # Step 2 — verify source image exists
            if not os.path.exists(image_path):
                print(f"❌ Image not found: {image_path}")
                return False

            print(f"📁 Source image: {image_path}")

            # Step 3 — prepare temp JPEG in same folder
            base_dir  = os.path.dirname(os.path.abspath(image_path))
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            temp_image = os.path.join(base_dir, f"_ig_upload_{base_name}.jpg")

            print(f"🖼️  Preparing image → {temp_image}")
            self.prepare_image(image_path, temp_image)

            # Step 4 — upload
            print("📤 Uploading to Instagram...")
            media = self.client.photo_upload(temp_image, caption)
            print(f"✅ Posted! Media ID: {media.pk}")
            return True

        except LoginRequired:
            print("❌ login_required during upload. Run login_once.py again.")
            return False

        except ChallengeRequired:
            print("❌ Challenge required during upload. Run login_once.py again.")
            return False

        except Exception as e:
            print(f"❌ Upload failed — {type(e).__name__}: {e}")
            return False

        finally:
            if temp_image and os.path.exists(temp_image):
                os.remove(temp_image)
                print("🗑️  Temp file removed")

    # kept for backward-compat with old code that calls load_session()
    def load_session(self):
        return self.ensure_logged_in()

    def post_album(self, image_paths, caption):
        """Post multiple images as Instagram carousel"""
        temp_images = []
        try:
            if not self.ensure_logged_in():
                return False

            for i, path in enumerate(image_paths):
                if not os.path.exists(path):
                    print(f"❌ Image not found: {path}")
                    continue
                base_dir = os.path.dirname(os.path.abspath(path))
                base_name = os.path.splitext(os.path.basename(path))[0]
                temp = os.path.join(base_dir, f"_ig_album_{i}_{base_name}.jpg")
                self.prepare_image(path, temp)
                temp_images.append(temp)

            if not temp_images:
                print("❌ No valid images for album")
                return False

            if len(temp_images) == 1:
                media = self.client.photo_upload(temp_images[0], caption)
            else:
                media = self.client.album_upload(temp_images, caption)

            print(f"✅ Album posted! Media ID: {media.pk}")
            return True
        except Exception as e:
            print(f"❌ Album post failed: {type(e).__name__}: {e}")
            return False
        finally:
            for t in temp_images:
                if os.path.exists(t):
                    os.remove(t)
