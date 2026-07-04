import os
import requests
import json
from PIL import Image

class TelegramBot:
    def __init__(self, bot_token=None):
        # You should move this to environment variables
        self.bot_token = bot_token or "8756559155:AAG43wMnWq6iuhAew91aroqcIyNbNdSFBq4"
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.config_file = "telegram_config.json"
        self.chat_id = None
        
        # Load saved config
        self.load_config()
    
    def load_config(self):
        """Load saved Telegram configuration"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.chat_id = config.get('chat_id')
                    return True
            except:
                pass
        return False
    
    def save_config(self):
        """Save Telegram configuration"""
        config = {
            'chat_id': self.chat_id
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f)
    
    def set_chat_id(self, chat_id):
        """Set the chat/channel ID for posting"""
        self.chat_id = chat_id
        self.save_config()
        return True
    
    def verify_chat_id(self):
        """Verify if the saved chat ID is valid"""
        if not self.chat_id:
            return False
        
        try:
            # Try to send a test message
            url = f"{self.api_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": "✅ Connection test successful!"
            }
            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200 and response.json().get('ok', False)
        except:
            return False
    
    def prepare_image(self, input_path, output_path=None):
        """Prepare image for Telegram (compress if needed)"""
        if output_path is None:
            name, ext = os.path.splitext(input_path)
            output_path = f"{name}_telegram{ext}"
        
        img = Image.open(input_path)
        
        # Resize if too large (Telegram has size limits)
        max_size = 1280
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_image = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                rgb_image.paste(img, mask=img.split()[-1])
            else:
                rgb_image.paste(img)
            img = rgb_image
        
        img.save(output_path, "JPEG", quality=85, optimize=True)
        return output_path
    
    def send_image(self, image_path, caption=""):
        """Send image to Telegram"""
        if not self.chat_id:
            print("❌ Telegram chat ID not configured")
            return False, "Chat ID not configured"
        
        try:
            # Prepare image
            prepared_image = self.prepare_image(image_path)
            
            # Send photo
            url = f"{self.api_url}/sendPhoto"
            
            with open(prepared_image, "rb") as img:
                files = {"photo": img}
                data = {
                    "chat_id": self.chat_id,
                    "caption": caption[:1024]  # Telegram caption limit is 1024 chars
                }
                
                response = requests.post(url, data=data, files=files, timeout=30)
            
            # Clean up temp file if different from original
            if prepared_image != image_path and os.path.exists(prepared_image):
                os.remove(prepared_image)
            
            result = response.json()
            
            if result.get("ok"):
                print("✅ Posted successfully to Telegram!")
                return True, "Success"
            else:
                error_msg = result.get('description', 'Unknown error')
                print(f"❌ Telegram post failed: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            print(f"❌ Telegram error: {str(e)}")
            return False, str(e)
    
    def send_message(self, message):
        """Send a text message to Telegram"""
        if not self.chat_id:
            return False, "Chat ID not configured"
        
        try:
            url = f"{self.api_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message
            }
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result.get("ok"):
                return True, "Success"
            else:
                return False, result.get('description', 'Unknown error')
        except Exception as e:
            return False, str(e)


# Test function
def test_telegram_connection(bot_token, chat_id):
    """Test Telegram connection with given credentials"""
    bot = TelegramBot(bot_token)
    bot.set_chat_id(chat_id)
    return bot.verify_chat_id()