"""Permission management system for Discord bot admin commands."""

import logging
from functools import wraps
from typing import Callable, Optional

import discord
from discord import app_commands, Interaction

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


def is_bot_owner(user_id: int) -> bool:
    """Check if a user is the bot owner."""
    if not settings.bot_owner_id:
        logger.warning("BOT_OWNER_ID not configured - owner checks will fail")
        return False
    return user_id == settings.bot_owner_id


def is_admin(interaction: Interaction) -> bool:
    """Check if a user has administrator permissions in the guild."""
    if not interaction.guild:
        logger.debug(f"Admin check failed for user {interaction.user.id}: No guild context")
        return False

    member = interaction.guild.get_member(interaction.user.id)
    if not member:
        logger.debug(f"Admin check failed for user {interaction.user.id}: Member not found in guild")
        return False

    return member.guild_permissions.administrator


def get_permission_embed(
    title: str = "❌ Permission Denied",
    description: str = "You don't have permission to use this command.",
    required_permission: str = "Administrator or Bot Owner"
) -> discord.Embed:
    """Create a standardized permission denied embed."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.red()
    )
    embed.add_field(
        name="Required Permission",
        value=f"`{required_permission}`",
        inline=False
    )
    embed.add_field(
        name="💡 Need Access?",
        value="Contact your server administrator or the bot owner.",
        inline=False
    )
    embed.set_footer(text="This action has been logged for security purposes.")
    return embed


def require_admin(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(self, interaction: Interaction, *args, **kwargs):
        user_id = interaction.user.id
        command_name = interaction.command.name if interaction.command else "unknown"

        # Check if user is bot owner
        if is_bot_owner(user_id):
            logger.info(
                f"Admin command authorized: user={user_id} (BOT OWNER), "
                f"command=/{command_name}"
            )
            return await func(self, interaction, *args, **kwargs)

        # Check if user is administrator in guild
        if is_admin(interaction):
            logger.info(
                f"Admin command authorized: user={user_id} (ADMINISTRATOR), "
                f"command=/{command_name}, guild={interaction.guild_id}"
            )
            return await func(self, interaction, *args, **kwargs)

        # Permission denied
        logger.warning(
            f"Admin command denied: user={user_id}, command=/{command_name}, "
            f"guild={interaction.guild_id}, reason=insufficient_permissions"
        )

        embed = get_permission_embed(
            description="This command is restricted to server administrators and the bot owner.",
            required_permission="Administrator or Bot Owner"
        )

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

        return None

    return wrapper


def require_bot_owner(func: Callable) -> Callable:
    """Decorator to restrict command access to bot owner only."""
    @wraps(func)
    async def wrapper(self, interaction: Interaction, *args, **kwargs):
        user_id = interaction.user.id
        command_name = interaction.command.name if interaction.command else "unknown"

        # Check if user is bot owner
        if is_bot_owner(user_id):
            logger.info(
                f"Owner command authorized: user={user_id}, command=/{command_name}"
            )
            return await func(self, interaction, *args, **kwargs)

        # Permission denied
        logger.warning(
            f"Owner command denied: user={user_id}, command=/{command_name}, "
            f"guild={interaction.guild_id}, reason=not_bot_owner"
        )

        embed = get_permission_embed(
            title="❌ Bot Owner Only",
            description="This command is restricted to the bot owner only.",
            required_permission="Bot Owner"
        )

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

        return None

    return wrapper


def check_permissions(interaction: Interaction) -> tuple[bool, Optional[str]]:
    """Check user permissions and return status with reason."""
    user_id = interaction.user.id

    # Check bot owner
    if is_bot_owner(user_id):
        return True, None

    # Check administrator
    if is_admin(interaction):
        return True, None

    # Permission denied
    return False, "User is neither bot owner nor server administrator"
