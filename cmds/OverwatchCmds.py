import discord
import requests
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.context import SlashContext
from discord_slash.utils.manage_commands import create_option


class Overwatch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(name="overwatch", description="Get Overwatch player information",
                       options=[
                           create_option(
                               name="player",
                               description="The player's battle-tag",
                               option_type=3,
                               required=True
                           ),
                           create_option(
                               name="hero",
                               description="The specific hero to look up for this player",
                               option_type=3,
                               required=False
                           )
                       ])
    async def overwatch(self, ctx: SlashContext, player: str, hero: str = None):
        # Create the API URL based on whether or not the hero parameter was provided
        player = player.replace("#", "-")
        if hero is None:
            api_url = f"https://ow-api.com/v1/stats/pc/us/{player}/complete"
        else:
            api_url = f"https://ow-api.com/v1/stats/pc/us/{player}/heroes/{hero}"

        # Make a GET request to the Overwatch API with the constructed URL
        response = requests.get(api_url)

        if response.status_code == 200:
            # If the request was successful, extract the player's ranks from the response JSON
            data = response.json()

            if data["ratings"] is not None:
                ratings = data["ratings"]
                icon_url = data["icon"]
                endorsement_level = data["endorsement"]
                # endorsement_icon_url = data["endorsementIcon"] broken?
                embed = discord.Embed(title=f"{data['name']}'s Competitive Overwatch Stats")
                embed.set_thumbnail(url=icon_url)

                # check for hero flag
                if hero is None:
                    # Create an embed message with the player's stats and ranks
                    embed.add_field(name="Games Won", value=f"{data['competitiveStats']['games']['won']}", inline=True)
                    embed.add_field(name="Games Played", value=f"{data['competitiveStats']['games']['played']}",
                                    inline=False)
                    for rank in ratings:
                        role = str(rank["role"])
                        embed.add_field(name=f"{role.capitalize()}", value=f"{rank['group']} {rank['tier']}",
                                        inline=True)
                else:
                    # Create an embed message with the player's hero stats
                    embed.add_field(name=f"{str(hero).capitalize()} Stats",
                                    value=f"Coming soon... Outdated Season 3 Stats")

                # Send the embed message back to the user
                embed.set_footer(text=f"Endorsement Level: {endorsement_level}")
                await ctx.send(embed=embed)
            else:
                await ctx.send("> Player's profile is set to private. To use this command, the player's profile "
                               "must be set to public on Overwatch.")
        else:
            # If the request failed, send an error message to the user
            await ctx.send("> Could not retrieve player information, double check you are using the player's "
                           "case-sensitive battletag: Name#1234")


def setup(bot):
    bot.add_cog(Overwatch(bot))
