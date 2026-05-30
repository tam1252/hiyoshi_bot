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
        Always returns a candidate from songs.txt if the list is loaded.
        """
        if not self.songs:
            return ocr_title

        if not ocr_title:
            return self.songs[0]

        result = process.extractOne(ocr_title, self.songs, scorer=fuzz.WRatio)

        if result:
            match, score, _ = result
            print(f"DEBUG: Matching '{ocr_title}' -> '{match}' (Score: {score})")
            return match

        return self.songs[0]

if __name__ == "__main__":
    # Test
    matcher = TitleMatcher()
    print(matcher.correct_title("XENoW I -T瀬yuいの野望"))
