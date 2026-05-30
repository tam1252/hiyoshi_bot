import discord
from discord import ui
import traceback


class TitleSelectMenu(ui.Select):
    def __init__(self, songs: list[str], current_title: str):
        current = current_title or ""
        options = [
            discord.SelectOption(
                label=song,
                value=song,
                default=(song == current),
            )
            for song in songs
        ]
        super().__init__(
            placeholder="曲名を選択...",
            options=options,
            custom_id="title_select",
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.data['title'] = self.values[0]
        # 選択後にembedを更新して反映を見せる
        embed = discord.Embed(title="OCR Result Preview", color=discord.Color.blue())
        embed.add_field(name="Date", value=self.view.data.get('date') or 'N/A', inline=True)
        embed.add_field(name="Player", value=self.view.username, inline=True)
        embed.add_field(name="Song", value=self.values[0], inline=True)
        embed.add_field(name="Score", value=str(self.view.data.get('score') or 'N/A'), inline=True)
        if self.view.image_url:
            embed.set_thumbnail(url=self.view.image_url)
        await interaction.response.edit_message(embed=embed, view=self.view)


class ScoreCorrectionModal(ui.Modal, title="スコア修正"):
    score_input = ui.TextInput(
        label="正しいスコア",
        style=discord.TextStyle.short,
        placeholder="1234",
        required=True,
        min_length=1,
        max_length=5,
    )

    def __init__(self, view, data, username, client, image_url, is_qualifier):
        super().__init__()
        self.original_view = view
        self.data = data
        self.username = username
        self.client = client
        self.image_url = image_url
        self.is_qualifier = is_qualifier
        self.score_input.default = str(data.get('score', 0))

    async def on_submit(self, interaction: discord.Interaction):
        try:
            self.data['score'] = int(self.score_input.value)
        except ValueError:
            await interaction.response.send_message("スコアは数値で入力してください。", ephemeral=True)
            return

        await interaction.response.defer()
        await self.original_view.finalize_submission(
            interaction,
            self.data,
            self.username,
            self.client,
            self.image_url,
            self.is_qualifier,
            is_modal=True,
        )


class VerificationView(ui.View):
    def __init__(self, data, username, client, image_url, is_qualifier=False, songs=None):
        super().__init__(timeout=None)
        self.data = data
        self.username = username
        self.client = client
        self.image_url = image_url
        self.is_qualifier = is_qualifier
        self.message = None

        if songs:
            self.add_item(TitleSelectMenu(songs, current_title=data.get('title', '')))

    @ui.button(label="送信", style=discord.ButtonStyle.green, custom_id="verify_submit")
    async def submit(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await self.finalize_submission(
            interaction,
            self.data,
            self.username,
            self.client,
            self.image_url,
            self.is_qualifier,
            is_modal=False,
        )

    @ui.button(label="スコアを修正", style=discord.ButtonStyle.secondary, custom_id="verify_edit")
    async def edit(self, interaction: discord.Interaction, button: ui.Button):
        modal = ScoreCorrectionModal(self, self.data, self.username, self.client, self.image_url, self.is_qualifier)
        await interaction.response.send_modal(modal)

    async def finalize_submission(self, interaction, data, username, client, image_url, is_qualifier, is_modal):
        try:
            status_text = ""
            if client.sheet_manager:
                success = client.sheet_manager.append_score(data, username, is_qualifier, worksheet_name="素データ")
                status_text = "スプレッドシートを更新しました！" if success else "スプレッドシートの更新に失敗しました。"
            else:
                status_text = "スプレッドシート連携は無効です。"

            embed = discord.Embed(title="New Score!", color=discord.Color.green())
            embed.add_field(name="Player", value=username, inline=True)
            embed.add_field(name="Song", value=data.get('title', 'Unknown'), inline=True)
            embed.add_field(name="Score", value=f"{data.get('score', 0):,}", inline=True)
            embed.add_field(name="Date", value=data.get('date', 'N/A'), inline=True)
            if image_url:
                embed.set_thumbnail(url=image_url)
            if interaction.channel:
                await interaction.channel.send(content="", embed=embed)

            final_content = (
                f"送信が完了しました！\n{status_text}\n\n"
                f"**登録内容**\n"
                f"曲名: {data.get('title')}\n"
                f"スコア: {data.get('score')}\n"
            )
            for child in self.children:
                child.disabled = True

            if is_modal:
                if self.message:
                    await self.message.edit(content=final_content, view=None, embed=None)
                else:
                    await interaction.followup.send("送信完了 (元のメッセージが見つかりませんでした)", ephemeral=True)
            else:
                await interaction.edit_original_response(content=final_content, view=None, embed=None)

        except Exception as e:
            print(f"Error in finalize_submission: {e}")
            traceback.print_exc()
            await interaction.followup.send(f"エラーが発生しました: {e}", ephemeral=True)
