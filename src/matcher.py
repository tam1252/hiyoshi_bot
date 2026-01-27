from rapidfuzz import process, fuzz
import os

class TitleMatcher:
    def __init__(self, song_list_path="songs.txt"):
        self.songs = []
        if os.path.exists(song_list_path):
            with open(song_list_path, 'r', encoding='utf-8') as f:
                self.songs = [line.strip() for line in f if line.strip()]
        else:
            print(f"Warning: {song_list_path} not found. Fuzzy matching disabled.")

    def correct_title(self, ocr_title):
        """
        Returns the best matching title from the song list.
        If no songs are loaded or match score is too low, returns original.
        """
        if not self.songs or not ocr_title:
            return ocr_title

        # extractOne returns (match, score, index)
        # WRatio handles case, partial matching, and sorting well
        result = process.extractOne(ocr_title, self.songs, scorer=fuzz.WRatio)
        
        if result:
            match, score, _ = result
            print(f"DEBUG: Matching '{ocr_title}' -> '{match}' (Score: {score})")
            
            # Lower threshold for messy OCR
            if score >= 45.0:
                return match
        
        return ocr_title

if __name__ == "__main__":
    # Test
    matcher = TitleMatcher()
    print(matcher.correct_title("XENoW I -T瀬yuいの野望"))
