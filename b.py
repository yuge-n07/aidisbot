import sys
import os
import re
import json
import time
import random
import logging

# --- discord.py 1.7.3 (no Intents) ---
try:
    import discord
    from discord.ext import commands
    print(f"✅ discord version: {discord.__version__}")
except ImportError:
    print("❌ discord not installed. Run: pip install discord.py==1.7.3")
    sys.exit(1)

# --- Groq ---
try:
    from groq import AsyncGroq
except ImportError:
    print("❌ groq not installed. Run: pip install groq")
    sys.exit(1)

# --- Environment variables ---
def get_token():
    token = os.environ.get("TOKEN")
    if token:
        return token.strip()
    print("❌ TOKEN environment variable not set.")
    sys.exit(1)

def get_groq_keys():
    keys_str = os.environ.get("GROQ_KEYS")
    if keys_str:
        try:
            keys = json.loads(keys_str)
            if isinstance(keys, list) and keys:
                return keys
        except:
            pass
        if ',' in keys_str:
            keys = [k.strip() for k in keys_str.split(',') if k.strip()]
            if keys:
                return keys
        return [keys_str.strip()]
    print("❌ GROQ_KEYS environment variable not set.")
    print("Set as comma-separated or JSON array.")
    sys.exit(1)

TOKEN = get_token()
GROQ_KEYS = get_groq_keys()
print(f"Token length: {len(TOKEN)}")
print(f"Loaded {len(GROQ_KEYS)} Groq keys.")

ALLOWED_CHANNELS_FILE = "allowed_channels.json"

# --- Logging ---
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# --- Bot setup (NO Intents, NO self_bot) ---
bot = commands.Bot(command_prefix="!")

# --- Key rotation ---
current_key_index = 0

def get_next_groq_client():
    global current_key_index
    key = GROQ_KEYS[current_key_index]
    current_key_index = (current_key_index + 1) % len(GROQ_KEYS)
    return AsyncGroq(api_key=key), key

# --- Persona prompt ---
SYSTEM_PROMPT = (
    "You are a friendly, casual Discord chatbot with a chill personality. "
    "Keep your responses short, engaging, and occasionally humorous. "
    "Use informal language and emojis when fitting. "
    "Never break character or mention that you're an AI."
)

# --- Globals ---
OWNER_ID = None
allowed_channels = {}
CHAT_COOLDOWN = 60
CHAT_CHANCE = 0.20

def load_allowed_channels():
    global allowed_channels
    if os.path.exists(ALLOWED_CHANNELS_FILE):
        try:
            with open(ALLOWED_CHANNELS_FILE, "r") as f:
                data = json.load(f)
                allowed_channels = {int(k): v for k, v in data.items()}
                logger.info(f"Loaded allowed channels: {allowed_channels}")
        except Exception as e:
            logger.error(f"Failed to load allowed channels: {e}")
            allowed_channels = {}
    else:
        allowed_channels = {}

def save_allowed_channels():
    try:
        with open(ALLOWED_CHANNELS_FILE, "w") as f:
            json.dump(allowed_channels, f)
        logger.info("Allowed channels saved.")
    except Exception as e:
        logger.error(f"Failed to save allowed channels: {e}")

load_allowed_channels()

# --- Help text ---
HELP_TEXT = f"""
**🤖 AI Chat Bot – Owner Only**

**Commands** (mention me + command):
• `ping` – Pong!
• `help` – show this message.

**AI Chat:**
• Enable a channel via DM: `enable #channel` or `enable channel-id`.
• Disable: `disable #channel` or `disable channel-id`.
• Cooldown: {CHAT_COOLDOWN}s, chance: {int(CHAT_CHANCE*100)}%.
• Auto‑rotates through {len(GROQ_KEYS)} API keys.
"""

# --- AI response ---
async def get_ai_response(message_text):
    attempts = 0
    while attempts < len(GROQ_KEYS):
        client, key = get_next_groq_client()
        try:
            completion = await client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": message_text},
                ],
                temperature=0.8,
                max_tokens=100,
                top_p=0.9,
            )
            reply = completion.choices[0].message.content.strip()
            logger.info(f"AI reply using key {key[:8]}...")
            return reply
        except Exception as e:
            logger.warning(f"Key {key[:8]}... failed: {e}, trying next key.")
            attempts += 1
            if attempts >= len(GROQ_KEYS):
                logger.error("All Groq keys failed.")
                return None
    return None

# --- Bot events ---
@bot.event
async def on_ready():
    global OWNER_ID
    OWNER_ID = bot.user.id
    logger.info(f"Logged in as {bot.user} (ID: {OWNER_ID})")
    print(f"✅ Logged in as {bot.user} (ID: {OWNER_ID})")
    print(f"AI Chat enabled. {len(GROQ_KEYS)} API keys in rotation.")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # ---- DM from owner ----
    if isinstance(message.channel, discord.DMChannel) and message.author.id == OWNER_ID:
        content = message.content.strip().lower()
        if content.startswith("enable"):
            matches = re.findall(r"<#(\d+)>", content)
            if not matches:
                numbers = re.findall(r"\b(\d+)\b", content)
                if numbers:
                    channel_id = int(numbers[0])
                else:
                    await message.channel.send("❌ Please provide a channel mention or ID.")
                    return
            else:
                channel_id = int(matches[0])
            channel = bot.get_channel(channel_id)
            if channel is None:
                await message.channel.send("❌ Channel not found.")
                return
            allowed_channels[channel_id] = 0
            save_allowed_channels()
            await message.channel.send(f"✅ Enabled AI chat in #{channel.name} (ID: {channel_id})")
            logger.info(f"Enabled channel {channel_id}")
            return
        elif content.startswith("disable"):
            matches = re.findall(r"<#(\d+)>", content)
            if not matches:
                numbers = re.findall(r"\b(\d+)\b", content)
                if numbers:
                    channel_id = int(numbers[0])
                else:
                    await message.channel.send("❌ Please provide a channel mention or ID.")
                    return
            else:
                channel_id = int(matches[0])
            if channel_id in allowed_channels:
                del allowed_channels[channel_id]
                save_allowed_channels()
                await message.channel.send(f"✅ Disabled AI chat in channel ID: {channel_id}")
                logger.info(f"Disabled channel {channel_id}")
            else:
                await message.channel.send("❌ That channel is not enabled.")
            return
        else:
            return

    # ---- Guild messages ----
    if not isinstance(message.channel, discord.DMChannel):
        if message.channel.id in allowed_channels and bot.user not in message.mentions:
            now = time.time()
            last_reply = allowed_channels.get(message.channel.id, 0)
            if now - last_reply >= CHAT_COOLDOWN:
                if random.random() < CHAT_CHANCE:
                    reply = await get_ai_response(message.content)
                    if reply:
                        allowed_channels[message.channel.id] = now
                        save_allowed_channels()
                        await message.channel.send(reply)
                        logger.info(f"AI replied in #{message.channel.name}")
                    else:
                        logger.warning("AI returned no reply.")

        if bot.user in message.mentions and message.author.id == OWNER_ID:
            content = message.content.strip()
            if re.search(r"help$", content, re.IGNORECASE):
                await message.channel.send(HELP_TEXT)
                return
            if re.search(r"^ping$", content, re.IGNORECASE):
                await message.channel.send("Pong! 🏓")
                return

# --- Run ---
if __name__ == "__main__":
    bot.run(TOKEN.strip())
