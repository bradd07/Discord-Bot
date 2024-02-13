import discord
from discord_slash import SlashCommand
from discord.ext import commands
from dotenv import load_dotenv
import os
from cmds.TwitchCmds import TwitchCmds

client = commands.Bot(command_prefix='/', intents=discord.Intents.all())
slash = SlashCommand(client, sync_commands=True)

# load cogs
client.load_extension("cmds.RegCmds")
client.load_extension("cmds.PointsCmds")
client.load_extension("cmds.OverwatchCmds")
client.load_extension("cmds.TwitchCmds")


@client.event
async def on_ready():
    # set status
    await client.change_presence(activity=discord.Game(name="@brad.dev"))
    # Start checking Twitch streams
    twitch_cmds = TwitchCmds(client)
    client.loop.create_task(twitch_cmds.check_streams())

load_dotenv()
bot_token = os.getenv("BOT_TOKEN")
client.run(f"{bot_token}")
