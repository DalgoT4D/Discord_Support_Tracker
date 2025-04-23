import discord
import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

# Configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SUPPORT_CHANNEL_ID = int(os.getenv("SUPPORT_CHANNEL_ID", 0))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

# Print configuration for debugging
print(f"Support Channel ID configured as: {SUPPORT_CHANNEL_ID}")
print(f"Webhook URL configured as: {WEBHOOK_URL}")

# Set up Discord client with necessary intents
intents = discord.Intents.default()
intents.message_content = True  # Required for reading message content
client = discord.Client(intents=intents)

# Tags that indicate a thread is resolved
RESOLVED_TAGS = ["resolved"]

def get_issue_type_from_tags(tags):
    """Extract issue type from forum tags and join them"""
    tag_names = [tag.name for tag in tags]
    
    # Join all tags with commas, or return empty list if none found
    if tag_names:
        return ", ".join(tag_names)
    return ""  # Return empty string if no tags found

def is_thread_resolved(tags):
    """Check if any of the tags indicate the thread is resolved"""
    for tag in tags:
        if tag.name.lower() in RESOLVED_TAGS:
            return True
    return False

@client.event
async def on_ready():
    print(f"Bot is ready! Logged in as {client.user}")
    
    # Analyze the channel structure
    for guild in client.guilds:
        print(f"Connected to guild: {guild.name}")
        
        # Try to find our support channel
        support_channel = None
        for channel in guild.channels:
            if channel.id == SUPPORT_CHANNEL_ID:
                support_channel = channel
                channel_type = type(channel).__name__
                print(f"✅ FOUND SUPPORT CHANNEL: {channel.name} (ID: {channel.id})")
                break
        
        if not support_channel:
            print(f"❌ Could not find support channel with ID {SUPPORT_CHANNEL_ID}")

@client.event
async def on_thread_update(before, after):
    """Called when a thread is updated (tags changed, etc.)"""
    if not hasattr(after, 'parent_id') or after.parent_id != SUPPORT_CHANNEL_ID:
        return
    
    # Check if thread was just marked as resolved (wasn't resolved before, but is now)
    was_resolved_before = hasattr(before, "applied_tags") and is_thread_resolved(before.applied_tags)
    is_resolved_now = hasattr(after, "applied_tags") and is_thread_resolved(after.applied_tags)
    
    if is_resolved_now and not was_resolved_before:
        thread_id = after.id
        thread_title = after.name
        
        print(f"Thread marked as resolved: {thread_title} (ID: {thread_id})")
        
        # Get all current tags for the issue type
        issue_type = "Unknown"
        if hasattr(after, "applied_tags"):
            issue_type = get_issue_type_from_tags(after.applied_tags)
        
        # Get resolution time
        resolved_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        # Get thread URL
        thread_link = ""
        if hasattr(after, "guild") and after.guild:
            thread_link = f"https://discord.com/channels/{after.guild.id}/{thread_id}"
        
        # Send update to the webhook
        try:
            data = {
                'thread_id': str(thread_id),
                'title': thread_title,
                'type': issue_type,
                'resolved_time': resolved_time,
                'thread_link': thread_link,
                'event_type': 'resolution'
            }
            
            response = requests.post(WEBHOOK_URL, json=data)
            
            if response.status_code == 200:
                print(f"✅ Resolution update sent successfully for thread ID: {thread_id}")
                
                # Add a checkmark reaction to the last message if possible
                try:
                    async for message in after.history(limit=1):
                        await message.add_reaction("✅")
                        break
                except Exception as e:
                    print(f"Error adding reaction: {str(e)}")
            else:
                print(f"❌ Failed to send resolution update: {response.status_code}")
        except Exception as e:
            print(f"❌ Error sending resolution update: {str(e)}")

@client.event
async def on_message(message):
    """Process messages in support threads"""
    # Skip bot messages
    if message.author.bot:
        return
    
    # Check if this is a thread in our support channel
    channel = message.channel
    thread_parent_id = getattr(channel, 'parent_id', None)
    
    # If not in a support thread, skip
    if thread_parent_id != SUPPORT_CHANNEL_ID:
        return
    
    thread_id = channel.id
    thread_title = channel.name
    
    print(f"Message received in thread: {thread_title} (ID: {thread_id})")
    
    # Get the first message of the thread to identify the creator
    thread_starter = None
    try:
        async for first_message in channel.history(limit=1, oldest_first=True):
            thread_starter = first_message.author
            break
    except Exception as e:
        print(f"Error getting thread starter: {str(e)}")
    
    # Prepare the message data
    now = datetime.now(timezone.utc)
    message_data = {
        'thread_id': str(thread_id),
        'title': thread_title,
        'content': message.content,
        'author': str(message.author),
        'author_id': str(message.author.id),
        'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
        'thread_link': f"https://discord.com/channels/{message.guild.id}/{thread_id}"
    }
    
    # Check if this is the thread starter or a response
    is_thread_starter = thread_starter and message.author.id == thread_starter.id
    
    # Get issue type from thread tags
    if hasattr(channel, "applied_tags"):
        message_data['type'] = get_issue_type_from_tags(channel.applied_tags)
    
    # Set event type based on whether this is the starter or a response
    message_data['event_type'] = 'thread_created' if is_thread_starter else 'thread_response'
    event_type = "new thread" if is_thread_starter else "response"
    
    # Send to webhook
    try:
        response = requests.post(WEBHOOK_URL, json=message_data)
        
        if response.status_code == 200:
            # Only add the checkmark reaction to new thread creation messages
            if is_thread_starter:
                await message.add_reaction("✅")
            print(f"✅ {event_type.capitalize()} processed for thread ID: {thread_id}")
        else:
            # For errors, still show the X reaction to indicate failure
            await message.add_reaction("❌")
            print(f"❌ Failed to process {event_type}: {response.status_code}")
    except Exception as e:
        print(f"❌ Error processing {event_type}: {str(e)}")
        await message.add_reaction("❌")

# Run the bot
if __name__ == "__main__":
    try:
        print("Starting bot...")
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