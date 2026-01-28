import discord
from discord import app_commands
import os
import aiohttp
from datetime import datetime
from dotenv import load_dotenv
from src.ocr import IIDXReader
from src.sheets import SheetManager
from src.matcher import TitleMatcher

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SPREADSHEET_KEY = os.getenv('SPREADSHEET_KEY')
GUILD_ID = os.getenv('GUILD_ID') # Optional: for instant sync in dev server
EVENT_START_DATE = os.getenv('EVENT_START_DATE')
EVENT_END_DATE = os.getenv('EVENT_END_DATE')
SERVICE_ACCOUNT_PATH = "service_account.json"

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.ocr_reader = None
        self.sheet_manager = None
        self.matcher = None

    async def setup_hook(self):
        # Initialize modules
        print("Initializing OCR Reader...")
        self.ocr_reader = IIDXReader()
        print("OCR Reader Ready.")
        
        if SPREADSHEET_KEY and os.path.exists(SERVICE_ACCOUNT_PATH):
            print("Initializing Sheet Manager...")
            self.sheet_manager = SheetManager(SERVICE_ACCOUNT_PATH)
            try:
                self.sheet_manager.connect(SPREADSHEET_KEY)
                print("Sheet Manager Connected.")
            except Exception as e:
                print(f"Sheet Connection Failed: {e}")
                self.sheet_manager = None
        else:
            print("Spreadsheet configuration missing. Sheets disabled.")

        print("Initializing Title Matcher...")
        self.matcher = TitleMatcher()
        print("Title Matcher Ready.")

        # Sync commands
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Commands synced to guild {GUILD_ID}.")
        else:
            await self.tree.sync()
            print("Commands synced globally (may take up to 1 hour).")

client = MyClient()

@client.tree.command(name="result", description="日吉マスターズ予選のリザルト画像を登録します")
@app_commands.describe(image="リザルト画像")
async def result(interaction: discord.Interaction, image: discord.Attachment):
    # Defer response as OCR might take time
    await interaction.response.defer(ephemeral=True)

    if not image.content_type or not image.content_type.startswith('image/'):
        await interaction.followup.send("画像ファイルをアップロードしてください。")
        return

    try:
        # Download image
        image_bytes = await image.read()
        
        # Save temporary file for OpenCV
        # src/ocr.py expects a file path.
        temp_filename = f"temp_{interaction.id}_{image.filename}"
        with open(temp_filename, 'wb') as f:
            f.write(image_bytes)
        
        try:
            # Run OCR
            data = client.ocr_reader.extract_data(temp_filename)
            
            # --- Date Filtering ---
            ocr_date_str = data.get('date')
            if ocr_date_str:
                try:
                    # Cloud Vision usually returns YYYY-MM-DD HH:MM
                    # Or verify_ocr output format which is similar
                    # Let's handle generic ISO-like formats
                    # Normalize separators
                    norm_date = ocr_date_str.replace('/', '-').replace('.', '-')
                    # Parse just the date part (first 10 chars should be YYYY-MM-DD)
                    date_obj = datetime.strptime(norm_date[:10], "%Y-%m-%d")
                    
                    if EVENT_START_DATE and EVENT_END_DATE:
                        start_obj = datetime.strptime(EVENT_START_DATE, "%Y-%m-%d")
                        end_obj = datetime.strptime(EVENT_END_DATE, "%Y-%m-%d")
                        
                        if not (start_obj <= date_obj <= end_obj):
                            await interaction.followup.send(f"⚠️ 指定期間外のリザルトです。予選期間内の画像をアップロードしてください。")
                            return
                except Exception as e:
                    print(f"Date Parsing Warning: {e}")
            else:
                 # If no date found, what to do? User said: "入っていない場合は...受け取るようにして欲しい"(Only strict filtering mentioned). 
                 # Usually safest to block if strict, or warn. 
                 # "指定期間内のリザルトをアップロードしてください" implies rejection if not verified.
                 # Let's assume rejection if no date found? Or let it pass if date is missing (OCR failure)?
                 # "日付について...入っているものだけを受け取る" implies strict -> Reject on missing date.
                 await interaction.followup.send(f"⚠️ 画像から日付を読み取れませんでした。鮮明な画像をアップロードしてください。")
                 return

            # --- Title Fuzzy Matching ---
            raw_title = data.get('title')
            corrected_title = client.matcher.correct_title(raw_title)
            data['title'] = corrected_title


            # Get username
            username = interaction.user.display_name
            
            # Format reply
            reply_text = "### OCR Result\n"
            reply_text += f"**Date**: {data.get('date') or 'N/A'}\n"
            reply_text += f"**Player**: {username}\n"
            reply_text += f"**Song**: {data.get('title') or 'N/A'}\n"
            reply_text += f"**Score**: {data.get('score') or 'N/A'}\n"
            
            # Append to sheets
            if client.sheet_manager:
                success = client.sheet_manager.append_score(data, username, worksheet_name="素データ")
                if success:
                    reply_text += "\n✅ **Spreadsheet updated!**"
                else:
                    reply_text += "\n❌ **Failed to update spreadsheet.**"
            else:
                reply_text += "\n⚠️ Spreadsheet Integration disabled."
            
            await interaction.followup.send(reply_text)
        
        except Exception as e:
            await interaction.followup.send(f"Error processing image: {e}")
            print(f"OCR Error: {e}")
        
        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}")
        print(f"Global Error: {e}")

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN is not set in .env")
    else:
        client.run(TOKEN)
