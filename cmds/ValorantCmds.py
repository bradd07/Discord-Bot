import json
from datetime import datetime

import discord
from dateutil.tz import tz
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from dateutil import parser
from typing import Optional

from cmds.TwitchCmds import is_url_image

"""
Cog for Valorant commands: match scheduling, match results submission, stat tracker
Author: bradd07
"""

TIMEZONE_OFFSETS = {
    'EST': tz.gettz('America/New_York'),
    'EDT': tz.gettz('America/New_York'),
    'CST': tz.gettz('America/Chicago'),
    'CDT': tz.gettz('America/Chicago'),
    'MST': tz.gettz('America/Denver'),
    'MDT': tz.gettz('America/Denver'),
    'PST': tz.gettz('America/Los_Angeles'),
    'PDT': tz.gettz('America/Los_Angeles'),
    'UTC': tz.gettz('UTC'),
    'GMT': tz.gettz('GMT')
    # add more as needed
}


class ValCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = {}
        self.load_settings()  # load settings from json file

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

    @commands.hybrid_group(name="schedule", description="Schedule a match between two teams")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(team1="Team 1 of the match you want to schedule",
                           team2="Team 2 of the match you want to schedule",
                           date="Date and time of the match")
    async def schedule(self, ctx: Context):
        return

    @schedule.command(name="send", description="Send a message notifying users of a scheduled match")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(team1="Team 1 of the match you want to schedule",
                           team2="Team 2 of the match you want to schedule",
                           date="Date and time of the match")
    async def send(self, ctx: Context, team1: discord.Role, team2: discord.Role, date: str, thumbnail: Optional[str]):
        # check that a channel has been set
        guild_id = str(ctx.guild.id)
        if guild_id in self.settings and "schedule_channel" in self.settings[guild_id]:
            # get the channel ID for this guild
            channel_id = self.settings[guild_id]["schedule_channel"]
            channel = self.bot.get_channel(int(channel_id))

            # make sure that the set channel still exists
            if channel:
                try:
                    # replace timezone abbreviations with their proper offsets, if a timezone is provided by the user
                    tzinfos = None
                    for tz_name, tz_info in TIMEZONE_OFFSETS.items():
                        if tz_name in date.upper():
                            # if we found an abbreviation, set tzinfos
                            tzinfos = {tz_name: tz_info}
                            break

                    # remove '@' from the date string if it exists since it breaks parser
                    date = date.replace('@', '')

                    # parse date with timezone info
                    parsed_date = parser.parse(date.upper(), tzinfos=tzinfos)

                    # convert the datetime object to a UNIX timestamp
                    unix_timestamp = int(parsed_date.timestamp())

                    # set up embed
                    embed = discord.Embed(
                        title=f"",
                        description=f"## <a:notification:1290833540711321621> UPCOMING MATCH",
                        color=discord.Color.dark_blue()
                    )
                    embed.add_field(name="Teams", value=f'<@&{team1.id}> vs. <@&{team2.id}>',
                                    inline=False)
                    embed.add_field(name="When", value=f'<t:{unix_timestamp}:f>', inline=False)
                    if ctx.guild.icon:
                        # attempt to use the current guild's icon
                        embed.set_thumbnail(url=ctx.guild.icon.url)
                    else:
                        # use default Status brand
                        embed.set_thumbnail(url='https://i.imgur.com/gZyZBpQ.png')
                    if thumbnail:
                        if is_url_image(thumbnail):
                            embed.set_image(url=thumbnail)
                        else:
                            # assume not an image link
                            await ctx.send(f"> `{thumbnail}` is not a valid image URL", ephemeral=True)
                            return

                    # send the embed to the designated channel
                    await channel.send(embed=embed)
                    await ctx.send(f"> Message sent successfully to {channel.mention}", ephemeral=True)

                # incorrect date/time entered by user
                except ValueError as e:
                    await ctx.send(f"{date} Does not seem to be a valid date/time. Please try again.",
                                   ephemeral=True)
            else:
                # no channel has been set yet
                await ctx.send(f"> Announcement channel for scheduled matches has not been set yet. "
                               f"Use `/schedule setchannel` to get started.",
                               ephemeral=True)
        else:
            # no channel has been set yet
            await ctx.send(f"> Announcement channel for scheduled matches has not been set yet. "
                           f"Use `/schedule setchannel` to get started.",
                           ephemeral=True)

    @schedule.command(name="setchannel", description="Designate the channel for scheduled game announcements")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(channel="Channel to send announcements to")
    async def set_channel(self, ctx: Context, channel: discord.TextChannel):
        # get guild
        guild_id = str(ctx.guild.id)

        # check if we have a list for this guild yet
        if guild_id not in self.settings:
            self.settings[guild_id] = {}

        # set channel id for this guild
        self.settings[guild_id]["schedule_channel"] = channel.id

        # notify and save
        embed = discord.Embed(title="Set match announcement channel", colour=discord.Colour.dark_blue())
        embed.add_field(name=f"Modified by @{ctx.author}", value=f"Set to {channel.mention}", inline=False)

        if ctx.guild.icon:
            # attempt to use the current guild's icon
            embed.set_thumbnail(url=ctx.guild.icon.url)
        else:
            # use default Status brand
            embed.set_thumbnail(url='https://i.imgur.com/gZyZBpQ.png')

        await ctx.send(embed=embed)
        self.save_settings()


async def setup(bot):
    await bot.add_cog(ValCommands(bot))
