import discord
import os
from discord_slash import SlashCommand
from discord.ext import commands
from dotenv import load_dotenv
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


@client.event
async def on_command_error(ctx, error):
    # try to catch any potential errors when running a command
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have the permissions to do that!", hidden=True)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please enter all the required arguments!", hidden=True)
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("Member not found, Please mention a valid user!", hidden=True)
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("I don't have the permissions to do that!", hidden=True)
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("That doesn't seem to be a real command. Try again!", hidden=True)


load_dotenv()
bot_token = os.getenv("BOT_TOKEN")
slash.on_slash_command_error = on_command_error
client.run(f"{bot_token}")
