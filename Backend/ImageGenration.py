import requests
from PIL import Image
from io import BytesIO
from dotenv import get_key
import os
from time import sleep




# Load Hugging Face API key from .env file
API_TOKEN = get_key(".env", "HUGGINGFACE_API_KEY")
API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def enhance_prompt(prompt: str) -> str:
    enhancements = [
        "high detail",
        "4k resolution",
        "photorealistic",
        "artstation",
        "cinematic lighting",
        "masterpiece",
        "sharp focus"
    ]
    return f"{prompt}, " + ", ".join(enhancements)

def generate_image(prompt: str, index: int = 1):
    prompt = enhance_prompt(prompt)
    data = {
        "inputs": prompt,
        "options": {
            "wait_for_model": True
        }
    }

    response = requests.post(API_URL, headers=HEADERS, json=data)
    
    if response.status_code == 200:
        image = Image.open(BytesIO(response.content))
        folder = "Data"
        os.makedirs(folder, exist_ok=True)
        filename = os.path.join(folder, f"{prompt.replace(' ', '_')}_{index}.png")
        image.save(filename)
        print(f"[✓] Image saved to {filename}")
        # image.show()
        try:
            from Frontend.Gui import MainWindowInstance
            if MainWindowInstance:
                MainWindowInstance.image_preview_screen.show_image_signal.emit(filename)
                MainWindowInstance.stacked_widget.setCurrentIndex(2)

        except Exception as e:
            print("[!] Could not update GUI:", e)

        return filename
    else:
        print(f"[!] Failed to generate image: {response.status_code}")
        print(response.text)
        return None

def generate_multiple_images(prompt: str, count: int = 4):
    for i in range(1, count + 1):
        generate_image(prompt, i)
        sleep(1)

# Example usage
if __name__ == "__main__":
    user_prompt = input("Enter image prompt: ")
    generate_multiple_images(user_prompt)

