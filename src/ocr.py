import cv2
import re
import numpy as np
import os
from google.cloud import vision

class IIDXReader:
    def __init__(self, credentials_path="service_account.json"):
        if os.path.exists(credentials_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        self.client = vision.ImageAnnotatorClient()

    def _upscale(self, img, scale=2):
        h, w = img.shape[:2]
        return cv2.resize(img, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)

    def _preprocess_score(self, crop):
        """スコア用: グレースケール + 3倍アップスケール + 反転
        IIDXの数値は暗背景に明るい色文字のため、反転して黒文字on白背景にするとOCR精度が上がる"""
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        large = self._upscale(gray, scale=3)
        return cv2.bitwise_not(large)

    def _preprocess_text(self, crop, scale=2):
        """テキスト用: グレースケール + アップスケール + 反転"""
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        large = self._upscale(gray, scale=scale)
        return cv2.bitwise_not(large)

    def recognize_text_cloud(self, image_array, document_mode=False):
        """numpy画像をCloud Vision APIに送りテキストを返す。
        document_mode=True でdocument_text_detectionを使用（日本語混じりに有効）"""
        success, encoded_image = cv2.imencode('.jpg', image_array)
        if not success:
            return ""

        content = encoded_image.tobytes()
        image = vision.Image(content=content)
        image_context = vision.ImageContext(language_hints=["ja", "en"])

        if document_mode:
            response = self.client.document_text_detection(image=image, image_context=image_context)
            annotation = response.full_text_annotation
            if response.error.message:
                raise Exception(f'{response.error.message}')
            return annotation.text if annotation else ""
        else:
            response = self.client.text_detection(image=image, image_context=image_context)
            texts = response.text_annotations
            if response.error.message:
                raise Exception(f'{response.error.message}')
            return texts[0].description if texts else ""

    def _parse_score(self, text):
        """スコアをパース。MAX-XXXX除去・スペース区切り数字連結に対応"""
        # MAX-XXXX を先に除去（誤ってスコアと混同しないため）
        text = re.sub(r'MAX-\d+', '', text, flags=re.IGNORECASE)

        # スペース区切りの数字列を連結 (改行は除く: "2 2 4 2" → "2242")
        collapsed = text
        for _ in range(4):
            collapsed = re.sub(r'(\d) +(\d)', r'\1\2', collapsed)

        numbers = re.findall(r'\d+', collapsed)
        candidates = []
        for num_str in numbers:
            if 3 <= len(num_str) <= 4:
                val = int(num_str)
                if 500 <= val < 6000:  # IIDXのEXスコアは実質500以上
                    candidates.append(val)

        return max(candidates) if candidates else None

    def extract_data(self, image_path):
        """Cloud VisionでDate/Title/Scoreを抽出する"""
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

        # 1. 日付抽出 (左上: y=0.015-0.045, x=0.03-0.37)
        date_crop = img[int(height*0.015):int(height*0.045), int(width*0.03):int(width*0.37)]
        date_proc = self._preprocess_text(date_crop, scale=2)
        date_text = self.recognize_text_cloud(date_proc)
        print(f"DEBUG: Date raw: {date_text}")

        match = re.search(r'20\d{2}[-./]\d{2}[-./]\d{2}( \d{2}:\d{2})?', date_text.replace('\n', ' '))
        if match:
            data["date"] = match.group(0)

        # 2. スコア抽出: MAX-00XXの直下にある4桁スコアを狙う
        score_crop = img[int(height*0.48):int(height*0.57), int(width*0.64):int(width*0.88)]
        score_proc = self._preprocess_score(score_crop)
        score_text = self.recognize_text_cloud(score_proc)
        print(f"DEBUG: Score raw: {score_text}")

        data["score"] = self._parse_score(score_text)

        # 3. 曲名抽出 (y=0.245-0.268, x=0.05-0.95)
        # document_text_detectionで日本語・特殊文字の読み取り精度を上げる
        title_crop = img[int(height*0.245):int(height*0.268), int(width*0.05):int(width*0.95)]
        title_proc = self._preprocess_text(title_crop, scale=3)
        title_text = self.recognize_text_cloud(title_proc, document_mode=True)
        print(f"DEBUG: Title raw: {title_text}")

        if title_text:
            cleaned = title_text.replace('\n', ' ').strip()
            data["title"] = cleaned

        return data
