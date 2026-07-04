import requests
import io
from PIL import Image
import time

class ImageGenerator:
    def __init__(self, api_token):
        self.api_token = api_token
        self.headers = {"Authorization": f"Bearer {api_token}"}
        
    def generate_image(self, prompt, model="stabilityai/stable-diffusion-xl-base-1.0", max_retries=3):
        # Updated API endpoint
        api_url = f"https://router.huggingface.co/hf-inference/models/{model}"
        
        for attempt in range(max_retries):
            try:
                response = requests.post(api_url, headers=self.headers, json={"inputs": prompt})
                
                if response.status_code == 200:
                    # Check if it's actually an image
                    if 'image' in response.headers.get('content-type', ''):
                        return response.content
                    else:
                        print(f"Unexpected response type: {response.headers.get('content-type')}")
                        print(f"Response: {response.text[:200]}")
                        return None
                        
                elif response.status_code == 503:
                    # Model is loading
                    wait_time = 20
                    print(f"Model is loading, waiting {wait_time} seconds... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                    
                else:
                    print(f"Error {response.status_code}: {response.text}")
                    return None
                    
            except Exception as e:
                print(f"Request failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                continue
                
        return None
    
    def process(self, prompt):
        image_bytes = self.generate_image(prompt)
        
        if image_bytes is None:
            print("Failed to generate image")
            return
            
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.show()
            
            # Save with timestamp to avoid filename collisions
            timestamp = int(time.time())
            filename = f"generated_image_{timestamp}.jpg"
            image.save(filename)
            print(f"Image saved as {filename}")
            
        except Exception as e:
            print(f"Error processing image: {e}")

# Usage
import os
generator = ImageGenerator(os.environ.get("HUGGINGFACE_TOKEN", ""))
generator.process("A cat riding on a black horse")