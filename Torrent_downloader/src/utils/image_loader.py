import requests
from PIL import Image
from io import BytesIO

def load_image_from_url(url, size=None):
    """Load image from URL and optionally resize it"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        if 'image' not in response.headers.get('Content-Type', ''):
            raise ValueError("URL did not return an image")
            
        img_data = response.content
        img = Image.open(BytesIO(img_data))
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        if size:
            img = img.resize(size)
            
        return img
    except Exception as e:
        raise Exception(f"Failed to load image: {str(e)}")