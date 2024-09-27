import discord
import requests
import asyncio
import json
import os
import pytz
import time
from datetime import datetime, timedelta
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from dotenv import load_dotenv
from typing import Optional
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


def is_url_image(image_url):
    image_extensions = ["jpg", "jpeg", "png", "gif", "bmp", "webp"]

    # check URL extension
    if any(image_url.lower().endswith(ext) for ext in image_extensions):
        return True

    # make a request to the URL
    try:
        response = requests.head(image_url, allow_redirects=True)
        content_type = response.headers.get("Content-Type")
        if content_type and content_type.startswith("image"):
            return True
    except requests.RequestException:
        pass

    return False


def get_custom_thumbnail_embed(streamer_name: str, custom_thumbnail: str):
    embed = discord.Embed(
        title="Thumbnail Preview",
        description=f"`{streamer_name}`",
        color=discord.Color.purple()
    )
    embed.set_image(url=custom_thumbnail)
    return embed


def timestamp():
    return (Back.BLACK + Fore.GREEN + Style.BRIGHT +
            datetime.now(pytz.utc).astimezone(pytz.timezone('US/Arizona')).strftime("%H:%M:%S GMT/PST" +
                                                                                    Back.RESET + Fore.WHITE))


# this class handles the Accept/Cancel buttons for both changing a thumbnail
# and for changing the announcement message. what action(s) to take is determined by the
# flag provided during initialization ("thumbnail" or "message)
class ConfirmationButtons(discord.ui.View):
    def __init__(self, ctx: commands.Context, settings: dict, flag: str, streamer_name=None, image_url=None, message=None):
        super().__init__(timeout=None)
        # set optional parameters
        self.streamer_name = streamer_name
        self.image_url = image_url
        self.message = message

        # set required parameters
        self.ctx = ctx
        self.settings = settings
        self.guild_id = str(ctx.guild.id)
        self.flag = flag

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        # check what we are accepting
        if self.flag == "thumbnail":
            # set the custom thumbnail
            self.settings[self.guild_id]["thumbnails"][self.streamer_name] = self.image_url

            # notify
            embed = discord.Embed(title="Custom thumbnail set", color=discord.Color.purple())
            embed.add_field(name=f"Modified by @{self.ctx.author}", value=f"For `{self.streamer_name}`", inline=False)
            embed.set_image(url=self.image_url)
            if self.ctx.guild.icon:
                # attempt to use the current guild's icon
                embed.set_thumbnail(url=self.ctx.guild.icon.url)
            else:
                # use default Status brand
                embed.set_thumbnail(url='https://i.imgur.com/gZyZBpQ.png')

            await interaction.response.send_message(embed=embed)
            # await interaction.response.send_message(f"> Custom thumbnail for `{self.streamer_name}` "
            #                                         f"has been set to `{self.image_url}` by "
            #                                         f"`{self.ctx.author.display_name}`")
        elif self.flag == "message":
            # set the custom message
            self.settings[self.guild_id]["message"] = self.message

            # notify
            embed = discord.Embed(title="New announcement message set", color=discord.Color.purple())
            embed.add_field(name=f"Modified by @{self.ctx.author}", value=self.message, inline=False)
            if self.ctx.guild.icon:
                # attempt to use the current guild's icon
                embed.set_thumbnail(url=self.ctx.guild.icon.url)
            else:
                # use default Status brand
                embed.set_thumbnail(url='https://i.imgur.com/gZyZBpQ.png')

            await interaction.response.send_message(embed=embed)

        self.save_settings()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.flag == "thumbnail":
            await interaction.response.send_message(f"> Thumbnail change for `{self.streamer_name}` has been cancelled.",
                                                    ephemeral=True)
        elif self.flag == "message":
            await interaction.response.send_message(f"Announcement message change has been cancelled.", ephemeral=True)
        self.stop()

    def save_settings(self):
        with open('settings.json', 'w') as file:
            json.dump(self.settings, file, indent=4)


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

    @twitch.command(name="setmessage", description="Set a custom message for livestream announcements")
    @app_commands.describe(message='What do you want to say? ("default" to reset)')
    @commands.has_permissions(manage_guild=True)
    async def set_message(self, ctx: Context, message: str):
        # get guild
        guild_id = str(ctx.guild.id)

        if message == "default":
            # set back to default
            self.settings[guild_id].pop("message", None)
            embed = discord.Embed(title="New announcement message set")
            embed.add_field(name=f"Set to default by @{ctx.author}", value="", inline=False)

            if ctx.guild.icon:
                # attempt to use the current guild's icon
                embed.set_thumbnail(url=ctx.guild.icon.url)
            else:
                # use default Status brand
                embed.set_thumbnail(url='https://i.imgur.com/gZyZBpQ.png')

            await ctx.send(embed=embed)
            self.save_settings()
        else:
            # check if we have a list for this guild yet
            if guild_id not in self.settings:
                self.settings[guild_id] = {}

            # provide a preview with Accept and Cancel buttons
            view = ConfirmationButtons(ctx, self.settings, "message", message=message)
            embed = discord.Embed(title="Confirm your changes", color=discord.Color.purple())
            embed.add_field(name=f"New Announcement Message:", value=message, inline=False)
            if ctx.guild.icon:
                # attempt to use the current guild's icon
                embed.set_thumbnail(url=ctx.guild.icon.url)
            else:
                # use default Status brand
                embed.set_thumbnail(url='https://i.imgur.com/gZyZBpQ.png')
            await ctx.send(embed=embed, view=view, ephemeral=True)

    @twitch.command(name="thumbnail", description="Set a custom thumbnail for a Twitch streamer")
    @app_commands.describe(name="Name of the streamer to modify/view",
                           image_url='URL of the image (type "default" to reset)')
    @commands.has_permissions(manage_guild=True)
    async def set_thumbnail(self, ctx: Context, name: str, image_url: Optional[str]):
        # get guild
        guild_id = str(ctx.guild.id)

        # set to lower to caps doesn't matter
        name = name.lower()

        # check if we have a list for this guild yet
        if guild_id not in self.settings:
            self.settings[guild_id] = {"thumbnails": {}}
        if "thumbnails" not in self.settings[guild_id]:
            self.settings[guild_id]["thumbnails"] = {}

        # check if this streamer is already in the list
        if "names" in self.settings[guild_id] and name in self.settings[guild_id]["names"]:
            # check if they provided a URL at all
            if image_url:
                # check if we need to set back to default
                if image_url == "default":
                    self.settings[guild_id]["thumbnails"].pop(name, None)
                    await ctx.send(f"> Thumbnail for `{name}` has been set to `{image_url}` "
                                   f"by `{ctx.author.display_name}`")
                else:
                    # check that this is a valid URL that is an image
                    if is_url_image(image_url):
                        # Provide a preview with Accept and Cancel buttons
                        embed = get_custom_thumbnail_embed(name, image_url)
                        view = ConfirmationButtons(ctx, self.settings, "thumbnail", streamer_name=name, image_url=image_url)
                        await ctx.send(embed=embed, view=view, ephemeral=True)
                    else:
                        # assume not an image link
                        await ctx.send(f"> `{image_url}` is not a valid image URL", ephemeral=True)
            else:
                # no URL provided, give a preview of the current thumnail if it exists
                custom_thumbnail = self.settings[guild_id].get("thumbnails", {}).get(name)
                if custom_thumbnail:
                    # Provide a preview of the existing custom thumbnail
                    embed = get_custom_thumbnail_embed(name, custom_thumbnail)
                    await ctx.send(embed=embed, ephemeral=True)
                else:
                    await ctx.send(f"> No custom thumbnail is set for `{name}`. "
                                   f"Try `/twitch thumbnail {name} [URL]` to set one for them!", ephemeral=True)
        # else assume this streamer is not in the list yet
        else:
            await ctx.send(f"> `{name}` is not in the list of broadcasters. "
                           f"Add them with `/twitch add [name]`!", ephemeral=True)

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
            with open("./settings.json", "r") as file:
                # load settings
                self.settings = json.load(file)
        except FileNotFoundError:
            # assume no file exists, set default
            self.settings = {}

    def save_settings(self):
        # open settings file to write
        with open("./settings.json", "w") as file:
            json.dump(self.settings, file, indent=4)

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
                        stream_data = data["data"][0]
                        if guild_id in self.settings and "channel_id" in self.settings[guild_id]:
                            # get specified channel ID for this guild
                            channel_id = self.settings[guild_id]["channel_id"]
                            channel = self.bot.get_channel(channel_id)

                            # make sure channel exists
                            if channel:
                                broadcaster_name = stream_data["user_name"]
                                current_time = datetime.now()
                                last_announcement_time = self.streams.get(guild_id, {}).get(broadcaster_name)

                                # check for an announcement for this specific streamer within the last 6hrs
                                if not last_announcement_time or (current_time - last_announcement_time) > timedelta(
                                        hours=6):
                                    await self.send_announcement(channel, stream_data, guild_id)
                                    self.streams.setdefault(guild_id, {})[broadcaster_name] = current_time

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
                f"Current broadcasters set to check for this guild:\n> Announcement Channel: "
                f"{channel_id}\n{broadcasters}")
        else:
            await ctx.send("> There are no broadcasters set to check for this guild.")

    # helper method for sending an announcement message to the specified channel with the collected stream data
    async def send_announcement(self, channel, stream_data, guild_id):
        # extract data
        stream_title = stream_data["title"]
        stream_url = f"https://www.twitch.tv/{stream_data['user_name']}"
        viewer_count = stream_data["viewer_count"]
        game_name = stream_data["game_name"]
        name = stream_data['user_name']
        guild = self.bot.get_guild(int(guild_id))

        # set up embed
        embed = discord.Embed(
            title=f"**{stream_title}**",
            url=stream_url,
            color=discord.Color.purple()
        )
        embed.set_author(name=name)

        # get custom thumbnail if available
        custom_thumbnail = self.settings.get(guild_id, {}).get("thumbnails", {}).get(name)
        if custom_thumbnail:
            embed.set_image(url=custom_thumbnail)
        else:
            # generate the current UNIX timestamp
            unix_time = int(time.time())

            # default to Twitch stream thumbnail with cache busting
            embed.set_image(
                url=f"{stream_data['thumbnail_url'].replace('{width}', '320').replace('{height}', '180')}?v={unix_time}")

        if guild.icon:
            # attempt to use the current guild's icon
            embed.set_thumbnail(url=guild.icon.url)
        else:
            # use default Status brand
            embed.set_thumbnail(url='https://i.imgur.com/gZyZBpQ.png')
        embed.add_field(name="Viewers", value=viewer_count, inline=False)
        embed.add_field(name="Game", value=game_name, inline=False)

        # get current time and footer
        embed.set_footer(text="Twitch",
                         icon_url="https://cdn-longterm.mee6.xyz/plugins/twitch/logo.png")
        embed.timestamp = datetime.now()

        # send the message
        custom_message = self.settings.get(guild_id, {}).get("message")
        if custom_message and custom_message != "":
            # replace {name} placeholder with actual name variable
            formatted_message = custom_message.format(name=name)
            await channel.send(formatted_message, embed=embed)
        else:
            await channel.send(
                f"Hey @everyone, `{name}` is now live on Twitch! Come and support the stream! "
                f"Leave a comment and chat with them!",
                embed=embed)

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
                    await self.send_announcement(channel, stream_data, guild_id)
                else:
                    # if no data exists, the user is offline
                    await ctx.send(f"> `{broadcaster_name}` is currently offline.")
            else:
                # if channel does not exist, no channel is set yet
                await ctx.send(f"> Announcement channel has not been set yet. Use `/twitch setchannel` to get started.")


async def setup(bot):
    await bot.add_cog(TwitchCmds(bot))
