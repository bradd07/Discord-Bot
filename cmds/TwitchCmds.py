from datetime import datetime, timedelta
import discord
import requests
import asyncio
import json
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from dotenv import load_dotenv
import os
import pytz
from colorama import Back, Fore, Style

"""
Cog for twitch announcement commands.
Author: bradd07
"""


# generates a new twitch OAUTH token when requested
def get_oauth_token():
    # twitch API endpoint for OAuth token generation
    url = 'https://id.twitch.tv/oauth2/token'

    # twitch IDs
    client_id = os.getenv("TWITCH_CLIENT_ID")
    client_secret = os.getenv("TWITCH_SECRET")

    # generate payload
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }

    try:
        # making a POST request to the Twitch API
        response = requests.post(url, params=payload)
        data = response.json()

        # check if access token is present in response
        if 'access_token' in data:
            # yay
            return data['access_token']
        else:
            # nay
            print(f"{timestamp()} Error: {data.get('message', 'Failed to get access token')}")
            return None

    # catch errors
    except requests.RequestException as e:
        print(f"{timestamp()} Error: {e}")
        return None


# automatically updates the locally stored .env file with new values
def update_env_file(key, value):
    # load existing .env file
    dotenv_path = '.env'
    with open(dotenv_path, 'r') as file:
        lines = file.readlines()

    # write the new value
    with open(dotenv_path, 'w') as file:
        for line in lines:
            if line.startswith(key):
                file.write(f"{key}={value}\n")
            else:
                file.write(line)


# sends an announcement message to the specified channel with the collected stream data
async def send_announcement(channel, stream_data):
    # extract data
    stream_title = stream_data["title"]
    stream_url = f"https://www.twitch.tv/{stream_data['user_name']}"
    viewer_count = stream_data["viewer_count"]
    game_name = stream_data["game_name"]
    broadcaster_name = stream_data['user_name']

    # set up embed
    embed = discord.Embed(
        title=f"**{stream_title}**",
        url=stream_url,
        color=discord.Color.red()
    )
    embed.set_author(name=broadcaster_name)

    if broadcaster_name == 'xFlxZh':
        # set custom thumbnail for flazh...
        embed.set_image(
            url='https://media.discordapp.net/attachments/1049713626895896686/1245587352693379154/live'
                'now.png?ex=66cdf7de&is=66cca65e&hm=3b0c29d57726e493805c28cacd4e81c400e549650bf3ced52'
                '2068d2a0cabdc66&=&format=webp&quality=lossless&width=550&height=309'.replace
            ("{width}", "320").replace("{height}", "180"))
    else:
        # default to Twitch stream thumbnail
        embed.set_image(
            url=stream_data['thumbnail_url'].replace("{width}", "320").replace("{height}", "180"))

    embed.set_thumbnail(url='https://media.discordapp.net/attachments/1049713626895896686/124558727353'
                            '8605117/newlogo.png?ex=66cdf7cb&is=66cca64b&hm=3a39e66fa6fbdce183d99f9f561'
                            '6ff24a2d357421bb52911b286ad2e6e586ac1&=&format=webp&quality=lossless&widt'
                            'h=920&height=460')
    embed.add_field(name="Viewers", value=viewer_count, inline=False)
    embed.add_field(name="Game", value=game_name, inline=False)

    # get mst current time
    mst_timezone = pytz.timezone('America/Phoenix')
    mst_now = datetime.now(tz=mst_timezone)
    embed.set_footer(text="Twitch • " + mst_now.strftime("%m/%d/%Y %I:%M %p"),
                     icon_url="https://cdn-longterm.mee6.xyz/plugins/twitch/logo.png")

    # send the message
    await channel.send(
        f"Hey @everyone, {broadcaster_name} is now live on Twitch! Come and support the stream! Leave a comment and chat with them!",
        embed=embed)


def timestamp():
    return (Back.BLACK + Fore.GREEN + Style.BRIGHT +
            datetime.now(pytz.utc).astimezone(pytz.timezone('US/Arizona')).strftime("%H:%M:%S GMT/PST" +
                                                                                    Back.RESET + Fore.WHITE))


class TwitchCmds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # define twitch client id and access token from environment variables
        load_dotenv()
        self.twitch_client_id = os.getenv("TWITCH_CLIENT_ID")
        self.twitch_access_token = os.getenv("TWITCH_ACCESS_TOKEN")
        self.streams = {}
        self.settings = {}
        self.load_settings()  # load settings from json file

    # default /twitch command, does nothing without sub-parameter
    @commands.hybrid_group(name="twitch", description="Manage twitch integration settings")
    @commands.has_permissions(manage_guild=True)
    async def twitch(self, ctx: Context):
        return

    @twitch.command(name="add", description="Add a broadcaster to the list of streams")
    @app_commands.describe(name="Name of the broadcaster")
    @commands.has_permissions(manage_guild=True)
    async def add_broadcaster(self, ctx: Context, name: str):
        # get guild
        guild_id = str(ctx.guild.id)

        # check if we have a list for this guild yet
        if guild_id not in self.settings:
            self.settings[guild_id] = {}

        # set to lower to caps doesn't matter
        name = name.lower()

        # check if this streamer is already in the list
        if "names" in self.settings[guild_id] and name in self.settings[guild_id]["names"]:
            await ctx.send(f"> `{name}` is already in the list of broadcasters.")
        # else assume this streamer is not in the list yet
        else:
            self.settings[guild_id].setdefault("names", []).append(name)
            await ctx.send(f"> Added `{name}` to the list of broadcasters to check.")

        # save settings
        self.save_settings()

    @twitch.command(name="remove", description="Remove a broadcaster from the list")
    @app_commands.describe(name="Name of the broadcaster")
    @commands.has_permissions(manage_guild=True)
    async def remove_broadcaster(self, ctx: Context, name: str):
        # get guild
        guild_id = str(ctx.guild.id)

        # check if we have a list for this guild yet
        if guild_id not in self.settings:
            self.settings[guild_id] = {}

        # set to lower to caps doesn't matter
        name = name.lower()

        # check if this streamer is already in the list
        if "names" in self.settings[guild_id] and name in self.settings[guild_id]["names"]:
            self.settings[guild_id]["names"].remove(name)
            await ctx.send(f"> Removed `{name}` from the list of broadcasters.")
        # else assume this streamer is not in the list yet
        else:
            await ctx.send(f"> `{name}` is not in the list of broadcasters.")

        # save settings
        self.save_settings()

    @twitch.command(name="list", description="List all broadcasters")
    @commands.has_permissions(manage_guild=True)
    async def list_broadcasters_command(self, ctx: Context):
        # get guild
        guild_id = str(ctx.guild.id)

        # list broadcasters
        await self.list_broadcasters(ctx, guild_id)

    @twitch.command(name="setchannel", description="Designate the channel for announcements")
    @app_commands.describe(channel_id="ID of the channel to send announcements to")
    @commands.has_permissions(manage_guild=True)
    async def set_announcement_channel(self, ctx: Context, channel_id):
        # get guild
        guild_id = str(ctx.guild.id)

        # check if we have a list for this guild yet
        if guild_id not in self.settings:
            self.settings[guild_id] = {}

        # set channel id for this guild
        self.settings[guild_id]["channel_id"] = channel_id.id

        # notify and save
        await ctx.send(f"> Set announcement channel to <#{channel_id.id}>.")
        self.save_settings()

    # used to force an announcement for a streamer, ignoring the 6hr rule for automatic broadcasts
    @twitch.command(name="force", description="Forces an announcement for a broadcaster in the designated channel")
    @app_commands.describe(name="Name of the broadcaster")
    @commands.has_permissions(manage_guild=True)
    async def force_announcement_command(self, ctx: Context, name: str):
        # get guild
        guild_id = str(ctx.guild.id)

        # check if we have a list for this guild yet
        if guild_id not in self.settings:
            self.settings[guild_id] = {}

        # set to lower to caps doesn't matter
        name = name.lower()

        # check if this streamer is in the list
        if "names" in self.settings[guild_id] and name in self.settings[guild_id]["names"]:
            # force announcement
            await ctx.send("> Attempting to force the announcement...", delete_after=5)
            await self.force_announcement(ctx, guild_id, name)
        # else assume this streamer is not in the list yet
        else:
            await ctx.send(f"`{name}` is not in the list of broadcasters. Use `/twitch add` to add this streamer.")

        # save settings
        self.save_settings()

    def load_settings(self):
        # try to open settings file
        try:
            with open("./settings.json", "r") as f:
                # load settings
                self.settings = json.load(f)
        except FileNotFoundError:
            # assume no file exists, set default
            self.settings = {}

    def save_settings(self):
        # open settings file to write
        with open("./settings.json", "w") as f:
            json.dump(self.settings, f)

    async def validate_token(self):
        # set up get request
        url = "https://id.twitch.tv/oauth2/validate"
        headers = {
            "Authorization": f"OAuth {self.twitch_access_token}"
        }

        # send request
        response = requests.get(url, headers=headers)

        # check response
        if response.status_code == 200:
            print(f"{timestamp()} Token is valid")
        else:
            print(f"{timestamp()} Token is invalid... Generating a new one")
            token = get_oauth_token()
            if token:
                # update token
                print(f"{timestamp()} Generated OAuth Access Token: {token}")
                os.environ['TWITCH_ACCESS_TOKEN'] = token
                update_env_file('TWITCH_ACCESS_TOKEN', token)

    async def check_streams(self):
        # wait until the bot is ready to start checking streams
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            # load guild settings
            self.load_settings()

            # validate our token
            await self.validate_token()

            # get live stream data for every streamer in every guild
            for guild_id, data in self.settings.items():
                await self.get_live_streams(guild_id, data)

            # check every 10 mins... this is so that the stream has time to generate a thumbnail
            await asyncio.sleep(600)

    async def get_live_streams(self, guild_id, dataz):
        # get each broadcaster for this guild
        for username in dataz.get("names", []):
            # set up get request
            url = "https://api.twitch.tv/helix/streams"
            params = {
                "user_login": username
            }
            headers = {
                "Client-ID": self.twitch_client_id,
                "Authorization": f"Bearer {self.twitch_access_token}"
            }

            # send request
            response = requests.get(url, params=params, headers=headers)
            data = response.json()

            # check for data
            if 'data' in data:
                if data["data"]:
                    stream_id = data["data"][0]["id"]
                    # check if we haven't announced this stream by ID
                    if stream_id not in self.streams.get(guild_id, {}):
                        self.streams.setdefault(guild_id, {})[stream_id] = datetime.now()
                        # try to send message
                        await self.send_live_stream_message(guild_id, data["data"][0])

    # helper function for /twitch list command
    async def list_broadcasters(self, ctx, guild_id):
        # check if there are broadcasters set
        if "names" in self.settings[guild_id]:
            if "channel_id" in self.settings[guild_id]:
                channel_id = f"<#{self.settings[guild_id]['channel_id']}>"
            else:
                channel_id = "None"
            # display
            broadcasters = "> "
            broadcasters += "\n> ".join(self.settings[guild_id]["names"])
            await ctx.send(
                f"Current broadcasters set to check for this guild:\n> Announcement Channel: {channel_id}\n{broadcasters}")
        else:
            await ctx.send("> There are no broadcasters set to check for this guild.")

    # forces an announcement for a specific broadcaster
    async def force_announcement(self, ctx, guild_id, broadcaster_name):
        # check that a channel ID has been set
        if guild_id in self.settings and "channel_id" in self.settings[guild_id]:
            # get the channel ID for this guild
            channel_id = self.settings[guild_id]["channel_id"]
            channel = self.bot.get_channel(channel_id)

            if channel:
                # set up request to API
                url = "https://api.twitch.tv/helix/streams"
                params = {"user_login": broadcaster_name}
                headers = {
                    "Client-ID": self.twitch_client_id,
                    "Authorization": f"Bearer {self.twitch_access_token}"
                }

                # send request
                response = requests.get(url, params=params, headers=headers)
                data = response.json()

                if data["data"]:
                    # if stream data is available, send the announcement
                    stream_data = data["data"][0]
                    await send_announcement(channel, stream_data)
                else:
                    # if no data exists, the user is offline
                    await ctx.send(f"> `{broadcaster_name}` is currently offline.")
            else:
                # if channel does not exist, no channel is set yet
                await ctx.send(f"> Announcement channel has not been set yet. Use `/twitch setchannel` to get started.")

    # sends the automatic live stream message for broadcasters in the list
    # NOTE: to limit pings, it is one broadcast per streamer every 6hrs
    async def send_live_stream_message(self, guild_id, stream_data):
        if guild_id in self.settings and "channel_id" in self.settings[guild_id]:
            # get specified channel ID for this guild
            channel_id = self.settings[guild_id]["channel_id"]
            channel = self.bot.get_channel(channel_id)

            if channel:
                broadcaster_name = stream_data["user_name"]
                current_time = datetime.now()
                last_announcement_time = self.streams.get(guild_id, {}).get(broadcaster_name)

                # check for an announcement for this specific streamer within the last 6hrs
                if not last_announcement_time or (current_time - last_announcement_time) > timedelta(hours=6):
                    await send_announcement(channel, stream_data)
                    self.streams.setdefault(guild_id, {})[broadcaster_name] = current_time


async def setup(bot):
    await bot.add_cog(TwitchCmds(bot))
