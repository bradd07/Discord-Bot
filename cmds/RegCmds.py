import discord
import random
import pytz
from discord import NotFound, Forbidden, HTTPException
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.context import SlashContext
from discord_slash.utils.manage_commands import create_option
from datetime import datetime

"""
Cog for "regular" commands, such as basic utility actions.
Author: bradd07
"""


class RegCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(name="ping", description="Ping the bot to check if it's online")
    async def ping(self, ctx: SlashContext):
        await ctx.send("Pong!")

    @cog_ext.cog_slash(name="avatar", description="Displays the user's avatar")
    async def avatar(self, ctx: SlashContext, user: discord.User = None):
        # if they did not provide a user, assume they want their own avatar
        if user is None:
            user = ctx.author

        # send the user's avatar URL to the channel
        message = discord.Embed(title=user)
        message.set_image(url=user.avatar_url)
        await ctx.send(embed=message)

    @cog_ext.cog_slash(
        name="purge",
        description="Delete a number of messages (limit 50)",
        options=[
            create_option(
                name="count",
                description="Number of messages to delete",
                option_type=4,
                required=True
            )
        ]
    )
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx: SlashContext, num_messages: int):
        # limit the number of messages to delete to 50
        num_messages = min(num_messages, 50)

        # check for negative or zero
        if num_messages <= 0:
            await ctx.send("> Please specify a positive number of messages to delete.", hidden=True)
            return

        # catch any discord errors
        try:
            # bulk delete
            await ctx.channel.purge(limit=num_messages)
            await ctx.send(f"Successfully purged {num_messages} messages.", hidden=True)
        except (NotFound, Forbidden, HTTPException):
            # Catch exceptions if the bot cannot delete messages due to permissions or messages being older than 14 days
            await ctx.send(
                "> Failed to purge all messages. Make sure the bot has the necessary permissions, the messages are not "
                "older than 14 days, or try a smaller number at a time.", hidden=True)

    @cog_ext.cog_subcommand(
        base="poll",
        name="create",
        description="Start a poll with up to 10 choices",
        options=[
            create_option(
                name="message",
                description="Message for the poll",
                option_type=3,
                required=True
            ),
            create_option(
                name="choice1",
                description="Choice 1",
                option_type=3,
                required=True
            ),
            create_option(
                name="choice2",
                description="Choice 2",
                option_type=3,
                required=True
            ),
            *[create_option(
                name=f"choice{i}",
                description=f"Choice {i}",
                option_type=3,
                required=False
            ) for i in range(3, 11)]
        ]
    )
    @commands.has_permissions(manage_guild=True)
    async def create_poll(self, ctx: SlashContext, message, **choices):
        # check if at least two choices are provided (shouldn't happen)
        num_choices = sum(1 for choice in choices.values() if choice is not None)
        if num_choices < 2:
            await ctx.send("Please provide at least two choices for the poll.", hidden=True)
            return

        # get current time
        mst_timezone = pytz.timezone('America/Phoenix')
        current_time = datetime.now(tz=mst_timezone)

        # create the poll message
        poll_message = ""
        emoji_list = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

        for i, choice in enumerate(choices.values(), start=1):
            if choice:
                poll_message += f"{emoji_list[i-1]}: {choice}\n"

        # create the embed
        embed = discord.Embed(
            title=f"**{message}**",
            color=discord.Color.dark_blue(),
            description=poll_message
        )
        embed.set_footer(text=f"Poll created by {ctx.author.display_name} • {current_time.strftime('%m/%d/%Y %I:%M %p')}")

        # Send the poll message
        await ctx.send("> :white_check_mark: Poll created.", hidden=True)
        poll = await ctx.send(embed=embed)

        # Add emoji reactions
        for i in range(num_choices):
            await poll.add_reaction(emoji_list[i])

    @cog_ext.cog_slash(name="8ball", description="Ask the magic 8-ball a question")
    async def eight_ball(self, ctx: SlashContext, *, question: str):
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


def setup(bot):
    bot.add_cog(RegCommands(bot))
