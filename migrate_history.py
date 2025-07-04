#!/usr/bin/env python3
"""
Historical Data Migration Script for Discord Support Bot

This script scans Discord message history for a specified date range
and populates the Google Sheet with historical support tickets.

Usage:
    python migrate_history.py

The script will scan messages from April 1st to June 30th by default.
You can modify the date ranges in the script if needed.
"""

import discord
import os
import requests
import json
import asyncio
import sys
from dotenv import load_dotenv
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

# Configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SUPPORT_CHANNEL_ID = int(os.getenv("SUPPORT_CHANNEL_ID", 0))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

def get_date_range():
    """Get date range from user input or command line arguments"""
    
    # Check if dates provided as command line arguments
    if len(sys.argv) >= 3:
        try:
            start_str = sys.argv[1]  # Format: YYYY-MM-DD
            end_str = sys.argv[2]    # Format: YYYY-MM-DD
            
            start_date = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end_date = datetime.strptime(end_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            
            return start_date, end_date
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)
    
    # Interactive prompts
    print("📅 Configure Date Range for Migration")
    print("=" * 40)
    print()
    
    # Suggest some common options
    print("🎯 Common options:")
    print("   1. Last 3 months")
    print("   2. All of 2024")  
    print("   3. All of 2025")
    print("   4. Custom date range")
    print()
    
    choice = input("Choose an option (1-4): ").strip()
    
    now = datetime.now(timezone.utc)
    
    if choice == "1":
        # Last 3 months
        start_date = datetime(now.year, now.month - 3 if now.month > 3 else now.month + 9, 1, tzinfo=timezone.utc)
        if now.month <= 3:
            start_date = start_date.replace(year=now.year - 1)
        end_date = now
        
    elif choice == "2":
        # All of 2024
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        
    elif choice == "3":
        # All of 2025
        start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        
    elif choice == "4":
        # Custom range
        print()
        print("Enter custom date range:")
        
        while True:
            try:
                start_str = input("Start date (YYYY-MM-DD): ").strip()
                start_date = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                break
            except ValueError:
                print("❌ Invalid format. Use YYYY-MM-DD (e.g., 2025-04-01)")
        
        while True:
            try:
                end_str = input("End date (YYYY-MM-DD): ").strip()
                end_date = datetime.strptime(end_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
                break
            except ValueError:
                print("❌ Invalid format. Use YYYY-MM-DD (e.g., 2025-06-30)")
    
    else:
        print("❌ Invalid choice. Using default: April-June 2025")
        start_date = datetime(2025, 4, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 6, 30, 23, 59, 59, tzinfo=timezone.utc)
    
    return start_date, end_date

# Get date range dynamically
START_DATE, END_DATE = get_date_range()

# Print configuration
print()
print(f"🔧 Configuration:")
print(f"   Support Channel ID: {SUPPORT_CHANNEL_ID}")
print(f"   Webhook URL: {WEBHOOK_URL}")
print(f"   Date Range: {START_DATE.date()} to {END_DATE.date()}")
print()

# Set up Discord client with necessary intents
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

def get_issue_type_from_tags(tags):
    """Extract issue type from forum tags and join them"""
    tag_names = [tag.name for tag in tags]
    if tag_names:
        return ", ".join(tag_names)
    return ""



def is_in_date_range(message_time):
    """Check if a message timestamp is within our target date range"""
    return START_DATE <= message_time <= END_DATE

def send_to_webhook(data):
    """Send data to the Google Apps Script webhook"""
    try:
        response = requests.post(WEBHOOK_URL, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error sending to webhook: {str(e)}")
        return False

async def process_thread_messages(thread, processed_threads):
    """Process all messages in a thread and return thread statistics"""
    thread_id = thread.id
    thread_title = thread.name
    
    # Skip if already processed
    if thread_id in processed_threads:
        return {"skipped": True}
    
    print(f"📂 Processing thread: {thread_title} (ID: {thread_id})")
    
    # Get all messages in the thread within our date range
    messages_in_range = []
    thread_starter = None
    
    try:
        async for message in thread.history(limit=None, oldest_first=True):
            if is_in_date_range(message.created_at):
                messages_in_range.append(message)
                
                # First message is the thread starter
                if not thread_starter:
                    thread_starter = message.author
    except Exception as e:
        print(f"❌ Error fetching messages from thread {thread_title}: {str(e)}")
        return {"error": True}
    
    if not messages_in_range:
        return {"no_messages_in_range": True}
    
    # Get issue type from thread tags
    issue_type = ""
    if hasattr(thread, "applied_tags"):
        issue_type = get_issue_type_from_tags(thread.applied_tags)
    
    # Find the first message (support query) to check for engineering mentions
    first_message_content = ""
    if messages_in_range:
        first_message_content = messages_in_range[0].content
    
    # Determine if this is an engineering issue
    # If first message mentions Siddhant (365127154847186945) or Prateeksha (535859343665397791), then is_engineering = False
    # Otherwise, is_engineering = True
    engineering_user_ids = ["365127154847186945", "535859343665397791"]  # Siddhant, Prateeksha
    found_mentions = [user_id for user_id in engineering_user_ids if user_id in first_message_content]
    is_engineering = len(found_mentions) == 0
    
    if found_mentions:
        # Convert user IDs to names for display
        user_names = []
        for user_id in found_mentions:
            if user_id == "365127154847186945":
                user_names.append("Siddhant")
            elif user_id == "535859343665397791":
                user_names.append("Prateeksha")
            else:
                user_names.append(f"UserID:{user_id}")
        print(f"  🔧 Engineering mentions found: {', '.join(user_names)} → is_engineering = False")
    else:
        print(f"  🏢 No engineering mentions found → is_engineering = True")
    
    # Process only the first message and first response
    messages_processed = 0
    first_message = None
    first_response = None
    
    # Find the first message (thread creation)
    for message in messages_in_range:
        if not message.author.bot:
            first_message = message
            break
    
    # Find the first response (from someone different than thread creator)
    if first_message:
        for message in messages_in_range:
            if (not message.author.bot and 
                message.author.id != first_message.author.id and
                message.created_at > first_message.created_at):
                first_response = message
                break
    
    # Process first message (thread creation)
    if first_message:
        message_data = {
            'thread_id': str(thread_id),
            'title': thread_title,
            'content': first_message.content,
            'author': str(first_message.author),
            'author_id': str(first_message.author.id),
            'timestamp': first_message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'thread_link': f"https://discord.com/channels/{first_message.guild.id}/{thread_id}",
            'type': issue_type,
            'event_type': 'thread_created',
            'is_engineering': is_engineering,
            'historical_import': True
        }
        
        if send_to_webhook(message_data):
            messages_processed += 1
            engineering_status = "Non-Engineering" if is_engineering else "Engineering"
            print(f"  ✅ Imported thread creation from {first_message.author} at {first_message.created_at.strftime('%Y-%m-%d %H:%M')} [{engineering_status}]")
        else:
            print(f"  ❌ Failed to import thread creation")
        
        await asyncio.sleep(0.1)
    
    # Process first response (if exists)
    if first_response:
        message_data = {
            'thread_id': str(thread_id),
            'title': thread_title,
            'content': first_response.content,
            'author': str(first_response.author),
            'author_id': str(first_response.author.id),
            'timestamp': first_response.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'thread_link': f"https://discord.com/channels/{first_response.guild.id}/{thread_id}",
            'type': issue_type,
            'event_type': 'thread_response',
            'is_engineering': is_engineering,
            'historical_import': True
        }
        
        if send_to_webhook(message_data):
            messages_processed += 1
            engineering_status = "Non-Engineering" if is_engineering else "Engineering"
            print(f"  ✅ Imported first response from {first_response.author} at {first_response.created_at.strftime('%Y-%m-%d %H:%M')} [{engineering_status}]")
        else:
            print(f"  ❌ Failed to import first response")
        
        await asyncio.sleep(0.1)
    else:
        print(f"  ℹ️  No response found in this thread")
    
    # Summary for this thread
    if not first_message:
        print(f"  ⚠️  No valid messages found in date range")
    
    processed_threads.add(thread_id)
    return {"messages_processed": messages_processed}

async def scan_channel_history():
    """Main function to scan the support channel for historical data"""
    print(f"🔍 Starting historical data migration...")
    print(f"📅 Scanning from {START_DATE.date()} to {END_DATE.date()}")
    print()
    
    support_channel = client.get_channel(SUPPORT_CHANNEL_ID)
    if not support_channel:
        print(f"❌ Error: Could not find support channel with ID {SUPPORT_CHANNEL_ID}")
        return
    
    print(f"📋 Found support channel: {support_channel.name}")
    
    # Check if it's a forum channel
    if not isinstance(support_channel, discord.ForumChannel):
        print(f"❌ Error: Channel is not a forum channel. This script is designed for forum-based support channels.")
        return
    
    # Get all threads (active and archived)
    threads_to_process = []
    
    # Get archived threads
    async for thread in support_channel.archived_threads(limit=None):
        if is_in_date_range(thread.created_at):
            threads_to_process.append(thread)
    
    # Get active threads
    for thread in support_channel.threads:
        if is_in_date_range(thread.created_at):
            threads_to_process.append(thread)
    
    print(f"🧵 Found {len(threads_to_process)} threads in the specified date range")
    print()
    
    # Sort threads by creation date for month breakpoints
    threads_to_process.sort(key=lambda t: t.created_at)
    
    # Process each thread with month breakpoints
    processed_threads = set()
    total_messages = 0
    total_threads = 0
    current_month = None
    
    for thread in threads_to_process:
        # Check if we've moved to a new month
        thread_month = thread.created_at.strftime("%Y-%m")
        if current_month != thread_month:
            if current_month is not None:  # Not the first month
                print()
                print("=" * 60)
                print(f"📅 MONTH BREAK: Moving from {current_month} to {thread_month}")
                print("=" * 60)
                print()
            else:
                print(f"📅 Starting with month: {thread_month}")
                print()
            current_month = thread_month
        result = await process_thread_messages(thread, processed_threads)
        
        if result.get("messages_processed", 0) > 0:
            total_messages += result["messages_processed"]
            total_threads += 1
        elif result.get("skipped"):
            print(f"⏭️  Skipped thread: {thread.name} (already processed)")
        elif result.get("no_messages_in_range"):
            print(f"📅 No messages in date range for thread: {thread.name}")
        elif result.get("error"):
            print(f"❌ Error processing thread: {thread.name}")
    
    print()
    print("=" * 60)
    print(f"✅ MIGRATION COMPLETED!")
    print("=" * 60)
    print(f"📊 Summary:")
    print(f"   - Threads processed: {total_threads}")
    print(f"   - Messages imported: {total_messages}")
    print(f"   - Date range: {START_DATE.date()} to {END_DATE.date()}")
    print(f"   - Data includes: Thread creation + All responses + Engineering classification")
    print(f"   - Engineering logic: is_engineering = False if first message contains Siddhant or Prateeksha user IDs")
    print(f"   - Note: Resolution timing to be calculated manually in your sheet")
    print("=" * 60)

@client.event
async def on_ready():
    print(f"🤖 Bot connected as {client.user}")
    print()
    
    try:
        await scan_channel_history()
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🔄 Closing connection...")
        await client.close()

def main():
    """Entry point for the script"""
    
    # Validate configuration
    if not DISCORD_TOKEN:
        print("❌ Error: DISCORD_TOKEN not found in environment variables")
        return
    
    if not SUPPORT_CHANNEL_ID:
        print("❌ Error: SUPPORT_CHANNEL_ID not found in environment variables")
        return
    
    if not WEBHOOK_URL:
        print("❌ Error: WEBHOOK_URL not found in environment variables")
        return
    
    print("🚀 Starting Discord Historical Data Migration")
    print("=" * 50)
    
    try:
        client.run(DISCORD_TOKEN)
    except discord.errors.LoginFailure:
        print("❌ ERROR: Invalid Discord token! Check your .env file.")
    except discord.errors.PrivilegedIntentsRequired:
        print("❌ ERROR: Message content intent is required but not enabled!")
        print("Please enable intents at: https://discord.com/developers/applications/")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 