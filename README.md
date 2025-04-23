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
   - Create a Google Sheet with columns for title, user, and date
   - Open Script Editor (Extensions > Apps Script)
   - Copy the code from `google_apps_script_example.js` into the editor
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

Run the bot:
```
python discord_support_bot.py
```

The bot will:
1. Monitor the specified support channel
2. Send any messages to your Google Apps Script webhook
3. React with ✅ when successfully logged or ❌ if there was an error

## Troubleshooting

- If you see the error "Script function not found: doGet", make sure your Apps Script includes a `doGet()` function
- If the bot isn't connecting to Discord, check your token
- If messages aren't being logged, ensure your webhook URL is correct and the Apps Script is deployed as a web app

## Deployment

For production, you can:
- Use a systemd service (Linux)
- Run with PM2: `pm2 start discord_support_bot.py --interpreter python`
- Use Docker: `docker run -d --name discord-bot -v $(pwd):/app python:3.9 python /app/discord_support_bot.py` 

