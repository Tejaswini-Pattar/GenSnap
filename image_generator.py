import os
import requests
import io
from datetime import datetime
from PIL import Image
import time
import urllib.parse

class ImageGenerator:
    def __init__(self, api_token=None):
        # Pollinations doesn't require an API token
        self.api_token = api_token
        
    def generate_image(self, prompt, model=None):
        """Generate image using Pollinations.ai (free, no API key needed)"""
        try:
            # Encode the prompt for URL
            encoded_prompt = urllib.parse.quote(prompt)
            
            # Pollinations API endpoint (free, no authentication)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            
            # Add parameters for better quality
            params = {
                "width": 1080,
                "height": 1080,
                "nologo": "true",
                "seed": int(time.time())
            }
            
            print(f"🎨 Generating image with Pollinations.ai...")
            response = requests.get(url, params=params, timeout=60)
            
            if response.status_code == 200:
                return response.content
            else:
                print(f"Error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"Request failed: {e}")
            return None

# Global generator instance
generator = None

def init_generator(api_token=None):
    """Initialize the image generator"""
    global generator
    # Pollinations doesn't need an API token
    generator = ImageGenerator(api_token)

def generate_and_save_image(prompt, user_id):
    """Generate image using Pollinations.ai (free)"""
    global generator
    
    if generator is None:
        init_generator()
    
    # Create user-specific directory
    user_dir = f"generated_images/user_{user_id}"
    os.makedirs(user_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{user_dir}/img_{timestamp}.jpg"
    
    print(f"🎨 Generating image for prompt: {prompt[:50]}...")
    
    try:
        image_bytes = generator.generate_image(prompt)
        
        if image_bytes:
            # Save the image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'RGBA':
                    rgb_image.paste(image, mask=image.split()[-1])
                else:
                    rgb_image.paste(image)
                image = rgb_image
            
            # Ensure 1080x1080
            image = image.resize((1080, 1080), Image.Resampling.LANCZOS)
            
            # Save with high quality
            image.save(filename, "JPEG", quality=95, optimize=True)
            
            print(f"✅ Image generated successfully!")
            return filename
        else:
            raise Exception("Failed to generate image - no image data received")
            
    except Exception as e:
        print(f"❌ Error generating image: {str(e)}")
        raise Exception(f"Failed to generate image: {str(e)}")