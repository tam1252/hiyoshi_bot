import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

class SheetManager:
    def __init__(self, key_path="service_account.json"):
        self.key_path = key_path
        self.client = None
        self.workbook = None
        self.sheet = None

    def connect(self, sheet_key):
        """Connects to Google Sheets using the service account."""
        if not os.path.exists(self.key_path):
            raise FileNotFoundError(f"Service account file not found: {self.key_path}")
        
        creds = Credentials.from_service_account_file(self.key_path, scopes=SCOPES)
        self.client = gspread.authorize(creds)
        
        # Open by key
        self.workbook = self.client.open_by_key(sheet_key)
        self.sheet = self.workbook.sheet1

    def append_score(self, data, username, worksheet_name=None):
        """
        Appends a score entry to the sheet.
        Columns: [Date, User Name, Song Title, Score]
        """
        if not self.workbook:
            raise RuntimeError("Sheet not connected. Call connect() first.")

        # Determine target sheet
        target_sheet = self.sheet
        if worksheet_name:
            try:
                target_sheet = self.workbook.worksheet(worksheet_name)
            except gspread.WorksheetNotFound:
                print(f"Worksheet '{worksheet_name}' not found. Falling back to default.")
                # target_sheet remains self.sheet (sheet1)
            except Exception as e:
                print(f"Error fetching worksheet '{worksheet_name}': {e}")
                return False

        # Prepare row
        ocr_date = data.get('date')
        if not ocr_date:
            # Fallback to current date if OCR failed
            ocr_date = datetime.now().strftime("%Y-%m-%d %H:%M")
            
        title = data.get('title', '') or 'Unknown'
        score = data.get('score', '') or 0
        
        # [Date, User Name, Song Title, Score]
        row = [ocr_date, username, title, score]
        
        try:
            target_sheet.append_row(row)
            return True
        except Exception as e:
            print(f"Error appending to sheet: {e}")
            return False

if __name__ == "__main__":
    # Test block (requires env vars or real files)
    import dotenv
    dotenv.load_dotenv()
    
    sheet_key = os.getenv("SPREADSHEET_KEY")
    if sheet_key:
        print(f"Connecting to sheet {sheet_key}...")
        sm = SheetManager()
        try:
            sm.connect(sheet_key)
            print("Connected!")
            # sm.append_score({"date": "2026-01-01", "title": "Test Song", "score": 1234})
        except Exception as e:
            print(f"Connection failed: {e}")
    else:
        print("SPREADSHEET_KEY not set in env.")
