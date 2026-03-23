import discord
from discord import app_commands
import os
import aiohttp
from datetime import datetime
from dotenv import load_dotenv
from src.ocr import IIDXReader
from src.sheets import SheetManager
from src.matcher import TitleMatcher
from src.ui import VerificationView

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
                    norm_date = ocr_date_str.replace('/', '-').replace('.', '-')
                    # Try to parse with time component first, then fall back to date only
                    if len(norm_date) >= 16 and ':' in norm_date:
                        image_dt = datetime.strptime(norm_date[:16], "%Y-%m-%d %H:%M")
                        # 12時間以内チェック
                        now = datetime.now()
                        elapsed = now - image_dt
                        if elapsed.total_seconds() > 12 * 3600:
                            await interaction.followup.send("リザルト画像の時刻から12時間以上経過しています。24時間以内のリザルト画像をアップロードしてください。")
                            return
                        if elapsed.total_seconds() < -3600:
                            # 画像の時刻が未来（1時間以上先）は異常
                            await interaction.followup.send("画像の時刻が不正です。正しいリザルト画像をアップロードしてください。")
                            return
                        date_obj = image_dt
                    else:
                        date_obj = datetime.strptime(norm_date[:10], "%Y-%m-%d")

                    if EVENT_START_DATE and EVENT_END_DATE:
                        start_obj = datetime.strptime(EVENT_START_DATE, "%Y-%m-%d")
                        end_obj = datetime.strptime(EVENT_END_DATE, "%Y-%m-%d")

                        if not (start_obj <= date_obj <= end_obj):
                            await interaction.followup.send("指定期間外のリザルトです。予選期間内の画像をアップロードしてください。")
                            return
                except Exception as e:
                    print(f"Date Parsing Warning: {e}")
            else:
                await interaction.followup.send("画像から日付を読み取れませんでした。鮮明な画像をアップロードしてください。")
                return

            # --- Title Fuzzy Matching ---
            raw_title = data.get('title')
            corrected_title = client.matcher.correct_title(raw_title)
            data['title'] = corrected_title


            # Get username
            username = interaction.user.display_name
            
            # Format reply (Preview for Verification)
            reply_text = "### OCR Result Preview\n"
            reply_text += "以下の内容で登録します。問題なければ「送信」、間違っていれば「修正」を押してください。\n"
            
            # Create Embed for preview
            embed = discord.Embed(title="OCR Result Preview", color=discord.Color.blue())
            embed.add_field(name="Date", value=data.get('date') or 'N/A', inline=True)
            embed.add_field(name="Player", value=username, inline=True)
            embed.add_field(name="Song", value=data.get('title') or 'N/A', inline=True)
            embed.add_field(name="Score", value=str(data.get('score') or 'N/A'), inline=True)
            
            # Image URL for embed
            # discord.Attachment has a 'url' property
            image_url = image.url
            embed.set_thumbnail(url=image_url)
            
            # Check for qualifier role
            is_qualifier = False
            if isinstance(interaction.user, discord.Member):
                role_names = [role.name for role in interaction.user.roles]
                if "鍵盤最強王予選参加者" in role_names:
                    is_qualifier = True
            
            # Create View
            view = VerificationView(data, username, client, image_url, is_qualifier)
            
            # Send Ephemeral Message with View
            # Using followup because we deferred
            message = await interaction.followup.send(content=reply_text, embed=embed, view=view, ephemeral=True)
            view.message = message
        
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
