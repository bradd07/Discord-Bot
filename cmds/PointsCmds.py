import asyncio
import json
import os
import time
import discord
import random
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.context import SlashContext
from discord_slash.utils.manage_commands import create_option


class Points(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.points_file = "./points.json"
        self.points_data = {}
        self.raffles = {}

        if os.path.exists(self.points_file):
            with open(self.points_file, "r") as f:
                self.points_data = json.load(f)
        else:
            with open(self.points_file, "w") as f:
                json.dump(self.points_data, f)

    @cog_ext.cog_slash(name="points", description="Displays the user's current amount of points on that guild")
    async def display_points(self, ctx: SlashContext, user: discord.User = None):
        if user is None:
            user = ctx.author

        user_id = str(user.id)
        guild_id = str(ctx.guild.id)

        if guild_id not in self.points_data:
            self.points_data[guild_id] = {}

        if user_id not in self.points_data[guild_id]:
            self.points_data[guild_id][user_id] = 0

        points = self.points_data[guild_id][user_id]

        await ctx.send(f"> {user.display_name} has {points} points.")

    @cog_ext.cog_slash(name="setpoints", description="Set the amount of points a user has", options=[
        create_option(
            name="user",
            description="The user you want to set points for",
            option_type=6,
            required=True
        ),
        create_option(
            name="points",
            description="The amount of points you want to set",
            option_type=4,
            required=True
        )
    ])
    async def set_points(self, ctx: SlashContext, user: discord.User, points: int):
        user_id = str(user.id)
        guild_id = str(ctx.guild.id)

        if guild_id not in self.points_data:
            self.points_data[guild_id] = {}

        self.points_data[guild_id][user_id] = points

        with open(self.points_file, "w") as f:
            json.dump(self.points_data, f)

        await ctx.send(f"> {user.display_name} now has {points} points.")

    @cog_ext.cog_slash(name="addpoints", description="Adds points to the specified user's current total in that guild",
                       options=[
                           create_option(
                               name="user",
                               description="The user you want to add points to",
                               option_type=6,
                               required=True
                           ),
                           create_option(
                               name="amount",
                               description="The amount of points you want to add",
                               option_type=4,
                               required=True
                           )
                       ])
    async def add_points(self, ctx: SlashContext, user: discord.User, amount: int):
        user_id = str(user.id)
        guild_id = str(ctx.guild.id)

        if guild_id not in self.points_data:
            self.points_data[guild_id] = {}

        if user_id not in self.points_data[guild_id]:
            self.points_data[guild_id][user_id] = 0

        self.points_data[guild_id][user_id] += amount
        new_points = self.points_data[guild_id][user_id]

        with open(self.points_file, "w") as f:
            json.dump(self.points_data, f)

        await ctx.send(f"> {user.display_name} now has {new_points} points (added {amount} points).")

    @cog_ext.cog_slash(name="givepoints", description="Give some of your points to another player in the same guild",
                       options=[
                           create_option(
                               name="user",
                               description="The user you want to give points to",
                               option_type=6,
                               required=True
                           ),
                           create_option(
                               name="amount",
                               description="The amount of points you want to give",
                               option_type=4,
                               required=True
                           )
                       ])
    async def give_points(self, ctx: SlashContext, user: discord.User, amount: int):
        if amount <= 0:
            await ctx.send("> The amount of points must be greater than 0.")
            return

        user_id = str(user.id)
        guild_id = str(ctx.guild.id)
        author_id = str(ctx.author.id)

        if guild_id not in self.points_data:
            self.points_data[guild_id] = {}

        if author_id not in self.points_data[guild_id]:
            self.points_data[guild_id][author_id] = 0

        if self.points_data[guild_id][author_id] < amount:
            await ctx.send("> You don't have enough points to give.")
            return

        if user_id not in self.points_data[guild_id]:
            self.points_data[guild_id][user_id] = 0

        self.points_data[guild_id][author_id] -= amount
        self.points_data[guild_id][user_id] += amount
        new_points = self.points_data[guild_id][user_id]

        with open(self.points_file, "w") as f:
            json.dump(self.points_data, f)

        await ctx.send(
            f"> You gave {amount} points to {user.display_name}. {user.display_name} now has {new_points} points.")

    @cog_ext.cog_slash(name="leaderboard", description="Displays the top 5 users with the most points in that guild")
    async def leaderboard(self, ctx: SlashContext):
        guild_id = str(ctx.guild.id)

        if guild_id not in self.points_data:
            self.points_data[guild_id] = {}

        # Sort the users by their points, and only take the top 5
        sorted_users = sorted(self.points_data[guild_id].items(), key=lambda x: x[1], reverse=True)[:5]

        # Create a nicely formatted leaderboard embed
        leaderboard_embed = discord.Embed(title="Leaderboard")
        for i, (user_id, points) in enumerate(sorted_users):
            try:
                user = await self.bot.fetch_user(int(user_id))
                leaderboard_embed.add_field(name=f"**@{user.display_name}**", value=f"{points} points",
                                            inline=False)
            except discord.NotFound:
                leaderboard_embed.add_field(name=f"Unknown User", value=f"{points} points", inline=False)

        await ctx.send(embed=leaderboard_embed)

    @cog_ext.cog_slash(name="raffle", description="Create a raffle for free points")
    async def create_raffle(self, ctx: SlashContext, amount: int, duration: int):
        guild_id = str(ctx.guild.id)

        if guild_id not in self.raffles:
            self.raffles[guild_id] = {"active": False}

        if self.raffles[guild_id]["active"]:
            await ctx.send("> There is already an ongoing raffle in this guild.")
            return

        if amount <= 0 or duration <= 0:
            await ctx.send("> Please provide a valid amount and duration.")
            return

        self.raffles[guild_id]["active"] = True
        self.raffles[guild_id]["amount"] = amount
        self.raffles[guild_id]["end_time"] = time.time() + duration
        self.raffles[guild_id]["participants"] = []

        await ctx.send(f"A raffle for {amount} points has been created. Type /join to participate!")

        while time.time() < self.raffles[guild_id]["end_time"]:
            await asyncio.sleep(1)

        await self.end_raffle(ctx, guild_id)

    async def end_raffle(self, ctx, guild_id):
        if not self.raffles[guild_id]["active"]:
            return

        self.raffles[guild_id]["active"] = False

        if not self.raffles[guild_id]["participants"]:
            await ctx.send("No one participated in the raffle. Better luck next time!")
            return

        winner = random.choice(self.raffles[guild_id]["participants"])
        user_id = str(winner.id)

        if user_id not in self.points_data[guild_id]:
            self.points_data[guild_id][user_id] = 0

        self.points_data[guild_id][user_id] += self.raffles[guild_id]["amount"]

        with open(self.points_file, "w") as f:
            json.dump(self.points_data, f)

        await ctx.send(f"{winner.display_name} won the raffle and got {self.raffles[guild_id]['amount']} points!")

    @cog_ext.cog_slash(name="join", description="Join the ongoing raffle in that guild")
    async def join_raffle(self, ctx: SlashContext):
        guild_id = str(ctx.guild.id)

        if guild_id not in self.raffles:
            await ctx.send("> There is no ongoing raffle in this server.")
            return

        raffle = self.raffles[guild_id]

        if ctx.author in raffle["participants"]:
            await ctx.send("> You have already joined the raffle.")
            return

        raffle["participants"].append(ctx.author)
        await ctx.send(f"> {ctx.author.display_name} has joined the raffle.")


def setup(bot):
    bot.add_cog(Points(bot))
