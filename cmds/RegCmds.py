import discord
import random
import pytz
from typing import Optional
from discord import NotFound, Forbidden, HTTPException
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from datetime import datetime

"""
Cog for "regular" commands, such as basic utility actions.
Author: bradd07
"""


class RegCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ping", description="Ping the bot to check if it's online")
    async def ping(self, ctx: Context):
        await ctx.send("Pong!")

    @commands.hybrid_command(name="avatar", description="Displays the user's avatar")
    async def avatar(self, ctx: Context, user: discord.User = None):
        # if they did not provide a user, assume they want their own avatar
        if user is None:
            user = ctx.author

        # send the user's avatar URL to the channel
        message = discord.Embed(title=user)
        message.set_image(url=user.avatar.url)
        await ctx.send(embed=message)

    @commands.hybrid_command(name="purge", description="Delete a number of messages (limit 50)")
    @app_commands.describe(num_messages="Number of messages to delete (default 10)")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx: Context, num_messages: Optional[int]):
        # set default parameters if not set
        if num_messages is None:
            num_messages = 10

        # limit the number of messages to delete to 50
        num_messages = min(num_messages, 50)

        # check for negative or zero
        if num_messages <= 0:
            await ctx.send("> Please specify a positive number of messages to delete.", ephemeral=True)
            return

        # catch any discord errors
        try:
            # bulk delete
            await ctx.defer(ephemeral=True)
            await ctx.channel.purge(limit=num_messages)
            await ctx.send(f"Successfully purged {num_messages} messages.", ephemeral=True)
        except (NotFound, Forbidden, HTTPException):
            # Catch exceptions if the bot cannot delete messages due to permissions or messages being older than 14 days
            await ctx.send(
                "> Failed to purge all messages. Make sure the bot has the necessary permissions, the messages are not "
                "older than 14 days, or try a smaller number at a time.", ephemeral=True)

    # default /poll command, does nothing without sub-parameter
    @commands.hybrid_group(name="poll", description="Start a poll!")
    @commands.has_permissions(manage_guild=True)
    async def poll(self, ctx: Context):
        return

    @poll.command(name="create", description="Start a poll!")
    @commands.has_permissions(manage_guild=True)
    async def create_poll(self, ctx: Context, message: str, choice1: str, choice2: str,
                          choice3: Optional[str], choice4: Optional[str], choice5: Optional[str]):
        # check if at least two choices are provided (shouldn't happen)
        choices = [choice1, choice2, choice3, choice4, choice5]
        # filter out None choices
        choices = [choice for choice in choices if choice]
        if len(choices) < 2:
            await ctx.send("Please provide at least two choices for the poll.", ephemeral=True)
            return

        # create the poll message
        emoji_list = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        poll_message = "\n".join(f"{emoji}: {choice}" for emoji, choice in zip(emoji_list, choices) if choice)

        embed = discord.Embed(
            title=f"**{message}**",
            color=discord.Color.dark_blue(),
            description=poll_message
        )
        embed.timestamp = datetime.now()
        embed.set_footer(
            text=f"Poll created by {ctx.author.display_name}")

        await ctx.send("> :white_check_mark: Poll created.", ephemeral=True)
        poll = await ctx.send(embed=embed)

        for emoji in emoji_list[:len(choices)]:
            await poll.add_reaction(emoji)

    @commands.hybrid_command(name="8ball", description="Ask the magic 8-ball a question")
    async def eight_ball(self, ctx: Context, question: str):
        # come up with some responses
        responses = [
            "It is certain",
            "It is decidedly so",
            "Without a doubt",
            "Yes, definitely",
            "You may rely on it",
            "As I see it, yes",
            "Most likely",
            "Outlook good",
            "Yes",
            "Signs point to yes",
            "Reply hazy, try again",
            "Ask again later",
            "Better not tell you now",
            "Cannot predict now",
            "Concentrate and ask again",
            "Don't count on it",
            "Outlook not so good",
            "My sources say no",
            "Very doubtful"
        ]
        # send a random response
        await ctx.send(f"> {question}\n:8ball: {random.choice(responses)}")


async def setup(bot):
    await bot.add_cog(RegCommands(bot))
