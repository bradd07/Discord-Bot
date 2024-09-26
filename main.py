import asyncio
import discord
import os
from discord.ext import commands
from discord.ext.commands import Context
from dotenv import load_dotenv
from cmds.TwitchCmds import TwitchCmds, timestamp

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

    # sync command tree
    synced = await client.tree.sync()
    print(f"{timestamp()} Synced {len(synced)} command(s)!")

    # start checking Twitch streams
    twitch_cmds = TwitchCmds(client)
    await client.loop.create_task(twitch_cmds.check_streams())


async def main():
    # load environment variables
    load_dotenv()

    try:
        await load_cogs()
        bot_token = os.getenv("BOT_TOKEN")
        print(f"{timestamp()} Starting up Brad's Bot...")
        await client.start(f"{bot_token}")
    except Exception as error:
        print(f"{timestamp()} Bot has shut down due to Exception: {error}\n")


@client.event
async def on_command_error(ctx: Context, error):
    # try to catch any potential errors when running a command
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have the permissions to do that!", ephemeral=True)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please enter all the required arguments!", ephemeral=True)
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("Member not found, Please mention a valid user!", ephemeral=True)
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("I don't have the permissions to do that!", ephemeral=True)
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("That doesn't seem to be a real command. Try again!", ephemeral=True)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print(f"{timestamp()} Brad's bot has shut down gracefully by the user..\n")
    except Exception as e:
        print(f"{timestamp()} Unhandled Exception: {e}\n")
    finally:
        loop.close()
