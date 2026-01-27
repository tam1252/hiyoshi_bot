# Hiyoshi Bot - Setup Guide

This bot extracts Beatmania IIDX result data from images posted on Discord and saves them to a Google Sheet.

## Prerequisites

- Python 3.13+
- `uv` (dependency manager)
- Discord Bot Token
- Google Service Account (JSON)

## Setup

1.  **Install Dependencies**:
    ```bash
    uv sync
    ```

2.  **Environment Variables**:
    Create a `.env` file in the root directory:
    ```bash
    DISCORD_TOKEN=your_discord_bot_token_here
    SPREADSHEET_KEY=your_google_sheet_key_here
    ```

3.  **Google Sheets Setup**:
    - Place your Service Account JSON file as `service_account.json` in the root directory.
    - Share your Google Sheet with the Service Account email address (found in the JSON).

## Running

Start the bot:
```bash
uv run python bot.py
```

## Usage

1.  Invite the bot to your Discord server.
2.  Use the slash command:
    ```
    /result image:[upload your image]
    ```
3.  The bot will reply with the extracted data and update the spreadsheet.
    - Sheet Columns: `Date`, `User Name`, `Song Title`, `Score`

## Note
- This bot uses **Google Cloud Vision API**. Please ensure:
    - Steps in `service_account.json` are correct.
    - **Billing is enabled** for your Google Cloud Project.
    - **Cloud Vision API is enabled** in the Google Cloud Console.
