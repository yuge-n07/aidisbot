import os
import asyncio
import discord
from discord.ext import commands

# --- Token ---
TOKEN = os.environ.get("TOKEN", "").strip()
if not TOKEN:
    raise RuntimeError("Missing TOKEN environment variable")

# --- Fix for Python 3.14 event loop issue ---
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# --- Bot setup (self_bot=True) ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, self_bot=True)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if bot.user in message.mentions:
        await message.channel.send("Pong! 🏓")

bot.run(TOKEN)
