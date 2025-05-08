import os
import discord
from discord import app_commands
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("AIzaSyCx0n22xstncD6uR5sD-wyjyj_9-uO63ws")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro-latest')

# Discord bot setup
DISCORD_TOKEN = os.getenv("MTM2OTgyMzEwODA4MDYwMzE5Nw.GtdoKB.dnOu6j40omSaUrfWQYyYR8hfAzrssd1vQg-js8")
intents = discord.Intents.default()
intents.message_content = True  # Required for reading messages
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Channel ID where the bot will respond (optional, set to None to respond everywhere)
TARGET_CHANNEL_ID = None  # Replace with your channel ID or keep as None

@client.event
async def on_ready():
    print(f"{client.user} is ready!")
    # Sync slash commands
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@client.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    # Check if bot is mentioned or message is in target channel
    if client.user in message.mentions or (TARGET_CHANNEL_ID and message.channel.id == TARGET_CHANNEL_ID):
        # Indicate typing
        async with message.channel.typing():
            try:
                # Clean message content (remove bot mention)
                user_message = message.content.replace(f"<@!{client.user.id}>", "").strip()

                # Generate response with Gemini
                response = model.generate_content(
                    user_message,
                    generation_config={
                        "max_output_tokens": 1900,  # Discord's limit is 2000 chars
                        "temperature": 0.7
                    }
                )

                # Handle long responses
                reply = response.text
                if len(reply) > 2000:
                    reply_chunks = [reply[i:i+2000] for i in range(0, len(reply), 2000)]
                    for chunk in reply_chunks:
                        await message.reply(chunk)
                else:
                    await message.reply(reply)

            except Exception as e:
                await message.reply(f"Error: {str(e)}")
                print(f"Error: {str(e)}")

@app_commands.command(name="ping", description="Check if the bot is responsive")
async def ping(interaction: discord.Interaction):
    latency = round(client.latency * 1000)
    await interaction.response.send_message(f"Pong! Latency: {latency}ms")

@app_commands.command(name="help", description="Display available commands")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Bot Commands",
        description="List of available commands",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="/ping", value="Check bot's latency", inline=False)
    embed.add_field(name="/help", value="Show this help message", inline=False)
    embed.add_field(name="/info", value="Display bot information", inline=False)
    embed.add_field(name="/clear [amount]", value="Clear specified number of messages (default 5, max 100)", inline=False)
    embed.add_field(name="Mention or Channel", value="Mention the bot or message in the target channel for a response", inline=False)
    embed.set_footer(text=f"Requested by {interaction.user.name}")
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="info", description="Show bot information")
async def info(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Bot Information",
        description="Details about the bot",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Bot Name", value=client.user.name, inline=True)
    embed.add_field(name="Created At", value=client.user.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.add_field(name="Powered By", value="Gemini API & discord.py", inline=True)
    embed.add_field(name="Target Channel", value="Any" if not TARGET_CHANNEL_ID else f"<#{TARGET_CHANNEL_ID}>", inline=True)
    embed.set_footer(text=f"Requested by {interaction.user.name}")
    await interaction.response.send_message(embed=embed)

@app_commands.command(name="clear", description="Clear a specified number of messages (default 5, max 100)")
@app_commands.describe(amount="Number of messages to clear (1-100)")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int = 5):
    if amount < 1:
        await interaction.response.send_message("Please specify a positive number of messages to clear.", ephemeral=True)
        return
    if amount > 100:
        await interaction.response.send_message("Cannot clear more than 100 messages at once.", ephemeral=True)
        return
    await interaction.response.defer()  # Defer response since purge can take time
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"Cleared {len(deleted)} message(s).", delete_after=5)

# Error handling for clear command
@clear.error
async def clear_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You need the 'Manage Messages' permission to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Error: {str(error)}", ephemeral=True)
        print(f"Clear command error: {str(error)}")

# General error handling for slash commands
@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    await interaction.response.send_message(f"Error: {str(error)}", ephemeral=True)
    print(f"Command error: {str(error)}")

# Run the bot
if __name__ == "__main__":
    client.run(DISCORD_TOKEN)