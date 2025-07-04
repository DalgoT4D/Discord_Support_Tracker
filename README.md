# Discord Support Bot
Link to the google sheet:
https://docs.google.com/spreadsheets/d/1kDKEkdfcYMQN5Hn4BAIDwHfA6h5340RiIp7AJXRl0RI/edit?usp=sharing

A simple Discord bot that forwards support requests to a Google Sheet using Google Apps Script.

## Setup

1. **Create a Discord Bot**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a New Application
   - Go to the Bot tab and create a bot
   - Enable Message Content Intent
   - Copy the bot token

2. **Set Up Google Apps Script**
   - Create a Google Sheet with columns for title, user, date, and engineering classification
   - Open Script Editor (Extensions > Apps Script)  
   - Copy the code from `google_apps_script_example.js` into the editor (includes `is_engineering` field support)
   - Deploy as web app:
     - Click "Deploy" > "New deployment"
     - Select type: "Web app"
     - Set "Who has access" to "Anyone"
     - Click "Deploy"
     - Copy the web app URL
   - **Important**: Make sure your script has both `doPost()` and `doGet()` functions

3. **Install the Bot**
   - Clone this repository
   - Install dependencies: `pip install -r requirements.txt`
   - Copy `.env.example` to `.env` and fill in your details:
     - Add your Discord token
     - Add your support channel ID
     - Add your Google Apps Script web app URL

## Usage

### Option 1: Real-time Bot (24/7 monitoring)
Run the bot:
```
python discord_support_bot.py
```

The bot will:
1. Monitor the specified support channel
2. Send any messages to your Google Apps Script webhook
3. React with ✅ when successfully logged or ❌ if there was an error

### Option 2: Monthly Data Collection (Recommended)
Instead of running a persistent bot, you can use the migration script monthly:

```
python migrate_history.py
```

This approach is:
- **Simpler**: No need to keep a bot running 24/7
- **More reliable**: No risk of bot downtime
- **Same data**: Captures all threads and responses (resolution timing done manually)
- **Visual breakpoints**: Shows clear month separators during import

**Setting up a monthly cron job:**
```bash
# Edit your crontab
crontab -e

# Add this line to run on the 1st of every month at 9 AM
0 9 1 * * cd /path/to/your/discord_bot && python migrate_history.py

# Or run weekly on Mondays at 9 AM  
0 9 * * 1 cd /path/to/your/discord_bot && python migrate_history.py
```

**Customizing the date range:**
Edit the `START_DATE` and `END_DATE` variables in `migrate_history.py`:
```python
# For April-June 2024
START_DATE = datetime(2024, 4, 1, tzinfo=timezone.utc)
END_DATE = datetime(2024, 6, 30, 23, 59, 59, tzinfo=timezone.utc)

# For previous month (dynamic)
from dateutil.relativedelta import relativedelta
today = datetime.now(timezone.utc)
START_DATE = (today - relativedelta(months=1)).replace(day=1, hour=0, minute=0, second=0)
END_DATE = today.replace(day=1, hour=0, minute=0, second=0) - timedelta(seconds=1)
```

## Troubleshooting

- If you see the error "Script function not found: doGet", make sure your Apps Script includes a `doGet()` function
- If the bot isn't connecting to Discord, check your token
- If messages aren't being logged, ensure your webhook URL is correct and the Apps Script is deployed as a web app

## Historical Data Migration

To import historical data from specific months (like April-June), run:
```
python migrate_history.py
```

The script will:
1. Scan all threads in the specified date range (with visual month breakpoints)
2. Import thread creation and all response messages
3. Classify threads as engineering vs non-engineering based on mentions
4. Send everything to your Google Sheet using the same webhook
5. **Note**: Resolution timing calculations are left for manual handling in your sheet

**Engineering Classification Logic:**
- If the first message (support query) contains Siddhant (ID: 365127154847186945) or Prateeksha (ID: 535859343665397791) → `is_engineering = false`
- Otherwise → `is_engineering = true`

**Date Range Options:**
```bash
# Interactive mode (prompts for date selection)
python migrate_history.py

# Command line mode (specify dates directly)
python migrate_history.py 2025-04-01 2025-06-30
```

## Deployment

### For Real-time Bot:
- Use a systemd service (Linux)
- Run with PM2: `pm2 start discord_support_bot.py --interpreter python`
- Use Docker: `docker run -d --name discord-bot -v $(pwd):/app python:3.9 python /app/discord_support_bot.py`

### For Monthly Collection:
- Set up a cron job (see Usage section above)
- Much simpler - no persistent service needed! 

