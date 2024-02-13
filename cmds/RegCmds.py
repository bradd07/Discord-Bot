import discord
import random
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.context import SlashContext


class RegCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(name="ping", description="Ping the bot to check if it's online")
    async def ping(self, ctx: SlashContext):
        await ctx.send("Pong!")

    @cog_ext.cog_slash(name="avatar", description="Displays the user's avatar")
    async def avatar(self, ctx: SlashContext, user: discord.User = None):
        if user is None:
            user = ctx.author

        # Send the user's avatar URL to the channel
        message = discord.Embed(title=user)
        message.set_image(url=user.avatar_url)
        await ctx.send(embed=message)

    @cog_ext.cog_slash(name="8ball", description="Ask the magic 8-ball a question")
    async def eight_ball(self, ctx: SlashContext, *, question: str):
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
        await ctx.send(f"> {question}\n:8ball: {random.choice(responses)}")


def setup(bot):
    bot.add_cog(RegCommands(bot))
