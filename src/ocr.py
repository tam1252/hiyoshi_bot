import cv2
import re
import numpy as np
import os
from google.cloud import vision

class IIDXReader:
    def __init__(self, credentials_path="service_account.json"):
        # Set credential path for Google Cloud Client
        if os.path.exists(credentials_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        self.client = vision.ImageAnnotatorClient()

    def preprocess_crop(self, crop):
        """Minimal preprocessing for Cloud Vision (just grayscale usually enough)"""
        # Cloud Vision is robust, maybe just simple grayscale?
        # Actually usually native color is fine too.
        # Let's clean it a bit just in case.
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        return gray

    def recognize_text_cloud(self, image_array):
        """Sends numpy image to Cloud Vision API and returns full text."""
        success, encoded_image = cv2.imencode('.jpg', image_array)
        if not success:
            return ""
        
        content = encoded_image.tobytes()
        image = vision.Image(content=content)
        
        # Hint Japanese and English
        image_context = vision.ImageContext(language_hints=["ja", "en"])
        
        response = self.client.text_detection(image=image, image_context=image_context)
        texts = response.text_annotations
        
        if response.error.message:
            raise Exception(f'{response.error.message}')

        if texts:
            # texts[0] is the full text
            return texts[0].description
        return ""

    def extract_data(self, image_path):
        """Extracts Date, Title, Artist, and Score from the image using Cloud Vision."""
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError("Could not read image")
        
        height, width, _ = img.shape
        data = {
            "date": None,
            "title": None,
            "artist": None,
            "score": None
        }

        # 1. Date Extraction
        # Tuned: 0.015-0.045 / 0.03-0.37 (Tight crop works well)
        date_crop = img[int(height*0.015):int(height*0.045), int(width*0.03):int(width*0.37)]
        date_text = self.recognize_text_cloud(date_crop)
        print(f"DEBUG: Date raw: {date_text}")
        
        # Parse date
        match = re.search(r'20\d{2}[-./]\d{2}[-./]\d{2}( \d{2}:\d{2})?', date_text.replace('\n', ' '))
        if match:
             data["date"] = match.group(0)

        # 2. Score Extraction
        # Tuned: 0.485-0.515 / 0.65-0.86
        score_crop = img[int(height*0.485):int(height*0.515), int(width*0.65):int(width*0.86)]
        score_text = self.recognize_text_cloud(score_crop)
        print(f"DEBUG: Score raw: {score_text}")
        
        # Parse score (find largest number)
        # Cloud vision might return "1234" or "1 234" etc.
        numbers = re.findall(r'\d+', score_text)
        candidates = []
        for num_str in numbers:
            if 3 <= len(num_str) <= 4:
                 val = int(num_str)
                 if val < 6000:
                     candidates.append(val)
        
        if candidates:
            data["score"] = max(candidates)

        # 3. Title Extraction (Merged Song Name)
        # Tuned: 0.245-0.268 / 0.05-0.95
        title_crop = img[int(height*0.245):int(height*0.268), int(width*0.05):int(width*0.95)]
        
        # Preprocess? Maybe invert for better contrast if it's white on black?
        # Cloud Vision handles white on black well usually, but let's try raw first.
        title_text = self.recognize_text_cloud(title_crop)
        print(f"DEBUG: Title raw: {title_text}")
        
        # Clean up title
        if title_text:
            # Replace newlines with space
            cleaned = title_text.replace('\n', ' ').strip()
            data["title"] = cleaned

        return data
