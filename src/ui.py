import discord
from discord import ui
import traceback

class ScoreCorrectionModal(ui.Modal, title="スコア修正"):
    score_input = ui.TextInput(
        label="正しいスコア",
        style=discord.TextStyle.short,
        placeholder="1234",
        required=True,
        min_length=1,
        max_length=5
    )

    def __init__(self, view, data, username, client, image_url):
        super().__init__()
        self.original_view = view
        self.data = data
        self.username = username
        self.client = client
        self.image_url = image_url
        # Set default value
        self.score_input.default = str(data.get('score', 0))

    async def on_submit(self, interaction: discord.Interaction):
        # Update score
        try:
            # Full-width to half-width conversion just in case, though usually int() handles simple cases? 
            # int() handles stick '123' but not fullwidth '１２３' without help in some versions? 
            # Actually python int() handles fullwidth digits fine.
            val = self.score_input.value
            new_score = int(val)
            self.data['score'] = new_score
        except ValueError:
            await interaction.response.send_message("スコアは数値で入力してください。", ephemeral=True)
            return

        # Defer to prevent interaction failure
        await interaction.response.defer()

        # Proceed to submission
        # We need to update the original message to reflect the new state (Confirmed)
        await self.original_view.finalize_submission(interaction, self.data, self.username, self.client, self.image_url, is_modal=True)


class VerificationView(ui.View):
    def __init__(self, data, username, client, image_url):
        super().__init__(timeout=None)
        self.data = data
        self.username = username
        self.client = client
        self.image_url = image_url
        self.message = None # To be set after sending

    @ui.button(label="送信", style=discord.ButtonStyle.green, custom_id="verify_submit")
    async def submit(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await self.finalize_submission(interaction, self.data, self.username, self.client, self.image_url, is_modal=False)

    @ui.button(label="修正", style=discord.ButtonStyle.secondary, custom_id="verify_edit")
    async def edit(self, interaction: discord.Interaction, button: ui.Button):
        modal = ScoreCorrectionModal(self, self.data, self.username, self.client, self.image_url)
        await interaction.response.send_modal(modal)

    async def finalize_submission(self, interaction, data, username, client, image_url, is_modal):
        try:
            # 1. Write to sheet
            status_text = ""
            if client.sheet_manager:
                success = client.sheet_manager.append_score(data, username, worksheet_name="素データ")
                if success:
                    status_text = "スプレッドシートを更新しました！"
                else:
                    status_text = "スプレッドシートの更新に失敗しました。"
            else:
                status_text = "スプレッドシート連携は無効です。"

            # 2. Public Embed
            embed = discord.Embed(title="New Score!", color=discord.Color.green())
            embed.add_field(name="Player", value=username, inline=True)
            embed.add_field(name="Song", value=data.get('title', 'Unknown'), inline=True)
            embed.add_field(name="Score", value=f"{data.get('score', 0):,}", inline=True)
            embed.add_field(name="Date", value=data.get('date', 'N/A'), inline=True)
            
            if image_url:
                embed.set_thumbnail(url=image_url)
            
            # Send to the channel (public)
            if interaction.channel:
                 await interaction.channel.send(content=f"{username} が予選スコアを提出しました！", embed=embed)

            # 3. Update Ephemeral Message (The View)
            final_content = (
                f"送信が完了しました！\n{status_text}\n\n"
                f"**登録内容**\n"
                f"曲名: {data.get('title')}\n"
                f"スコア: {data.get('score')}\n"
            )
            
            # Disable buttons
            for child in self.children:
                child.disabled = True
            
            # Update the private message
            if is_modal:
                # Modal interaction deferred. checking self.message
                if self.message:
                    await self.message.edit(content=final_content, view=None, embed=None)
                else:
                    # Fallback if message not tracked (should not happen if set correctly)
                    await interaction.followup.send("送信完了 (元のメッセージが見つかりませんでした)", ephemeral=True)
            else:
                # Button interaction deferred.
                await interaction.edit_original_response(content=final_content, view=None, embed=None)
                
        except Exception as e:
            print(f"Error in finalize_submission: {e}")
            traceback.print_exc()
            await interaction.followup.send(f"エラーが発生しました: {e}", ephemeral=True)
