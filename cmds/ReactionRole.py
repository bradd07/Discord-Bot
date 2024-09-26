import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
import json
import os

"""
Cog for reaction role commands. Allows admins to dedicate a message that assigns roles to users when reacted to with 
a specified Discord emoji.
Author: bradd07
"""


# fetches a Discord message object from a given message ID
async def get_message(ctx: Context, message_id: int):
    try:
        return await ctx.channel.fetch_message(message_id)
    except discord.NotFound:
        return None


class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reaction_roles_dir = "ReactionRoles"

        # ensure ReactionRoles directory exists
        if not os.path.exists(self.reaction_roles_dir):
            os.makedirs(self.reaction_roles_dir)

    # loads the reaction roles and verifies if the message exists and has roles associated with it.
    async def load_and_verify(self, ctx: Context, guild_id: str, message_id: int):
        # load existing reaction roles data or return if file not found
        try:
            with open(f"{self.reaction_roles_dir}/{guild_id}.json", "r") as file:
                reaction_roles = json.load(file)
        except FileNotFoundError:
            await ctx.send("> No reaction roles found for this server.", ephemeral=True)
            return None, None

        # get the message object from the message ID
        message = await get_message(ctx, message_id)
        if message is None:
            await ctx.send("> That message ID does not exist in this channel. "
                           "(hint: use this command in the same channel as the message!)", ephemeral=True)
            return None, None

        # check if the message has any reaction roles associated with it
        if message_id not in reaction_roles:
            await ctx.send("> No reaction roles found for that message ID.", ephemeral=True)
            return None, None

        return reaction_roles, message

    # saves the updated reaction roles data for the given server ID
    async def save_reaction_roles(self, guild_id: str, reaction_roles):
        with open(f"{self.reaction_roles_dir}/{guild_id}.json", "w") as file:
            json.dump(reaction_roles, file)

    # default /reactionrole command, does nothing without sub-parameter
    @commands.hybrid_group(name="reactionrole", description="Manage reaction roles")
    @commands.has_permissions(manage_guild=True)
    async def reaction_role(self, ctx: Context):
        return

    @reaction_role.command(name="add", description="Add a reaction role to a message")
    @app_commands.describe(emoji="The emoji to add as a reaction role",
                           role="The role to give when a user reacts with that emoji",
                           message_id="The message ID in which the reaction role will be added to")
    @commands.has_permissions(manage_guild=True)
    async def add_reaction_role(self, ctx: Context, emoji: str, role: discord.Role, message_id: int):
        await ctx.defer()
        guild_id = str(ctx.guild.id)

        # load existing reaction roles data or create a new dictionary
        try:
            with open(f"{self.reaction_roles_dir}/{guild_id}.json", "r") as file:
                reaction_roles = json.load(file)
        except FileNotFoundError:
            reaction_roles = {}

        # get the message object from the message ID
        message = await get_message(ctx, message_id)
        if message is None:
            await ctx.send("> That message ID does not exist in this channel. "
                           "(hint: use this command in the same channel as the message!)", ephemeral=True)
            return

        # check if the emoji is already a reaction to the message, attempt to overwrite it with new role if so
        if message_id in reaction_roles:
            for reaction_role in reaction_roles[str(message_id)]:
                if reaction_role["emoji"] == emoji:
                    old_role = ctx.guild.get_role(int(reaction_role["role_id"]))
                    if old_role:
                        if old_role == role:
                            await ctx.send("> That emoji is already assigned to this same role!",
                                           ephemeral=True)
                            return
                        else:
                            # remove old role from dictionary
                            await message.clear_reaction(emoji)
                            reaction_roles[str(message_id)].remove(reaction_role)

        # add the reaction to the message
        # get the message object from the message ID
        try:
            await message.add_reaction(emoji)
        except discord.NotFound:
            await ctx.send("> That emoji does not exist in this server!", ephemeral=True)
            return

        # append the new reaction role to the existing ones for this message
        message_id = str(message_id)
        if message_id not in reaction_roles:
            reaction_roles[message_id] = []
        reaction_roles[message_id].append({"emoji": emoji, "role_id": str(role.id)})

        # save the updated reaction role data
        await self.save_reaction_roles(guild_id, reaction_roles)
        await ctx.send("> The reaction role has been successfully added!", ephemeral=True)

    @reaction_role.command(name="remove", description="Remove a reaction role from a message")
    @app_commands.describe(emoji="The emoji to remove",
                           message_id="The message ID in which the reaction role will be removed from")
    @commands.has_permissions(manage_guild=True)
    async def remove_reaction_role(self, ctx: Context, emoji: str, message_id: int):
        await ctx.defer()
        guild_id = str(ctx.guild.id)

        # load and verify reaction roles and message
        reaction_roles, message = await self.load_and_verify(ctx, guild_id, message_id)
        if reaction_roles is None or message is None:
            return

        # check if the specified emoji is a reaction to the message
        for reaction_role in reaction_roles[message_id]:
            if reaction_role["emoji"] == emoji:
                # Remove the reaction from the message
                await message.clear_reaction(emoji)
                # Remove the reaction role from the list
                reaction_roles[message_id].remove(reaction_role)
                break
        else:
            await ctx.send("> That emoji is not assigned to any role for this message!", ephemeral=True)
            return

        # save the updated reaction role data
        await self.save_reaction_roles(guild_id, reaction_roles)
        await ctx.send("> The reaction role has been successfully removed!", ephemeral=True)

    @reaction_role.command(name="clear", description="Clear all reactions from a message")
    @app_commands.describe(message_id="The message ID in which the reaction role will be added to")
    @commands.has_permissions(manage_guild=True)
    async def clear_reaction_roles(self, ctx: Context, message_id: int):
        await ctx.defer()
        guild_id = str(ctx.guild.id)

        # load and verify reaction roles and message
        reaction_roles, message = await self.load_and_verify(ctx, guild_id, message_id)
        if reaction_roles is None or message is None:
            return

        # remove all reactions from the message
        await message.clear_reactions()

        # remove all reaction roles associated with the message
        del reaction_roles[message_id]

        # save the updated reaction role data
        await self.save_reaction_roles(guild_id, reaction_roles)
        await ctx.send("> The reaction role(s) have been successfully cleared!", ephemeral=True)

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


async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
