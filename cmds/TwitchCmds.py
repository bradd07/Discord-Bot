from datetime import datetime, timedelta
import discord
import requests
import asyncio
import json
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.context import SlashContext
from discord_slash.utils.manage_commands import create_option
from dotenv import load_dotenv
import os
import pytz

"""
Cog for twitch announcement commands.
Author: bradd07
"""


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

    @cog_ext.cog_subcommand(
        base="twitch",
        name="add",
        description="Add a broadcaster to the list",
        options=[
            create_option(
                name="name",
                description="Name of the broadcaster",
                option_type=3,
                required=True
            )
        ]
    )
    @commands.has_permissions(manage_guild=True)
    async def add_broadcaster(self, ctx: SlashContext, name: str):
        # get guild
        guild_id = str(ctx.guild.id)

        # check if we have a list for this guild yet
        if guild_id not in self.settings:
            self.settings[guild_id] = {}

        # set to lower to caps doesn't matter
        name = name.lower()

        # check if this streamer is already in the list
        if "names" in self.settings[guild_id] and name in self.settings[guild_id]["names"]:
            await ctx.send(f"> {name} is already in the list of broadcasters.")
        # else assume this streamer is not in the list yet
        else:
            self.settings[guild_id].setdefault("names", []).append(name)
            await ctx.send(f"> Added {name} to the list of broadcasters to check.")

        # save settings
        self.save_settings()

    @cog_ext.cog_subcommand(
        base="twitch",
        name="remove",
        description="Remove a broadcaster from the list",
        options=[
            create_option(
                name="name",
                description="Name of the broadcaster",
                option_type=3,
                required=True
            )
        ]
    )
    @commands.has_permissions(manage_guild=True)
    async def remove_broadcaster(self, ctx: SlashContext, name: str):
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
            await ctx.send(f"> Removed {name} from the list of broadcasters.")
        # else assume this streamer is not in the list yet
        else:
            await ctx.send(f"> {name} is not in the list of broadcasters.")

        # save settings
        self.save_settings()

    @cog_ext.cog_subcommand(
        base="twitch",
        name="list",
        description="List all broadcasters",
    )
    @commands.has_permissions(manage_guild=True)
    async def list_broadcasters_command(self, ctx: SlashContext):
        # get guild
        guild_id = str(ctx.guild.id)

        # list broadcasters
        await self.list_broadcasters(ctx, guild_id)

    @cog_ext.cog_subcommand(
        base="twitch",
        name="setchannel",
        description="Set the announcement channel",
        options=[
            create_option(
                name="channel_id",
                description="Channel ID for announcements",
                option_type=7,
                required=True
            )
        ]
    )
    @commands.has_permissions(manage_guild=True)
    async def set_announcement_channel(self, ctx: SlashContext, channel_id):
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

    @cog_ext.cog_subcommand(
        base="twitch",
        name="force",
        description="Force an announcement for a broadcaster",
        options=[
            create_option(
                name="name",
                description="Name of the broadcaster",
                option_type=3,
                required=True
            )
        ]
    )
    @commands.has_permissions(manage_guild=True)
    async def force_announcement_command(self, ctx: SlashContext, name: str):
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
            await ctx.send(f"{name} is not in the list of broadcasters.")

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
            print("Token is valid")
        else:
            print("Token is invalid")

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

            # check every 5 mins
            await asyncio.sleep(300)

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
            if data["data"]:
                stream_id = data["data"][0]["id"]
                # check if we haven't announced this stream by ID
                if stream_id not in self.streams.get(guild_id, {}):
                    self.streams.setdefault(guild_id, {})[stream_id] = datetime.now()
                    # try to send message
                    await self.send_live_stream_message(guild_id, data["data"][0])

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
            await ctx.send(f"Current broadcasters set to check for this guild:\n> Announcement Channel: {channel_id}\n{broadcasters}")
        else:
            await ctx.send("> There are no broadcasters set to check for this guild.")

    async def force_announcement(self, ctx, guild_id, broadcaster_name):
        # check if we have a channel ID set for this guild
        if guild_id in self.settings and "channel_id" in self.settings[guild_id]:
            # get channel
            channel_id = self.settings[guild_id]["channel_id"]
            channel = self.bot.get_channel(channel_id)

            # make sure this is a real channel
            if channel:
                # set up get request
                url = "https://api.twitch.tv/helix/streams"
                params = {
                    "user_login": broadcaster_name
                }
                headers = {
                    "Client-ID": self.twitch_client_id,
                    "Authorization": f"Bearer {self.twitch_access_token}"
                }

                # send request
                response = requests.get(url, params=params, headers=headers)
                data = response.json()

                # check for data
                if data["data"]:
                    # get data
                    stream_data = data["data"][0]
                    stream_title = stream_data["title"]
                    stream_url = f"https://www.twitch.tv/{broadcaster_name}"
                    viewer_count = stream_data["viewer_count"]
                    game_name = stream_data["game_name"]

                    # set up embed
                    embed = discord.Embed(
                        title=f"**{stream_title}**",
                        url=stream_url,
                        color=discord.Color.red()
                    )
                    embed.set_author(name=stream_data['user_name'])
                    embed.set_image(
                        url=stream_data['thumbnail_url'].replace("{width}", "320").replace("{height}", "180"))
                    embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/1049713626895896686'
                                            '/1206815771129552906/Status_Logo.png?ex=65dd61c5&is=65caecc5&hm'
                                            '=2ea0ae42f9debc00f14796c03c821a31d91bf91d10a5702c1d6f2eed05b3598d&')
                    embed.add_field(name="Viewers", value=viewer_count, inline=False)
                    embed.add_field(name="Game", value=game_name, inline=False)

                    # get mst current time
                    mst_timezone = pytz.timezone('America/Phoenix')
                    mst_now = datetime.now(tz=mst_timezone)
                    embed.set_footer(text="Twitch • " + mst_now.strftime("%m/%d/%Y %I:%M %p"),
                                     icon_url="https://cdn-longterm.mee6.xyz/plugins"
                                              "/twitch/logo.png")

                    # send the message
                    await channel.send(
                        f"Hey @everyone, {stream_data['user_name']} is now live on Twitch! Come and support the stream! Leave a comment and chat with them!",
                        embed=embed)
                else:
                    # assume there is no stream available
                    await ctx.send(f"> {broadcaster_name} is currently offline.")
            else:
                # assume there is no channel set yet
                await ctx.send("> Announcement channel has not been set.")

    async def send_live_stream_message(self, guild_id, stream_data):
        # check if we have a channel ID set for this guild
        if guild_id in self.settings and "channel_id" in self.settings[guild_id]:
            # get channel
            channel_id = self.settings[guild_id]["channel_id"]
            channel = self.bot.get_channel(channel_id)

            # make sure this is a real channel
            if channel:
                # check that we have not made an announcement for this broadcaster within the last 6 hrs
                # regardless of how many streams that start within that period (one per broadcaster every 6hr)
                broadcaster_name = stream_data["user_name"]
                current_time = datetime.now()
                last_announcement_time = self.streams.get(guild_id, {}).get(broadcaster_name)
                if not last_announcement_time or (current_time - last_announcement_time) > timedelta(hours=6):
                    # assume no message has been sent for this specific streamer yet
                    stream_title = stream_data["title"]
                    stream_url = f"https://www.twitch.tv/{stream_data['user_name']}"
                    viewer_count = stream_data["viewer_count"]
                    game_name = stream_data["game_name"]

                    # set up embed
                    embed = discord.Embed(
                        title=f"**{stream_title}**",  # Display name as title
                        url=stream_url,
                        color=discord.Color.red()
                    )
                    embed.set_author(name=stream_data['user_name'])
                    embed.set_image(
                        url=stream_data['thumbnail_url'].replace("{width}", "320").replace("{height}", "180"))
                    embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/1049713626895896686'
                                            '/1206815771129552906/Status_Logo.png?ex=65dd61c5&is=65caecc5&hm'
                                            '=2ea0ae42f9debc00f14796c03c821a31d91bf91d10a5702c1d6f2eed05b3598d&')
                    embed.add_field(name="Viewers", value=viewer_count, inline=False)
                    embed.add_field(name="Game", value=game_name, inline=False)

                    # get mst current time
                    mst_timezone = pytz.timezone('America/Phoenix')
                    mst_now = datetime.now(tz=mst_timezone)
                    embed.set_footer(text="Twitch • " + mst_now.strftime("%m/%d/%Y %I:%M %p"),
                                     icon_url="https://cdn-longterm.mee6.xyz/plugins"
                                              "/twitch/logo.png")

                    # send the message
                    await channel.send(
                        f"Hey @everyone, {stream_data['user_name']} is now live on Twitch! Come and support the stream! Leave a comment and chat with them!",
                        embed=embed)
                    self.streams.setdefault(guild_id, {})[broadcaster_name] = current_time


def setup(bot):
    bot.add_cog(TwitchCmds(bot))
