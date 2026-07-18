import os
import discord
from discord.ext import commands

TOKEN = os.environ.get("TOKEN", "").strip()
if not TOKEN:
    raise RuntimeError("Missing TOKEN environment variable")

bot = commands.Bot(command_prefix="!")

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