from src.matcher import TitleMatcher
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv(".env")

def verify_logic():
    print("--- Verifying Title Matcher ---")
    matcher = TitleMatcher()
    
    test_titles = [
        "XENoW I -T瀬yuいの野望", # Expected: XENON II TOMOYUKI
        "Make A Difference",      # Expected: Make A Difference
        "Temple of Anubiss",      # Expected: Temple of Anubis (typo)
        "Totally Wrong Song"      # Expected: Totally Wrong Song (no match)
    ]
    
    for t in test_titles:
        corrected = matcher.correct_title(t)
        print(f"Original: '{t}' -> Corrected: '{corrected}'")

    print("\n--- Verifying Date Filtering ---")
    # Hardcoded for verification to bypass env loading issues in script
    start_date = "2025-01-01"
    end_date = "2026-12-31"
    print(f"Range: {start_date} to {end_date}")
    
    test_dates = [
        "2025-12-23", # Valid
        "2024-12-31", # Too early
        "2027-01-01", # Too late
        "2026/01/01"  # Valid format
    ]
    
    start_obj = datetime.strptime(start_date, "%Y-%m-%d")
    end_obj = datetime.strptime(end_date, "%Y-%m-%d")

    for d in test_dates:
        norm_date = d.replace('/', '-').replace('.', '-')
        try:
            date_obj = datetime.strptime(norm_date[:10], "%Y-%m-%d")
            is_valid = start_obj <= date_obj <= end_obj
            print(f"Date: {d} -> Valid: {is_valid}")
        except Exception as e:
            print(f"Date: {d} -> Error: {e}")

if __name__ == "__main__":
    verify_logic()
