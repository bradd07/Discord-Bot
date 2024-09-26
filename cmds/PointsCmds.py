import asyncio
import json
import os
import time
import discord
import random
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

"""
Cog for the points commands.
Author: bradd07
"""


class Points(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.points_file = "./points.json"
        self.points_data = {}
        self.raffles = {}

        # load the data if the file exists
        if os.path.exists(self.points_file):
            with open(self.points_file, "r") as f:
                self.points_data = json.load(f)
        else:
            # otherwise create an empty file
            with open(self.points_file, "w") as f:
                json.dump(self.points_data, f)

    async def save_points(self):
        with open(self.points_file, "w") as file:
            json.dump(self.points_data, file, indent=4)

    @commands.hybrid_command(name="points", description="Displays the user's current amount of points")
    async def display_points(self, ctx: Context, user: discord.User = None):
        # if user is not specified, assume they want their own points
        if user is None:
            user = ctx.author

        # make sure we have strings
        user_id = str(user.id)
        guild_id = str(ctx.guild.id)

        # check if this guild is saved yet
        if guild_id not in self.points_data:
            self.points_data[guild_id] = {}

        # check if this user is saved yet
        if user_id not in self.points_data[guild_id]:
            # set default
            self.points_data[guild_id][user_id] = 0

        # get points
        points = self.points_data[guild_id][user_id]

        # notify
        await ctx.send(f"> `{user.display_name}` has `{points}` points.")

    @commands.hybrid_command(name="setpoints", description="Manually set the amount of points a user has")
    @app_commands.describe(user="The user you want to modify the points of",
                           amount="The amount of points you want to their total to be")
    @commands.has_permissions(manage_guild=True)
    async def set_points(self, ctx: Context, user: discord.User, amount: int):
        # make sure we have strings
        user_id = str(user.id)
        guild_id = str(ctx.guild.id)

        # check if this guild is saved yet
        if guild_id not in self.points_data:
            self.points_data[guild_id] = {}

        # set points
        self.points_data[guild_id][user_id] = amount

        # write to file
        await self.save_points()

        # notify
        await ctx.send(f"> `{user.display_name}` now has `{amount}` points.", ephemeral=True)

    @commands.hybrid_command(name="addpoints", description="Adds points to a user's current total")
    @app_commands.describe(user="The user you want to modify the points of",
                           amount="The amount of points you want to add to their total")
    @commands.has_permissions(manage_guild=True)
    async def add_points(self, ctx: Context, user: discord.User, amount: int):
        # make sure we have strings
        user_id = str(user.id)
        guild_id = str(ctx.guild.id)

        # check if this guild is saved yet
        if guild_id not in self.points_data:
            self.points_data[guild_id] = {}

        # check if this user is saved yet
        if user_id not in self.points_data[guild_id]:
            # set default
            self.points_data[guild_id][user_id] = 0

        # add points
        self.points_data[guild_id][user_id] += amount
        new_points = self.points_data[guild_id][user_id]

        # write to file
        await self.save_points()

        # notify
        await ctx.send(f"> `{user.display_name}` now has `{new_points}` points (added `{amount}` points).",
                       ephemeral=True)

    @commands.hybrid_command(name="givepoints", description="Give some of your points to another player")
    @app_commands.describe(user="The user you want to give your points to",
                           amount="The amount of points you want to give")
    async def give_points(self, ctx: Context, user: discord.User, amount: int):
        # check for invalid amount
        if amount <= 0:
            await ctx.send("> The amount of points must be greater than 0.", ephemeral=True)
            return

        # make sure we have strings
        user_id = str(user.id)
        guild_id = str(ctx.guild.id)
        author_id = str(ctx.author.id)

        # check if this guild is saved yet
        if guild_id not in self.points_data:
            self.points_data[guild_id] = {}

        # check if the sender is saved yet
        if author_id not in self.points_data[guild_id]:
            # set default
            self.points_data[guild_id][author_id] = 0

        # check if the sender does not have enough funds
        if self.points_data[guild_id][author_id] < amount:
            await ctx.send("> You don't have enough points to give.", ephemeral=True)
            return

        # check if the recipient is saved yet
        if user_id not in self.points_data[guild_id]:
            # set default
            self.points_data[guild_id][user_id] = 0

        # update points
        self.points_data[guild_id][author_id] -= amount
        self.points_data[guild_id][user_id] += amount
        new_points = self.points_data[guild_id][user_id]

        # write to file
        await self.save_points()

        # notify
        await ctx.send(
            f"> You gave `{amount}` points to `{user.display_name}`. They now have `{new_points}` points.")

    @commands.hybrid_command(name="leaderboard", description="Displays the top 5 users with the most points")
    async def leaderboard(self, ctx: Context):
        # get guild
        guild_id = str(ctx.guild.id)

        # check if this guild is saved yet
        if guild_id not in self.points_data:
            self.points_data[guild_id] = {}

        # sort the users by their points, and only take the top 5
        sorted_users = sorted(self.points_data[guild_id].items(), key=lambda x: x[1], reverse=True)[:5]

        # create a nicely formatted leaderboard embed
        leaderboard_embed = discord.Embed(title="Leaderboard")
        for i, (user_id, points) in enumerate(sorted_users):
            try:
                user = await self.bot.fetch_user(int(user_id))
                leaderboard_embed.add_field(name=f"**@{user.display_name}**", value=f"{points} points",
                                            inline=False)
            except discord.NotFound:
                leaderboard_embed.add_field(name=f"Unknown User", value=f"{points} points", inline=False)

        # send the message
        await ctx.send(embed=leaderboard_embed)

    @commands.hybrid_command(name="raffle", description="Create a raffle for free points!")
    @app_commands.describe(amount="The amount of points you want to give away",
                           duration="How long to run the raffle for (in seconds)")
    @commands.has_permissions(manage_guild=True)
    async def create_raffle(self, ctx: Context, amount: int, duration: int):
        # get guild
        guild_id = str(ctx.guild.id)

        # check if this guild is saved yet
        if guild_id not in self.raffles:
            # set default
            self.raffles[guild_id] = {"active": False}

        # check if this guild has an active raffle
        if self.raffles[guild_id]["active"]:
            await ctx.send("> There is already an ongoing raffle in this guild.", ephemeral=True)
            return

        # check for invalid amount/duration
        if amount <= 0 or duration <= 0:
            await ctx.send("> Please provide a valid amount and duration.", ephemeral=True)
            return

        # save values
        self.raffles[guild_id]["active"] = True
        self.raffles[guild_id]["amount"] = amount
        self.raffles[guild_id]["end_time"] = time.time() + duration
        self.raffles[guild_id]["participants"] = []

        # notify
        await ctx.send(f"A raffle for `{amount}` points has been created. Type /join to participate!")

        # wait until we have reached the end time
        while time.time() < self.raffles[guild_id]["end_time"]:
            await asyncio.sleep(1)

        # end the raffle, pick winner
        await self.end_raffle(ctx, guild_id)

    async def end_raffle(self, ctx, guild_id):
        # make sure there is an active raffle
        if not self.raffles[guild_id]["active"]:
            return

        # update flag
        self.raffles[guild_id]["active"] = False

        # check that there were actually participants
        if not self.raffles[guild_id]["participants"]:
            await ctx.send("No one participated in the raffle. Better luck next time!")
            return

        # get a random winner
        winner = random.choice(self.raffles[guild_id]["participants"])
        user_id = str(winner.id)

        # make sure we have this user saved for this guild
        if user_id not in self.points_data[guild_id]:
            # if not, set default
            self.points_data[guild_id][user_id] = 0

        # update points
        self.points_data[guild_id][user_id] += self.raffles[guild_id]["amount"]

        # write to file
        await self.save_points()

        # notify winner
        await ctx.send(f"> `{winner.display_name}` won the raffle and received `{self.raffles[guild_id]['amount']}` "
                       f"points!")
        self.raffles.pop(guild_id)

    @commands.hybrid_command(name="join", description="Join the ongoing raffle (if there is one)")
    async def join_raffle(self, ctx: Context):
        # get guild
        guild_id = str(ctx.guild.id)

        # make sure there is not a raffle
        if guild_id not in self.raffles:
            await ctx.send("> There is no ongoing raffle in this server.", ephemeral=True)
            return

        # get the raffle for this guild
        raffle = self.raffles[guild_id]

        # make sure they haven't already joined this raffle
        if ctx.author in raffle["participants"]:
            await ctx.send("> You have already joined the raffle.", ephemeral=True)
            return

        # add the user to the raffle, notify
        raffle["participants"].append(ctx.author)
        await ctx.send(f"> `{ctx.author.display_name}` has joined the raffle.")


async def setup(bot):
    await bot.add_cog(Points(bot))
