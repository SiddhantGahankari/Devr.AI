import logging
import discord
from discord import app_commands, Interaction
from discord.ext import commands

from integrations.discord.bot import DiscordBot
from integrations.discord.permissions import require_admin
from app.core.orchestration.queue_manager import AsyncQueueManager
from app.services.admin import (
    BotStatsService,
    HealthCheckService,
    UserInfoService,
    QueueService,
    CacheService,
    UserManagementService,
)

logger = logging.getLogger(__name__)


class AdminCommands(commands.GroupCog, name="admin"):
    """Bot management and monitoring commands"""

    def __init__(self, bot: DiscordBot, queue_manager: AsyncQueueManager):
        self.bot = bot
        self.queue = queue_manager
        self.stats_service = BotStatsService(bot=bot, queue_manager=queue_manager)
        self.health_service = HealthCheckService(queue_manager=queue_manager)
        self.user_info_service = UserInfoService(bot=bot)
        self.queue_service = QueueService(queue_manager=queue_manager)
        self.cache_service = CacheService(bot=bot)
        self.user_management_service = UserManagementService(bot=bot, queue_manager=queue_manager)
        super().__init__()

    async def cog_command_error(self, interaction: Interaction, error: Exception):
        """Handle errors for admin commands."""
        logger.error(f"Admin command error: {error}", exc_info=True)

        if isinstance(error, app_commands.MissingPermissions):
            error_message = "You don't have permission to use this command."
        elif isinstance(error, app_commands.CommandInvokeError):
            error_message = f"Command failed: {str(error.original)}"
        else:
            error_message = "Something went wrong executing that command."

        try:
            if interaction.response.is_done():
                await interaction.followup.send(error_message, ephemeral=True)
            else:
                await interaction.response.send_message(error_message, ephemeral=True)
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")

    @app_commands.command(name="stats", description="Display bot statistics and metrics")
    @require_admin
    async def stats(self, interaction: Interaction):
        """Show current bot stats."""
        await interaction.response.defer(ephemeral=True)

        try:
            stats = await self.stats_service.get_all_stats()

            embed = discord.Embed(title="Bot Statistics", color=discord.Color.blue())
            embed.add_field(name="Servers", value=str(stats.guild_count), inline=True)
            embed.add_field(name="Total Members", value=str(stats.total_members), inline=True)
            embed.add_field(name="Active Threads", value=str(stats.active_threads), inline=True)
            embed.add_field(name="Latency", value=f"{stats.latency_ms}ms", inline=True)
            embed.add_field(name="Memory Usage", value=f"{stats.memory_mb} MB", inline=True)
            embed.add_field(name="Uptime", value=f"{int(stats.uptime_seconds)}s", inline=True)
            embed.add_field(name="Messages Today", value=str(stats.messages_today), inline=True)
            embed.add_field(name="Messages (7d)", value=str(stats.messages_week), inline=True)
            embed.add_field(
                name="Queue",
                value=(
                    f"High: {stats.queue_high}\n"
                    f"Medium: {stats.queue_medium}\n"
                    f"Low: {stats.queue_low}"
                ),
                inline=False,
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Stats command failed: {e}", exc_info=True)
            await interaction.followup.send(f"Failed to get stats: {str(e)}", ephemeral=True)

    @app_commands.command(name="health", description="Check system health and service status")
    @require_admin
    async def health(self, interaction: Interaction):
        """Check if all services are running."""
        await interaction.response.defer(ephemeral=True)

        try:
            health = await self.health_service.get_all_health()

            status_color = {
                "healthy": discord.Color.green(),
                "degraded": discord.Color.orange(),
                "unhealthy": discord.Color.red(),
            }
            status_emoji = {
                "healthy": "✅",
                "degraded": "⚠️",
                "unhealthy": "❌",
            }

            embed = discord.Embed(
                title="System Health",
                color=status_color.get(health.overall_status, discord.Color.orange()),
            )
            embed.add_field(
                name="Overall",
                value=f"{status_emoji.get(health.overall_status, '⚠️')} {health.overall_status.title()}",
                inline=False,
            )

            for service in health.services:
                details = f"{service.latency_ms}ms"
                if service.error:
                    details += f"\n{service.error}"
                embed.add_field(
                    name=f"{status_emoji.get(service.status, '⚠️')} {service.name}",
                    value=details,
                    inline=True,
                )

            embed.set_footer(text=f"Checked at {health.timestamp}")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Health check error: {e}", exc_info=True)
            await interaction.followup.send(f"Health check failed: {str(e)}", ephemeral=True)

    @app_commands.command(name="user_info", description="Get info about a user")
    @app_commands.describe(user="User to look up")
    @require_admin
    async def user_info(self, interaction: Interaction, user: discord.User):
        """Look up user details."""
        await interaction.response.defer(ephemeral=True)

        try:
            member = interaction.guild.get_member(user.id) if interaction.guild else None
            info = await self.user_info_service.get_full_user_info(user, member)

            embed = discord.Embed(title="User Information", color=discord.Color.blue())
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(name="Username", value=info.discord_username, inline=True)
            embed.add_field(name="ID", value=info.discord_id, inline=True)
            embed.add_field(name="Created", value=info.created_at, inline=True)
            embed.add_field(name="Verified", value="Yes" if info.is_verified else "No", inline=True)
            embed.add_field(name="GitHub", value=info.github_username or "Not linked", inline=True)
            embed.add_field(name="Messages", value=str(info.message_count), inline=True)
            embed.add_field(name="Active Thread", value="Yes" if info.has_active_thread else "No", inline=True)
            embed.add_field(name="Roles", value=str(info.roles_count), inline=True)
            embed.add_field(name="Last Message", value=info.last_message_at or "Never", inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"User info lookup failed: {e}", exc_info=True)
            await interaction.followup.send(f"Couldn't get user info: {str(e)}", ephemeral=True)

    @app_commands.command(name="user_reset", description="Reset user state")
    @app_commands.describe(
        user="User to reset",
        reset_memory="Clear conversation memory",
        reset_thread="Close active thread",
        reset_verification="Clear GitHub verification"
    )
    @require_admin
    async def user_reset(
        self,
        interaction: Interaction,
        user: discord.User,
        reset_memory: bool = False,
        reset_thread: bool = False,
        reset_verification: bool = False
    ):
        """Reset various aspects of user state."""
        await interaction.response.defer(ephemeral=True)

        if not any([reset_memory, reset_thread, reset_verification]):
            await interaction.followup.send("Select at least one thing to reset.", ephemeral=True)
            return

        try:
            result = await self.user_management_service.reset_user(
                user_id=str(user.id),
                reset_memory=reset_memory,
                reset_thread=reset_thread,
                reset_verification=reset_verification,
            )

            success = len(result.errors) == 0

            embed = discord.Embed(
                title="User Reset Complete" if success else "User Reset Completed with Issues",
                description=f"Target: {user.mention}",
                color=discord.Color.green() if success else discord.Color.orange(),
            )
            embed.add_field(name="Memory Cleared", value="Yes" if result.memory_cleared else "No", inline=True)
            embed.add_field(name="Thread Closed", value="Yes" if result.thread_closed else "No", inline=True)
            embed.add_field(name="Verification Reset", value="Yes" if result.verification_reset else "No", inline=True)

            if result.errors:
                embed.add_field(name="Errors", value="\n".join(result.errors), inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"User reset failed: {e}", exc_info=True)
            await interaction.followup.send(f"Reset failed: {str(e)}", ephemeral=True)

    @app_commands.command(name="queue_status", description="Check queue status")
    @require_admin
    async def queue_status(self, interaction: Interaction):
        """See what's in the queue."""
        await interaction.response.defer(ephemeral=True)

        try:
            status = await self.queue_service.get_queue_stats()

            total = status.total_pending
            if total == 0:
                color = discord.Color.green()
            elif total < 10:
                color = discord.Color.blue()
            elif total < 50:
                color = discord.Color.orange()
            else:
                color = discord.Color.red()

            embed = discord.Embed(title="Queue Status", color=discord.Color.blue())
            embed.color = color
            embed.add_field(
                name="High",
                value=f"{status.high.pending} pending\n{status.high.consumers} consumers",
                inline=True,
            )
            embed.add_field(
                name="Medium",
                value=f"{status.medium.pending} pending\n{status.medium.consumers} consumers",
                inline=True,
            )
            embed.add_field(
                name="Low",
                value=f"{status.low.pending} pending\n{status.low.consumers} consumers",
                inline=True,
            )
            embed.add_field(name="Total Pending", value=str(status.total_pending), inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Queue status check failed: {e}", exc_info=True)
            await interaction.followup.send(f"Couldn't get queue status: {str(e)}", ephemeral=True)

    @app_commands.command(name="queue_clear", description="Clear queue messages")
    @app_commands.describe(priority="Which queue to clear")
    @app_commands.choices(priority=[
        app_commands.Choice(name="All", value="all"),
        app_commands.Choice(name="High", value="high"),
        app_commands.Choice(name="Medium", value="medium"),
        app_commands.Choice(name="Low", value="low")
    ])
    @require_admin
    async def queue_clear(self, interaction: Interaction, priority: str = "all"):
        """Clear stuck messages from queue."""
        await interaction.response.defer(ephemeral=True)

        try:
            cleared = await self.queue_service.clear_queue(priority=priority)
            total = sum(cleared.values())

            embed = discord.Embed(
                title="Queue Cleared",
                description=f"Cleared queue scope: {priority}",
                color=discord.Color.orange(),
            )
            embed.add_field(name="High", value=str(cleared.get("high", 0)), inline=True)
            embed.add_field(name="Medium", value=str(cleared.get("medium", 0)), inline=True)
            embed.add_field(name="Low", value=str(cleared.get("low", 0)), inline=True)
            embed.add_field(name="Total Cleared", value=str(total), inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Queue clear failed: {e}", exc_info=True)
            await interaction.followup.send(f"Clear failed: {str(e)}", ephemeral=True)

    @app_commands.command(name="cache_clear", description="Clear cached data")
    @app_commands.describe(cache_type="What to clear")
    @app_commands.choices(cache_type=[
        app_commands.Choice(name="All", value="all"),
        app_commands.Choice(name="Active Threads", value="active_threads"),
        app_commands.Choice(name="Embeddings", value="embeddings"),
        app_commands.Choice(name="Memories", value="memories")
    ])
    @require_admin
    async def cache_clear(self, interaction: Interaction, cache_type: str = "all"):
        """Clear various caches."""
        await interaction.response.defer(ephemeral=True)

        try:
            cleared = await self.cache_service.clear_cache(cache_type=cache_type)

            embed = discord.Embed(
                title="Cache Clear",
                description=f"Cleared cache type: {cache_type}",
                color=discord.Color.blue(),
            )
            for name, count in cleared.items():
                embed.add_field(name=name.replace("_", " ").title(), value=str(count), inline=True)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Cache clear failed: {e}", exc_info=True)
            await interaction.followup.send(f"Clear failed: {str(e)}", ephemeral=True)


async def setup(bot: DiscordBot):
    """Register the admin cog."""
    await bot.add_cog(AdminCommands(bot, bot.queue_manager))
