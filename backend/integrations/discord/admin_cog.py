import logging
import discord
from discord import app_commands, Interaction
from discord.ext import commands

from integrations.discord.bot import DiscordBot
from integrations.discord.permissions import require_admin
from app.core.orchestration.queue_manager import AsyncQueueManager

logger = logging.getLogger(__name__)


class AdminCommands(commands.GroupCog, name="admin"):
    """Bot management and monitoring commands"""

    def __init__(self, bot: DiscordBot, queue_manager: AsyncQueueManager):
        self.bot = bot
        self.queue = queue_manager
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
            guild_count = len(self.bot.guilds)
            total_members = sum(guild.member_count or 0 for guild in self.bot.guilds)
            active_threads = len(self.bot.active_threads)

            embed = discord.Embed(title="Bot Statistics", color=discord.Color.blue())
            embed.add_field(name="Servers", value=str(guild_count), inline=True)
            embed.add_field(name="Total Members", value=str(total_members), inline=True)
            embed.add_field(name="Active Threads", value=str(active_threads), inline=True)
            embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
            embed.set_footer(text="More detailed stats coming soon")

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
            # TODO: Add actual health checks for Supabase, Weaviate, RabbitMQ, etc
            embed = discord.Embed(title="System Health", color=discord.Color.green())
            embed.add_field(name="Discord API", value="Healthy", inline=True)
            embed.add_field(name="Bot Status", value="Running", inline=True)
            embed.set_footer(text="Full service checks coming in next update")

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
            created = user.created_at.strftime("%Y-%m-%d")

            embed = discord.Embed(title="User Information", color=discord.Color.blue())
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(name="Username", value=user.name, inline=True)
            embed.add_field(name="ID", value=str(user.id), inline=True)
            embed.add_field(name="Created", value=created, inline=True)

            if member:
                embed.add_field(name="Nickname", value=member.display_name or "None", inline=True)
                embed.add_field(name="Roles", value=str(len(member.roles) - 1), inline=True)

            # TODO: Add verification status, message count, etc from database
            embed.set_footer(text="More details coming soon")

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
            # TODO: Implement actual reset logic with confirmation dialog
            actions = []
            if reset_memory:
                actions.append("memory")
            if reset_thread:
                actions.append("thread")
            if reset_verification:
                actions.append("verification")

            embed = discord.Embed(
                title="User Reset",
                description=f"Would reset {', '.join(actions)} for {user.mention}",
                color=discord.Color.orange()
            )
            embed.set_footer(text="Need to add confirmation dialog first")

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
            # TODO: Get actual queue stats from RabbitMQ
            embed = discord.Embed(title="Queue Status", color=discord.Color.blue())
            embed.add_field(name="High", value="0 pending", inline=True)
            embed.add_field(name="Medium", value="0 pending", inline=True)
            embed.add_field(name="Low", value="0 pending", inline=True)
            embed.set_footer(text="Need to wire up RabbitMQ stats")

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
            # TODO: Add confirmation buttons before actually clearing
            embed = discord.Embed(
                title="Queue Clear",
                description=f"This would clear {priority} priority queue(s).",
                color=discord.Color.orange()
            )
            embed.add_field(name="Warning", value="Can't undo this. Need confirmation dialog first.", inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Queue clear failed: {e}", exc_info=True)
            await interaction.followup.send(f"Clear failed: {str(e)}", ephemeral=True)

    @app_commands.command(name="cache_clear", description="Clear cached data")
    @app_commands.describe(cache_type="What to clear")
    @app_commands.choices(cache_type=[
        app_commands.Choice(name="All", value="all"),
        app_commands.Choice(name="Embeddings", value="embeddings"),
        app_commands.Choice(name="Memories", value="memories")
    ])
    @require_admin
    async def cache_clear(self, interaction: Interaction, cache_type: str = "all"):
        """Clear various caches."""
        await interaction.response.defer(ephemeral=True)

        try:
            # TODO: Implement actual cache clearing
            embed = discord.Embed(
                title="Cache Clear",
                description=f"Would clear {cache_type} cache.",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Still need to implement this")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Cache clear failed: {e}", exc_info=True)
            await interaction.followup.send(f"Clear failed: {str(e)}", ephemeral=True)


async def setup(bot: DiscordBot):
    """Register the admin cog."""
    await bot.add_cog(AdminCommands(bot, bot.queue_manager))
