from src.ocr import IIDXReader
from src.matcher import TitleMatcher
import json
import glob
import numpy as np

class NumpyEncoder(json.JSONEncoder):
    """ Special json encoder for numpy types """
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

def verify():
    reader = IIDXReader()
    matcher = TitleMatcher()
    images = sorted(glob.glob("test_image*.jpg"))

    for image_path in images:
        print(f"--- Processing {image_path} ---")
        try:
            data = reader.extract_data(image_path)
            corrected_title = matcher.correct_title(data.get('title'))
            print(f"Date:  {data.get('date')}")
            print(f"Song:  {corrected_title} (raw: {data.get('title')})")
            print(f"Score: {data.get('score')}")
        except Exception as e:
            print(f"Error processing {image_path}: {e}")
        print("-" * 30 + "\n")

if __name__ == "__main__":
    verify()
