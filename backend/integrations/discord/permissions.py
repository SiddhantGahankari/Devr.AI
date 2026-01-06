from functools import wraps
from typing import Optional, Tuple
import discord
from discord import Interaction
import logging

from backend.app.core.config.settings import settings

logger = logging.getLogger(__name__)


def is_bot_owner(user_id: int) -> bool:
    return settings.bot_owner_id is not None and user_id == settings.bot_owner_id


def is_admin(interaction: Interaction) -> bool:
    if not interaction.guild:
        return False
    member = interaction.guild.get_member(interaction.user.id)
    if not member:
        return False
    return member.guild_permissions.administrator


def get_permission_embed(
    title: str = "❌ Permission Denied",
    description: str = "You don't have permission to use this command.",
    required_permission: str = "Administrator or Bot Owner"
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.red()
    )
    embed.add_field(name="Required Permission", value=required_permission, inline=False)
    embed.add_field(name="Contact", value="Contact the bot owner if you believe this is an error.", inline=False)
    return embed


def require_admin(func):
    @wraps(func)
    async def wrapper(self, interaction: Interaction, *args, **kwargs):
        has_permission, reason = check_permissions(interaction)

        if not has_permission:
            logger.warning(
                f"Admin command denied: user={interaction.user.id} "
                f"command={interaction.command.name if interaction.command else 'unknown'} "
                f"reason={reason}"
            )

            embed = get_permission_embed()

            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            return None

        logger.info(
            f"Admin command authorized: user={interaction.user.id} "
            f"is_owner={is_bot_owner(interaction.user.id)} "
            f"command={interaction.command.name if interaction.command else 'unknown'}"
        )

        return await func(self, interaction, *args, **kwargs)

    return wrapper


def require_bot_owner(func):
    @wraps(func)
    async def wrapper(self, interaction: Interaction, *args, **kwargs):
        if not is_bot_owner(interaction.user.id):
            logger.warning(
                f"Bot owner command denied: user={interaction.user.id} "
                f"command={interaction.command.name if interaction.command else 'unknown'}"
            )

            embed = get_permission_embed(
                title="❌ Bot Owner Only",
                description="This command can only be used by the bot owner.",
                required_permission="Bot Owner"
            )

            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            return None

        logger.info(
            f"Bot owner command authorized: user={interaction.user.id} "
            f"command={interaction.command.name if interaction.command else 'unknown'}"
        )

        return await func(self, interaction, *args, **kwargs)

    return wrapper


def check_permissions(interaction: Interaction) -> Tuple[bool, Optional[str]]:
    if is_bot_owner(interaction.user.id):
        return True, None

    if is_admin(interaction):
        return True, None

    return False, f"User {interaction.user.id} is neither bot owner nor server administrator"
