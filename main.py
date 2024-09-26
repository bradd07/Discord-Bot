import asyncio
import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
from cmds.TwitchCmds import TwitchCmds

"""
Main file for the bot. Loads commands and starts the bot
Author: bradd07
"""

# instantiate bot
client = commands.AutoShardedBot(command_prefix='/', intents=discord.Intents.all())


async def load_cogs():
    for filename in os.listdir("./cmds"):
        if filename.endswith(".py"):
            await client.load_extension(f"cmds.{filename[:-3]}")


@client.event
async def on_ready():
    # set status
    await client.change_presence(activity=discord.Game(name="@brad.dev"))
    await client.tree.sync()
    # Start checking Twitch streams
    twitch_cmds = TwitchCmds(client)
    await client.loop.create_task(twitch_cmds.check_streams())


async def main():
    # load environment variables
    load_dotenv()

    try:
        # await load_cogs()
        await client.load_extension("cmds.RegCmds")
        await client.load_extension("cmds.TwitchCmds")
        await client.load_extension("cmds.PointsCmds")
        bot_token = os.getenv("BOT_TOKEN")
        await client.start(f"{bot_token}")
    except Exception as e:
        print(f"Bot has shut down due to Exception: {e}\n")


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

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Brad's bot has shut down gracefully by the user..\n")
    except Exception as e:
        print(f"Unhandled Exception: {e}\n")
    finally:
        loop.close()
