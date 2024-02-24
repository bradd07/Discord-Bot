import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option
import json
import os


class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reaction_roles_dir = "ReactionRoles"

        # Ensure ReactionRoles directory exists
        if not os.path.exists(self.reaction_roles_dir):
            os.makedirs(self.reaction_roles_dir)

    @cog_ext.cog_subcommand(
        base="reactionrole",
        name="add",
        description="Add a reaction role to a message",
        options=[
            create_option(
                name="emoji",
                description="The emoji to add as the reaction",
                option_type=3,
                required=True
            ),
            create_option(
                name="role",
                description="The role to give for the reaction",
                option_type=8,
                required=True
            ),
            create_option(
                name="message_id",
                description="The message ID of the message on which the reaction will be added",
                option_type=3,
                required=True
            )
        ]
    )
    @commands.has_permissions(manage_guild=True)
    async def add_reaction_role(self, ctx: SlashContext, emoji: str, role: discord.Role, message_id: int):
        await ctx.defer(hidden=True)
        guild_id = str(ctx.guild.id)
        # Load existing reaction roles data or create a new dictionary
        try:
            with open(f"{self.reaction_roles_dir}/{guild_id}.json", "r") as file:
                reaction_roles = json.load(file)
        except FileNotFoundError:
            reaction_roles = {}

        # Get the message object from the message ID
        try:
            message = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            await ctx.send("> The specified message does not exist for this channel. (hint: use this command in the "
                           "same channel as the message!)", hidden=True)
            return

        # Check if the emoji is already a reaction to the message
        if message_id in reaction_roles:
            for reaction_role in reaction_roles[str(message_id)]:
                if reaction_role["emoji"] == emoji:
                    old_role = ctx.guild.get_role(int(reaction_role["role_id"]))
                    if old_role:
                        if old_role == role:
                            await ctx.send("> The specified emoji is already assigned to the same role!", hidden=True)
                            return
                        else:
                            # remove old role from dictionary
                            await message.clear_reaction(emoji)
                            reaction_roles[str(message_id)].remove(reaction_role)

        # Add the reaction to the message
        # Get the message object from the message ID
        try:
            await message.add_reaction(emoji)
        except discord.NotFound:
            await ctx.send("> The specified emoji does not exist for this server.", hidden=True)
            return

        # Append the new reaction role to the existing ones for this message
        message_id = str(message_id)
        if message_id not in reaction_roles:
            reaction_roles[message_id] = []
        reaction_roles[message_id].append({"emoji": emoji, "role_id": str(role.id)})

        # Save the updated reaction role data
        with open(f"{self.reaction_roles_dir}/{guild_id}.json", "w") as file:
            json.dump(reaction_roles, file)

        await ctx.send("> The reaction role has been successfully added!", hidden=True)

    @cog_ext.cog_subcommand(
        base="reactionrole",
        name="remove",
        description="Remove a reaction role from a message",
        options=[
            create_option(
                name="emoji",
                description="The emoji to remove",
                option_type=3,
                required=True
            ),
            create_option(
                name="message_id",
                description="The message ID of the message on which the reaction will be removed",
                option_type=3,
                required=True
            )
        ]
    )
    @commands.has_permissions(manage_guild=True)
    async def remove_reaction_role(self, ctx: SlashContext, emoji: str, message_id: int):
        await ctx.defer(hidden=True)
        guild_id = str(ctx.guild.id)
        # Load existing reaction roles data or return if file not found
        try:
            with open(f"{self.reaction_roles_dir}/{guild_id}.json", "r") as file:
                reaction_roles = json.load(file)
        except FileNotFoundError:
            await ctx.send("> No reaction roles found for this server.", hidden=True)
            return

        # Get the message object from the message ID
        try:
            message = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            await ctx.send("> The specified message does not exist for this channel. (hint: use this command in the "
                           "same channel as the message!)", hidden=True)
            return

        # Check if the message has any reaction roles associated with it
        if message_id not in reaction_roles:
            await ctx.send("> No reaction roles found for the specified message.", hidden=True)
            return

        # Check if the specified emoji is a reaction to the message
        for reaction_role in reaction_roles[message_id]:
            if reaction_role["emoji"] == emoji:
                # Remove the reaction from the message
                await message.clear_reaction(emoji)
                # Remove the reaction role from the list
                reaction_roles[message_id].remove(reaction_role)
                break
        else:
            await ctx.send("> The specified emoji is not assigned to any role for this message.", hidden=True)
            return

        # Save the updated reaction role data
        with open(f"{self.reaction_roles_dir}/{guild_id}.json", "w") as file:
            json.dump(reaction_roles, file)

        await ctx.send("> The reaction role has been successfully removed!", hidden=True)

    @cog_ext.cog_subcommand(
        base="reactionrole",
        name="clear",
        description="Clear all reaction roles from a message",
        options=[
            create_option(
                name="message_id",
                description="The message ID of the message on which the reactions will be cleared",
                option_type=3,
                required=True
            )
        ]
    )
    @commands.has_permissions(manage_guild=True)
    async def clear_reaction_roles(self, ctx: SlashContext, message_id: int):
        await ctx.defer(hidden=True)
        guild_id = str(ctx.guild.id)
        # Load existing reaction roles data or return if file not found
        try:
            with open(f"{self.reaction_roles_dir}/{guild_id}.json", "r") as file:
                reaction_roles = json.load(file)
        except FileNotFoundError:
            await ctx.send("> No reaction roles found for this guild.", hidden=True)
            return

        # Get the message object from the message ID
        try:
            message = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            await ctx.send("> The specified message does not exist for this channel. (hint: use this command in the "
                           "same channel as the message!)", hidden=True)
            return

        # Check if the message has any reaction roles associated with it
        if message_id not in reaction_roles:
            await ctx.send("> No reaction roles found for the specified message.", hidden=True)
            return

        # Remove all reactions from the message
        await message.clear_reactions()

        # Remove all reaction roles associated with the message
        del reaction_roles[message_id]

        # Save the updated reaction role data
        with open(f"{self.reaction_roles_dir}/{guild_id}.json", "w") as file:
            json.dump(reaction_roles, file)

        await ctx.send("> The reaction role(s) have been successfully cleared!", hidden=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member.bot:
            return

        guild_id = str(payload.guild_id)
        try:
            with open(f"{self.reaction_roles_dir}/{guild_id}.json", "r") as file:
                reaction_roles = json.load(file)
        except FileNotFoundError:
            return

        message_id = str(payload.message_id)
        if message_id not in reaction_roles:
            return

        for reaction_role in reaction_roles[message_id]:
            if str(payload.emoji) == reaction_role["emoji"]:
                guild = self.bot.get_guild(payload.guild_id)
                role = guild.get_role(int(reaction_role["role_id"]))
                if role:
                    await payload.member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        guild_id = str(payload.guild_id)
        try:
            with open(f"{self.reaction_roles_dir}/{guild_id}.json", "r") as file:
                reaction_roles = json.load(file)
        except FileNotFoundError:
            return

        message_id = str(payload.message_id)
        if message_id not in reaction_roles:
            return

        for reaction_role in reaction_roles[message_id]:
            if str(payload.emoji) == reaction_role["emoji"]:
                guild = self.bot.get_guild(payload.guild_id)
                role = guild.get_role(int(reaction_role["role_id"]))
                if role:
                    member = guild.get_member(payload.user_id)
                    if member:
                        await member.remove_roles(role)


def setup(bot):
    bot.add_cog(ReactionRoles(bot))
