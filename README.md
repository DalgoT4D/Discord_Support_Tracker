# Discord Support Tracker Bot

Automated Discord bot that tracks support tickets in a forum channel and logs everything to Google Sheets.

## Features

- **Auto-logging**: New tickets automatically logged to Google Sheets
- **Response tracking**: Records first responder and response time
- **Tag sync**: Tag changes in Discord reflect in the sheet
- **Title sync**: Title changes in Discord reflect in the sheet
- **Resolution tracking**: Calculates time to resolution, sends warning message to user
- **Reopen detection**: Tracks reopened tickets, edits warning message
- **SLA alerts**: Sends alert if no response within 1 hour
- **Business hours**: Flags tickets created outside 9am-6pm IST (Mon-Fri)
- **Team classification**: Auto-classifies team (Engineering/Consulting) based on tags

---

## Setup Guide

### Step 1: Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** → Give it a name (e.g., "Dalgo Support Bot")
3. Go to **Bot** tab on the left sidebar
4. Click **"Add Bot"** → Confirm
5. Under **Privileged Gateway Intents**, enable:
   - ✅ **Message Content Intent**
6. Click **"Reset Token"** → Copy the token (save it securely, you'll need it later)

### Step 2: Invite Bot to Your Server

1. In Developer Portal, go to **OAuth2** → **URL Generator**
2. Under **Scopes**, select:
   - ✅ `bot`
3. Under **Bot Permissions**, select:
   - ✅ Read Messages/View Channels
   - ✅ Send Messages
   - ✅ Read Message History
   - ✅ Add Reactions
4. Copy the generated URL at the bottom
5. Open the URL in browser → Select your server → Authorize

### Step 3: Get Channel IDs

1. In Discord, go to **User Settings** → **Advanced** → Enable **Developer Mode**
2. Right-click on your **support forum channel** → **Copy Channel ID**
   - This is your `SUPPORT_CHANNEL_ID`
3. Right-click on the channel(s) where you want **SLA alerts** → **Copy Channel ID**
   - These are your `ALERT_CHANNEL_IDS` (comma-separated if multiple)

### Step 4: Set Up Google Sheet

1. Create a new Google Sheet
2. Go to **Extensions** → **Apps Script**
3. Delete any existing code in the editor
4. Copy the entire contents of `google_apps_script.js` from this repo and paste it
5. Click **Save** (Ctrl+S or Cmd+S)
6. Click **Deploy** → **New deployment**
7. Click the gear icon ⚙️ next to "Select type" → Choose **Web app**
8. Configure:
   - Description: "Discord Support Bot Webhook"
   - Execute as: **Me**
   - Who has access: **Anyone**
9. Click **Deploy**
10. Click **Authorize access** → Choose your Google account → Allow
11. Copy the **Web app URL** (this is your `WEBHOOK_URL`)

> **Note**: If you update the Apps Script code later, you need to create a **New deployment** for changes to take effect.

### Step 5: Configure the Bot

1. Clone or download this repository

2. Install Python dependencies using uv:
   ```bash
   # Option 1: Using uv sync (recommended)
   uv sync

   # Option 2: Using uv pip
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -r requirements.txt
   ```

3. Create your `.env` file:
   ```bash
   cp .env.example .env
   ```

4. Edit `.env` with your values:
   ```env
   # Your Discord bot token from Step 1
   DISCORD_TOKEN=MTIzNDU2Nzg5.ABC.xyz...

   # Support forum channel ID from Step 3
   SUPPORT_CHANNEL_ID=1234567890123456789

   # Google Apps Script URL from Step 4
   WEBHOOK_URL=https://script.google.com/macros/s/ABC123.../exec

   # Alert channel IDs (comma-separated) from Step 3
   ALERT_CHANNEL_IDS=1111111111111111111,2222222222222222222
   ```

### Step 6: Run the Bot

```bash
# Using uv (recommended)
uv run python discord_support_bot.py

# Or with activated venv
python discord_support_bot.py
```

You should see:
```
Support Channel ID: 1234567890123456789
Webhook URL: https://script.google.com/...
Alert Channel IDs: [1111111111111111111, 2222222222222222222]
Starting Discord Support Bot...
Business hours: 9:00 - 18:00 IST (Mon-Fri)
Bot is ready! Logged in as Dalgo Support Bot#1234
Connected to guild: Your Server Name
✅ Found support channel: support
```

### Step 7: Test the Bot

1. Create a new thread in your support forum channel
2. Check that:
   - ✅ Bot adds a checkmark reaction to the first message
   - ✅ A new row appears in your Google Sheet
3. Reply to the thread (with a different user)
4. Check that `first_responded_by` and `time_to_first_response` are updated
5. Add a "resolved" tag to the thread
6. Check that the bot posts a warning message and updates the sheet

---

## Google Sheet Columns

| Column | Description | Example |
|--------|-------------|---------|
| thread_id | Unique Discord thread ID | 1234567890 |
| title | Thread title | "Dashboard not loading" |
| type | Tags/categories | "Platform Issue, Bug" |
| raised_by | Who created the ticket | "user#1234" |
| date_created | When ticket was created | "2026-02-04 10:30:00" |
| first_responded_by | Who responded first | "support#5678" |
| time_to_first_response | Time until first response | "25m 30s" |
| time_to_resolution | Time to resolve | "2d 4h 15m" |
| resolution_date | When ticket was resolved | "2026-02-06 14:45:00" |
| link | Direct link to Discord thread | https://discord.com/... |
| team | Team assignment based on tag | Engineering / Consulting / (empty) |
| outside_business_hours | Created outside 9-6 IST Mon-Fri | TRUE / FALSE |
| reopen_count | How many times reopened | 0, 1, 2... |
| warning_message_id | ID of the resolved message | 9876543210 |

---

## How It Works

| Event | Bot Action | Sheet Update |
|-------|------------|--------------|
| New thread created | Logs ticket, adds ✅, starts 1hr SLA timer | New row created |
| Support responds (first time) | Records responder, cancels SLA timer | `first_responded_by`, `time_to_first_response` |
| Tags changed | Updates type | `type` |
| Title changed | Updates title | `title` |
| "resolved" tag added | Sends warning message, logs resolution | `resolution_date`, `time_to_resolution`, `warning_message_id` |
| "resolved" tag removed | Edits warning to "reopened" | `reopen_count` +1 |
| 1 hour with no response | Sends SLA alert to alert channels | None |

---

## Alert Messages

**When Resolved** (posted in thread):
```
🔴 @user This thread has been marked as RESOLVED.

We will no longer monitor this thread for new messages.
If you have a new issue or follow-up question, please create a new thread.

Thank you for reaching out to Dalgo Support!
```

**When Reopened** (edits above message):
```
🟢 UPDATE: This thread has been REOPENED!

We're continuing the conversation here.
Our support team will follow up shortly.
```

**SLA Alert** (sent to alert channels):
```
⚠️ SLA ALERT: Ticket Awaiting Response

📋 Title: Dashboard not loading
👤 Raised by: user#1234
⏰ Waiting: 1 hour
🏷️ Team: Engineering
🔗 Link: Click to view

Please respond to this ticket as soon as possible.
```

---

## Production Deployment

### Option 1: PM2 (Recommended)

```bash
# Install PM2
npm install -g pm2

# Start the bot with uv
pm2 start "uv run python discord_support_bot.py" --name support-bot

# Or with regular python (if venv activated)
pm2 start discord_support_bot.py --interpreter python3 --name support-bot

# Save process list and enable startup
pm2 save
pm2 startup
```

### Option 2: systemd (Linux)

Create `/etc/systemd/system/discord-support-bot.service`:

```ini
[Unit]
Description=Discord Support Tracker Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/Discord_Support_Tracker
ExecStart=/home/your_username/.cargo/bin/uv run python discord_support_bot.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

> **Note**: Update the `uv` path based on your installation. Find it with `which uv`.

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable discord-support-bot
sudo systemctl start discord-support-bot

# Check status
sudo systemctl status discord-support-bot

# View logs
sudo journalctl -u discord-support-bot -f
```

---

## Business Rules

| Rule | Value |
|------|-------|
| Business Hours | 9:00 AM - 6:00 PM IST |
| Business Days | Monday to Friday |
| SLA Timeout | 1 hour (single alert per ticket) |
| Team Assignment | Based on "Engineering" or "Consulting" tag |
| First Response | Only counts non-creator, non-bot responses |

---

## Troubleshooting

### Bot not starting
- Check your `DISCORD_TOKEN` is correct
- Ensure Message Content Intent is enabled in Developer Portal

### Messages not logged to sheet
- Test your webhook URL by visiting it in browser (should show "Webhook is active")
- Check Apps Script deployment is set to "Anyone" access
- Create a new deployment if you updated the script

### SLA alerts not sending
- Verify `ALERT_CHANNEL_IDS` are correct
- Bot needs permission to send messages in those channels

### Bot not detecting threads
- Verify `SUPPORT_CHANNEL_ID` is a forum channel (not a regular text channel)
- Check bot has permission to view the channel

---

## File Structure

```
Discord_Support_Tracker/
├── discord_support_bot.py    # Main bot script
├── google_apps_script.js     # Google Apps Script (copy to your sheet)
├── pyproject.toml            # Project config (for uv sync)
├── requirements.txt          # Python dependencies (fallback)
├── .env.example              # Environment variables template
├── .env                      # Your configuration (create this)
├── README.md                 # This file
├── PRD_Discord_Support_Bot.md    # Product requirements document
└── Support_Bot_Summary.md    # Quick reference guide
```
