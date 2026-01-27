from rapidfuzz import process, fuzz
from dotenv import load_dotenv
import os

# Explicitly load .env
load_dotenv(".env")

def debug_matcher():
    print(f"ENV CHECK: START={os.getenv('EVENT_START_DATE')}")

    songs = [
        "XENON II 〜TOMOYUKIの野望〜", # Real title ideally
        "XENON II TOMOYUKI",
        "Make A Difference",
        "Temple of Anubis"
    ]
    
    ocr_inputs = [
        "XENoW I -T瀬yuいの野望", # The messy one
        "5 Make A Difference",    # With extra number
        "Temple of Anubis"
    ]

    scorers = [
        fuzz.ratio,
        fuzz.partial_ratio,
        fuzz.token_sort_ratio,
        fuzz.token_set_ratio,
        fuzz.WRatio,
        fuzz.QRatio
    ]

    for ocr in ocr_inputs:
        print(f"\n--- Testing: '{ocr}' ---")
        for scorer in scorers:
            result = process.extractOne(ocr, songs, scorer=scorer)
            print(f"  {scorer.__name__}: {result}")

if __name__ == "__main__":
    debug_matcher()
