import discord
import os
import asyncio
import aiohttp
import logging
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from typing import Optional

try:
    import pytz
    IST = pytz.timezone('Asia/Kolkata')
except ImportError:
    print("WARNING: pytz not installed. Using UTC offset for IST.")
    IST = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def get_env_var(name: str, required: bool = True, default: str = "") -> str:
    """Get environment variable with validation"""
    value = os.getenv(name, default)
    if required and not value:
        logger.error(f"Missing required environment variable: {name}")
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def parse_int_env(name: str, default: int = 0) -> int:
    """Parse integer environment variable safely"""
    value = os.getenv(name, "")
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        logger.error(f"Invalid integer value for {name}: {value}")
        return default


def parse_int_list_env(name: str) -> list:
    """Parse comma-separated integer list from environment variable"""
    value = os.getenv(name, "")
    if not value:
        return []

    result = []
    for item in value.split(","):
        item = item.strip()
        if item:
            try:
                result.append(int(item))
            except ValueError:
                logger.warning(f"Skipping invalid channel ID in {name}: {item}")
    return result


# Configuration with validation
try:
    DISCORD_TOKEN = get_env_var("DISCORD_TOKEN")
    SUPPORT_CHANNEL_ID = parse_int_env("SUPPORT_CHANNEL_ID")
    WEBHOOK_URL = get_env_var("WEBHOOK_URL")
    ALERT_CHANNEL_IDS = parse_int_list_env("ALERT_CHANNEL_IDS")
except ValueError as e:
    logger.critical(f"Configuration error: {e}")
    exit(1)

# Validate critical config
if SUPPORT_CHANNEL_ID == 0:
    logger.critical("SUPPORT_CHANNEL_ID is not set or invalid")
    exit(1)

if not WEBHOOK_URL.startswith("http"):
    logger.critical("WEBHOOK_URL must be a valid URL")
    exit(1)

# Business hours configuration (IST)
BUSINESS_HOURS_START = 9   # 9 AM
BUSINESS_HOURS_END = 18    # 6 PM
BUSINESS_DAYS = [0, 1, 2, 3, 4]  # Monday to Friday (0=Monday, 6=Sunday)

# SLA configuration
SLA_TIMEOUT_MINUTES = 60  # 1 hour

# Tags that indicate a thread is resolved
RESOLVED_TAGS = ["resolved"]

# Consulting team Discord user IDs (for is_engineering detection)
CONSULTING_USER_IDS = [
    "365127154847186945",   # Siddhant
    "535859343665397791",   # Prateeksha
    "441276013578813441",
    "1394202624999559230"
]

# Print configuration for debugging
logger.info(f"Support Channel ID: {SUPPORT_CHANNEL_ID}")
logger.info(f"Webhook URL: {WEBHOOK_URL[:50]}...")
logger.info(f"Alert Channel IDs: {ALERT_CHANNEL_IDS}")

# Set up Discord client with necessary intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
client = discord.Client(intents=intents)

# Track pending SLA alerts: {thread_id: asyncio.Task}
pending_sla_alerts = {}

# Track threads that have received first response
responded_threads = set()

# HTTP session for webhook calls
http_session: Optional[aiohttp.ClientSession] = None


async def get_http_session() -> aiohttp.ClientSession:
    """Get or create HTTP session"""
    global http_session
    if http_session is None or http_session.closed:
        timeout = aiohttp.ClientTimeout(total=30)
        http_session = aiohttp.ClientSession(timeout=timeout)
    return http_session


async def close_http_session():
    """Close HTTP session"""
    global http_session
    if http_session and not http_session.closed:
        await http_session.close()


def is_business_hours() -> bool:
    """Check if current time is within business hours (9 AM - 6 PM IST, Mon-Fri)"""
    try:
        if IST:
            now_ist = datetime.now(IST)
        else:
            # Fallback: UTC+5:30
            now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)

        return (
            now_ist.weekday() in BUSINESS_DAYS and
            BUSINESS_HOURS_START <= now_ist.hour < BUSINESS_HOURS_END
        )
    except Exception as e:
        logger.error(f"Error checking business hours: {e}")
        return False  # Default to outside business hours on error


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format (e.g., '2d 4h 15m' or '45m 30s')"""
    try:
        if seconds < 0:
            return "0s"

        seconds = int(seconds)
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0 or days > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or hours > 0 or days > 0:
            parts.append(f"{minutes}m")
        if not parts or (days == 0 and hours == 0):
            parts.append(f"{secs}s")

        return " ".join(parts)
    except Exception as e:
        logger.error(f"Error formatting duration: {e}")
        return "Unknown"


def get_tags_string(tags) -> str:
    """Extract all tag names and join with comma"""
    try:
        if not tags:
            return ""
        return ", ".join(str(tag.name) for tag in tags if hasattr(tag, 'name'))
    except Exception as e:
        logger.error(f"Error getting tags string: {e}")
        return ""


def is_thread_resolved(tags) -> bool:
    """Check if any tag indicates resolved"""
    try:
        if not tags:
            return False
        return any(
            hasattr(tag, 'name') and tag.name.lower() in RESOLVED_TAGS
            for tag in tags
        )
    except Exception as e:
        logger.error(f"Error checking resolved status: {e}")
        return False


def is_engineering_issue(message_content: str) -> bool:
    """Check if ticket is engineering (True) or consulting (False)"""
    try:
        if not message_content:
            return True
        return not any(user_id in message_content for user_id in CONSULTING_USER_IDS)
    except Exception as e:
        logger.error(f"Error checking engineering status: {e}")
        return True


def get_thread_link(guild_id: int, thread_id: int) -> str:
    """Generate Discord thread URL"""
    return f"https://discord.com/channels/{guild_id}/{thread_id}"


async def send_to_webhook(data: dict, max_retries: int = 3) -> bool:
    """Send data to Google Apps Script webhook with retry logic"""
    for attempt in range(max_retries):
        try:
            session = await get_http_session()
            async with session.post(WEBHOOK_URL, json=data) as response:
                response_text = await response.text()

                if response.status == 200:
                    logger.info(f"Webhook success: {data.get('event_type')} for thread {data.get('thread_id')}")
                    return True
                else:
                    logger.warning(f"Webhook failed (attempt {attempt + 1}/{max_retries}): status={response.status}, response={response_text[:200]}")

        except asyncio.TimeoutError:
            logger.warning(f"Webhook timeout (attempt {attempt + 1}/{max_retries})")
        except aiohttp.ClientError as e:
            logger.warning(f"Webhook client error (attempt {attempt + 1}/{max_retries}): {e}")
        except Exception as e:
            logger.error(f"Webhook unexpected error (attempt {attempt + 1}/{max_retries}): {e}")

        # Wait before retry (exponential backoff)
        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)

    logger.error(f"Webhook failed after {max_retries} attempts for {data.get('event_type')}")
    return False


async def send_sla_alert(thread_id: int, title: str, raised_by: str, is_engineering: bool, guild_id: int):
    """Send SLA alert to configured alert channels"""
    try:
        # Check if thread still exists and hasn't been responded to
        if thread_id in responded_threads:
            logger.info(f"Thread {thread_id} was responded to, skipping SLA alert")
            return

        thread_link = get_thread_link(guild_id, thread_id)
        issue_type = "Engineering Issue" if is_engineering else "Non-Engineering Issue"

        alert_message = (
            f"⚠️ **SLA ALERT: Ticket Awaiting Response**\n\n"
            f"📋 **Title:** {title}\n"
            f"👤 **Raised by:** {raised_by}\n"
            f"⏰ **Waiting:** 1 hour\n"
            f"🏷️ **Type:** {issue_type}\n"
            f"🔗 **Link:** [Click to view]({thread_link})\n\n"
            f"Please respond to this ticket as soon as possible."
        )

        if not ALERT_CHANNEL_IDS:
            logger.warning("No alert channels configured, skipping SLA alert")
            return

        for channel_id in ALERT_CHANNEL_IDS:
            try:
                channel = client.get_channel(channel_id)
                if channel:
                    await channel.send(alert_message)
                    logger.info(f"SLA alert sent to channel {channel_id}")
                else:
                    # Try fetching the channel if not in cache
                    try:
                        channel = await client.fetch_channel(channel_id)
                        await channel.send(alert_message)
                        logger.info(f"SLA alert sent to channel {channel_id} (fetched)")
                    except discord.NotFound:
                        logger.error(f"Alert channel {channel_id} not found")
                    except discord.Forbidden:
                        logger.error(f"No permission to send to alert channel {channel_id}")
            except discord.HTTPException as e:
                logger.error(f"Discord error sending SLA alert to {channel_id}: {e}")
            except Exception as e:
                logger.error(f"Error sending SLA alert to {channel_id}: {e}")

    except Exception as e:
        logger.error(f"Unexpected error in send_sla_alert: {e}")


async def schedule_sla_alert(thread_id: int, title: str, raised_by: str, is_engineering: bool, guild_id: int):
    """Schedule an SLA alert after timeout period"""
    try:
        # Cancel any existing alert for this thread
        cancel_sla_alert(thread_id)

        async def alert_task():
            try:
                await asyncio.sleep(SLA_TIMEOUT_MINUTES * 60)
                # Check if thread still hasn't been responded to
                if thread_id not in responded_threads:
                    await send_sla_alert(thread_id, title, raised_by, is_engineering, guild_id)
            except asyncio.CancelledError:
                pass  # Task was cancelled (response received)
            except Exception as e:
                logger.error(f"Error in SLA alert task for thread {thread_id}: {e}")
            finally:
                # Clean up from pending alerts
                pending_sla_alerts.pop(thread_id, None)

        task = asyncio.create_task(alert_task())
        pending_sla_alerts[thread_id] = task
        logger.info(f"SLA timer started for thread {thread_id} ({SLA_TIMEOUT_MINUTES} min)")

    except Exception as e:
        logger.error(f"Error scheduling SLA alert for thread {thread_id}: {e}")


def cancel_sla_alert(thread_id: int):
    """Cancel pending SLA alert for a thread"""
    try:
        if thread_id in pending_sla_alerts:
            pending_sla_alerts[thread_id].cancel()
            del pending_sla_alerts[thread_id]
            logger.info(f"SLA timer cancelled for thread {thread_id}")
    except Exception as e:
        logger.error(f"Error cancelling SLA alert for thread {thread_id}: {e}")


@client.event
async def on_ready():
    """Called when bot is connected and ready"""
    logger.info(f"Bot is ready! Logged in as {client.user}")

    for guild in client.guilds:
        logger.info(f"Connected to guild: {guild.name}")

        # Verify support channel exists
        try:
            support_channel = guild.get_channel(SUPPORT_CHANNEL_ID)
            if support_channel:
                logger.info(f"Found support channel: {support_channel.name}")
            else:
                # Try fetching it
                try:
                    support_channel = await client.fetch_channel(SUPPORT_CHANNEL_ID)
                    logger.info(f"Found support channel (fetched): {support_channel.name}")
                except discord.NotFound:
                    logger.warning(f"Support channel {SUPPORT_CHANNEL_ID} not found in {guild.name}")
                except discord.Forbidden:
                    logger.warning(f"No permission to access support channel {SUPPORT_CHANNEL_ID}")
        except Exception as e:
            logger.error(f"Error checking support channel: {e}")


@client.event
async def on_disconnect():
    """Called when bot disconnects"""
    logger.warning("Bot disconnected from Discord")


@client.event
async def on_resumed():
    """Called when bot resumes after a disconnect"""
    logger.info("Bot reconnected to Discord")


@client.event
async def on_error(event, *args, **kwargs):
    """Global error handler for events"""
    logger.exception(f"Error in event {event}")


@client.event
async def on_thread_create(thread: discord.Thread):
    """Handle new thread creation in the support forum"""
    try:
        if not thread.parent_id or thread.parent_id != SUPPORT_CHANNEL_ID:
            return

        logger.info(f"New thread created: {thread.name} (ID: {thread.id})")

        # Wait a moment for the first message to be available
        await asyncio.sleep(1)

        # Get the first message (thread starter message)
        first_message = None
        thread_starter = None
        message_content = ""

        try:
            async for msg in thread.history(limit=1, oldest_first=True):
                first_message = msg
                thread_starter = msg.author
                message_content = msg.content or ""
                break
        except discord.Forbidden:
            logger.error(f"No permission to read history in thread {thread.id}")
        except discord.HTTPException as e:
            logger.error(f"Discord error getting first message: {e}")
        except Exception as e:
            logger.error(f"Error getting first message: {e}")

        now = datetime.now(timezone.utc)
        thread_id = str(thread.id)

        # Determine business hours and engineering status
        outside_business = not is_business_hours()
        is_eng = is_engineering_issue(message_content)

        # Get tags
        tags_str = get_tags_string(getattr(thread, "applied_tags", None))

        # Get guild ID safely
        guild_id = thread.guild.id if thread.guild else 0

        # Prepare data for webhook
        data = {
            'event_type': 'thread_created',
            'thread_id': thread_id,
            'title': thread.name or "Untitled",
            'type': tags_str,
            'raised_by': str(thread_starter) if thread_starter else "Unknown",
            'date_created': now.strftime("%Y-%m-%d %H:%M:%S"),
            'thread_link': get_thread_link(guild_id, thread.id) if guild_id else "",
            'is_engineering': is_eng,
            'outside_business_hours': outside_business
        }

        # Send to webhook
        success = await send_to_webhook(data)

        # Add reaction to first message
        if first_message:
            try:
                await first_message.add_reaction("✅" if success else "❌")
            except discord.Forbidden:
                logger.warning(f"No permission to add reaction in thread {thread.id}")
            except discord.HTTPException as e:
                logger.error(f"Discord error adding reaction: {e}")
            except Exception as e:
                logger.error(f"Error adding reaction: {e}")

        # Schedule SLA alert
        raised_by = str(thread_starter) if thread_starter else "Unknown"
        await schedule_sla_alert(thread.id, thread.name, raised_by, is_eng, guild_id)

    except Exception as e:
        logger.exception(f"Unexpected error in on_thread_create: {e}")


@client.event
async def on_message(message: discord.Message):
    """Handle messages in support threads (for tracking first response)"""
    try:
        # Skip bot messages
        if message.author.bot:
            return

        # Check if this is in a support thread
        channel = message.channel
        if not hasattr(channel, 'parent_id') or channel.parent_id != SUPPORT_CHANNEL_ID:
            return

        thread_id = channel.id

        # Check if we already tracked first response for this thread (fast path)
        if thread_id in responded_threads:
            return

        # Get thread starter
        thread_starter_id = None
        try:
            async for msg in channel.history(limit=1, oldest_first=True):
                thread_starter_id = msg.author.id
                break
        except discord.Forbidden:
            logger.error(f"No permission to read history in thread {thread_id}")
            return
        except discord.HTTPException as e:
            logger.error(f"Discord error getting thread starter: {e}")
            return
        except Exception as e:
            logger.error(f"Error getting thread starter: {e}")
            return

        # If this is the thread starter, ignore (not a response)
        if thread_starter_id and message.author.id == thread_starter_id:
            return

        # This is the first response!
        responded_threads.add(thread_id)
        cancel_sla_alert(thread_id)

        now = datetime.now(timezone.utc)

        # Calculate time to first response
        thread_created = getattr(channel, 'created_at', None)
        if thread_created:
            time_diff = (now - thread_created).total_seconds()
            time_to_response = format_duration(time_diff)
        else:
            time_to_response = "Unknown"

        logger.info(f"First response in thread {channel.name} by {message.author} ({time_to_response})")

        # Send to webhook
        data = {
            'event_type': 'first_response',
            'thread_id': str(thread_id),
            'first_responded_by': str(message.author),
            'time_to_first_response': time_to_response,
            'response_timestamp': now.strftime("%Y-%m-%d %H:%M:%S")
        }

        await send_to_webhook(data)

    except Exception as e:
        logger.exception(f"Unexpected error in on_message: {e}")


@client.event
async def on_thread_update(before: discord.Thread, after: discord.Thread):
    """Handle thread updates (tags, title, resolved status)"""
    try:
        if not after.parent_id or after.parent_id != SUPPORT_CHANNEL_ID:
            return

        thread_id = str(after.id)
        now = datetime.now(timezone.utc)

        # Check for title change
        if before.name != after.name:
            logger.info(f"Title changed: '{before.name}' → '{after.name}'")
            await send_to_webhook({
                'event_type': 'title_changed',
                'thread_id': thread_id,
                'title': after.name or "Untitled"
            })

        # Get tag states safely
        before_tags = getattr(before, 'applied_tags', None) or []
        after_tags = getattr(after, 'applied_tags', None) or []

        was_resolved = is_thread_resolved(before_tags)
        is_resolved = is_thread_resolved(after_tags)

        before_tags_str = get_tags_string(before_tags)
        after_tags_str = get_tags_string(after_tags)

        # Check for tag changes
        if before_tags_str != after_tags_str:
            logger.info(f"Tags changed: '{before_tags_str}' → '{after_tags_str}'")
            await send_to_webhook({
                'event_type': 'tags_changed',
                'thread_id': thread_id,
                'type': after_tags_str
            })

        # Check for resolution
        if is_resolved and not was_resolved:
            logger.info(f"Thread resolved: {after.name}")

            # Calculate time to resolution
            thread_created = getattr(after, 'created_at', None)
            if thread_created:
                time_diff = (now - thread_created).total_seconds()
                time_to_resolution = format_duration(time_diff)
            else:
                time_to_resolution = "Unknown"

            # Get thread starter for the warning message
            thread_starter = None
            try:
                async for msg in after.history(limit=1, oldest_first=True):
                    thread_starter = msg.author
                    break
            except Exception as e:
                logger.error(f"Error getting thread starter for resolution message: {e}")

            # Send warning message in the thread
            mention = f"<@{thread_starter.id}>" if thread_starter else ""
            warning_message = (
                f"🔴 {mention} This thread has been marked as **RESOLVED**.\n\n"
                f"We will no longer monitor this thread for new messages. "
                f"If you have a new issue or follow-up question, please create a new thread.\n\n"
                f"Thank you for reaching out to Dalgo Support!"
            )

            warning_msg = None
            try:
                warning_msg = await after.send(warning_message)
                logger.info(f"Sent resolved warning message (ID: {warning_msg.id})")
            except discord.Forbidden:
                logger.error(f"No permission to send message in thread {thread_id}")
            except discord.HTTPException as e:
                logger.error(f"Discord error sending warning message: {e}")
            except Exception as e:
                logger.error(f"Error sending warning message: {e}")

            # Send to webhook
            await send_to_webhook({
                'event_type': 'resolved',
                'thread_id': thread_id,
                'resolution_date': now.strftime("%Y-%m-%d %H:%M:%S"),
                'time_to_resolution': time_to_resolution,
                'warning_message_id': str(warning_msg.id) if warning_msg else "",
                'type': after_tags_str
            })

        # Check for reopen
        elif was_resolved and not is_resolved:
            logger.info(f"Thread reopened: {after.name}")

            # Try to edit the last warning message
            try:
                async for msg in after.history(limit=20):
                    if msg.author == client.user and "RESOLVED" in msg.content:
                        reopened_message = (
                            "🟢 **UPDATE:** This thread has been **REOPENED**!\n\n"
                            "We're continuing the conversation here. "
                            "Our support team will follow up shortly."
                        )
                        await msg.edit(content=reopened_message)
                        logger.info(f"Edited warning message to reopened status")
                        break
            except discord.Forbidden:
                logger.error(f"No permission to edit message in thread {thread_id}")
            except discord.HTTPException as e:
                logger.error(f"Discord error editing warning message: {e}")
            except Exception as e:
                logger.error(f"Error editing warning message: {e}")

            # Send to webhook
            await send_to_webhook({
                'event_type': 'reopened',
                'thread_id': thread_id
            })

    except Exception as e:
        logger.exception(f"Unexpected error in on_thread_update: {e}")


async def cleanup():
    """Cleanup resources on shutdown"""
    logger.info("Cleaning up resources...")

    # Cancel all pending SLA alerts
    for thread_id, task in list(pending_sla_alerts.items()):
        task.cancel()
    pending_sla_alerts.clear()

    # Close HTTP session
    await close_http_session()

    logger.info("Cleanup complete")


# Run the bot
if __name__ == "__main__":
    try:
        logger.info("Starting Discord Support Bot...")
        logger.info(f"Business hours: {BUSINESS_HOURS_START}:00 - {BUSINESS_HOURS_END}:00 IST (Mon-Fri)")

        # Run with cleanup
        async def main():
            try:
                await client.start(DISCORD_TOKEN)
            finally:
                await cleanup()

        asyncio.run(main())

    except discord.errors.LoginFailure:
        logger.critical("Invalid Discord token! Check your .env file.")
        exit(1)
    except discord.errors.PrivilegedIntentsRequired:
        logger.critical("Message content intent is required but not enabled!")
        logger.critical("Please enable intents at: https://discord.com/developers/applications/")
        exit(1)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        exit(1)
