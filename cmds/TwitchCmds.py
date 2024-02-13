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

    @cog_ext.cog_slash(
        name="twitch",
        description="Manage Twitch settings",
        guild_ids=[654559898641760256, 715119084056084550],  # testing guilds, can be changed
        options=[
            create_option(
                name="command",
                description="Select a command",
                option_type=3,
                required=True,
                choices=[
                    {"name": "add", "value": "add"},
                    {"name": "remove", "value": "remove"},
                    {"name": "list", "value": "list"},
                    {"name": "setchannel", "value": "setchannel"},
                    {"name": "force", "value": "force"}
                ]
            ),
            create_option(
                name="value",
                description="Value for the command",
                option_type=3,
                required=False
            )
        ]
    )
    async def twitch(self, ctx: SlashContext, action: str, value: str = None):
        guild_id = str(ctx.guild.id)
        if guild_id not in self.settings:
            self.settings[guild_id] = {}
        if action == "add":
            if value is not None:
                value = str(value).lower()
                if "names" in self.settings[guild_id] and value in self.settings[guild_id]["names"]:
                    await ctx.send(f"{value} is already in the list of broadcasters.")
                else:
                    self.settings[guild_id].setdefault("names", []).append(value)
                    await ctx.send(f"Added {value} to the list of broadcasters to check.")
            else:
                await ctx.send("You must provide the name of the streamer to add to the list.")
        elif action == "remove":
            if value is not None:
                value = str(value).lower()
                if "names" in self.settings[guild_id] and value in self.settings[guild_id]["names"]:
                    self.settings[guild_id]["names"].remove(value)
                    await ctx.send(f"Removed {value} from the list of broadcasters.")
                else:
                    await ctx.send(f"{value} is not in the list of broadcasters.")
            else:
                await ctx.send("You must provide the name of the streamer to remove from the list.")
        elif action == "list":
            await self.list_broadcasters(ctx, guild_id)
        elif action == "setchannel":
            if value is not None:
                value = str(value).lower()
                try:
                    channel_id = int(value.strip("<>#"))
                    self.settings[guild_id]["channel_id"] = channel_id
                    await ctx.send(f"Set announcement channel to <#{channel_id}>.")
                except ValueError:
                    await ctx.send("Invalid channel ID. To get an ID, right click the channel and copy the ID.")
            else:
                await ctx.send("You must provide the channel ID in which you want to set the announcement channel.")
        elif action == "force":
            if value is not None:
                value = str(value).lower()
                if "names" in self.settings[guild_id] and value in self.settings[guild_id]["names"]:
                    await self.force_announcement(ctx, guild_id, value)
                    await ctx.send("Forced announcement.")
                else:
                    await ctx.send(f"{value} is not in the list of broadcasters.")
            else:
                await ctx.send("You must provide the name of the streamer to force a broadcast for.")
        self.save_settings()

    def load_settings(self):
        try:
            with open("./settings.json", "r") as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            self.settings = {}

    def save_settings(self):
        with open("./settings.json", "w") as f:
            json.dump(self.settings, f)

    async def validate_token(self):
        # header contains app access token
        url = "https://id.twitch.tv/oauth2/validate"
        headers = {
            "Authorization": f"OAuth {self.twitch_access_token}"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print("Token is valid")
        else:
            print("Token is invalid")

    async def check_streams(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            self.load_settings()
            await self.validate_token()
            for guild_id, data in self.settings.items():
                await self.get_live_streams(guild_id, data)
            await asyncio.sleep(300)  # Check every 5 mins

    async def get_live_streams(self, guild_id, dataz):
        for username in dataz.get("names", []):
            url = "https://api.twitch.tv/helix/streams"
            params = {
                "user_login": username
            }
            headers = {
                "Client-ID": self.twitch_client_id,
                "Authorization": f"Bearer {self.twitch_access_token}"
            }
            response = requests.get(url, params=params, headers=headers)
            data = response.json()
            if data["data"]:
                stream_id = data["data"][0]["id"]
                if stream_id not in self.streams.get(guild_id, {}):
                    self.streams.setdefault(guild_id, {})[stream_id] = datetime.now()
                    await self.send_live_stream_message(guild_id, data["data"][0])

    async def list_broadcasters(self, ctx, guild_id):
        if "names" in self.settings[guild_id]:
            broadcasters = "\n".join(self.settings[guild_id]["names"])
            await ctx.send(f"Current broadcasters set to check for this guild:\n{broadcasters}")
        else:
            await ctx.send("There are no broadcasters set to check for this guild.")

    async def force_announcement(self, ctx, guild_id, broadcaster_name):
        # avoid keyError
        if guild_id in self.settings and "channel_id" in self.settings[guild_id]:
            channel_id = self.settings[guild_id]["channel_id"]
            channel = self.bot.get_channel(channel_id)
            if channel:
                url = "https://api.twitch.tv/helix/streams"
                params = {
                    "user_login": broadcaster_name
                }
                headers = {
                    "Client-ID": self.twitch_client_id,
                    "Authorization": f"Bearer {self.twitch_access_token}"
                }
                response = requests.get(url, params=params, headers=headers)
                data = response.json()
                if data["data"]:
                    stream_data = data["data"][0]
                    stream_title = stream_data["title"]
                    stream_url = f"https://www.twitch.tv/{broadcaster_name}"
                    viewer_count = stream_data["viewer_count"]
                    game_name = stream_data["game_name"]
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
                    embed.set_footer(text="Twitch • " + datetime.now().strftime("%m/%d/%Y %I:%M %p"),
                                     icon_url="https://cdn-longterm.mee6.xyz/plugins"
                                              "/twitch/logo.png")
                    await channel.send(f"Hey @everyone, {stream_data['user_name']} is now live on Twitch! Come and support the stream! Leave a comment and chat with them!", embed=embed)
                else:
                    await ctx.send(f"{broadcaster_name} is currently offline.")
            else:
                await ctx.send("Announcement channel has not been set.")

    async def send_live_stream_message(self, guild_id, stream_data):
        # avoid keyError
        if guild_id in self.settings and "channel_id" in self.settings[guild_id]:
            channel_id = self.settings[guild_id]["channel_id"]
            channel = self.bot.get_channel(channel_id)
            # check that a channel is set and valid
            if channel:
                # check that we have not made an announcement for this broadcaster within the last 6 hrs
                # regardless of how many streams that start within that period
                broadcaster_name = stream_data["user_name"]
                current_time = datetime.now()
                last_announcement_time = self.streams.get(guild_id, {}).get(broadcaster_name)
                if not last_announcement_time or (current_time - last_announcement_time) > timedelta(hours=6):
                    # assume no message has been sent for this specific streamer yet
                    stream_title = stream_data["title"]
                    stream_url = f"https://www.twitch.tv/{stream_data['user_name']}"
                    viewer_count = stream_data["viewer_count"]
                    game_name = stream_data["game_name"]

                    # set up discord message
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
                    await channel.send(f"Hey @everyone, {stream_data['user_name']} is now live on Twitch! Come and support the stream! Leave a comment and chat with them!", embed=embed)
                    self.streams.setdefault(guild_id, {})[broadcaster_name] = current_time


def setup(bot):
    bot.add_cog(TwitchCmds(bot))
