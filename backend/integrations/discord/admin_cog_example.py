import discord
from discord import app_commands, Interaction
from discord.ext import commands

from integrations.discord.permissions import require_admin, require_bot_owner


class AdminCommands(commands.GroupCog, name="admin"):
    """Admin command group for bot management and monitoring"""

    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="stats", description="Display bot statistics")
    @require_admin
    async def stats(self, interaction: Interaction):
        """Show bot stats like server count and latency."""
        try:
            # Gather stats
            guild_count = len(self.bot.guilds)
            total_members = sum(guild.member_count for guild in self.bot.guilds)

            embed = discord.Embed(
                title="Bot Statistics",
                color=discord.Color.blue()
            )
            embed.add_field(name="Servers", value=str(guild_count), inline=True)
            embed.add_field(name="Total Members", value=str(total_members), inline=True)
            embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(
                f"Error gathering statistics: {str(e)}",
                ephemeral=True
            )
            raise  # Re-raise for logging

    @app_commands.command(name="test", description="Test admin command with parameters")
    @require_admin
    async def test(
        self,
        interaction: Interaction,
        message: str,
        count: int = 1
    ):
        """Test command to verify parameter logging works correctly."""
        await interaction.response.send_message(
            f"Test executed! Message: {message}, Count: {count}",
            ephemeral=True
        )

    @app_commands.command(name="owner_only", description="Bot owner only command")
    @require_bot_owner
    async def owner_only(self, interaction: Interaction):
        """Example command restricted to bot owner only."""
        await interaction.response.send_message(
            "This command can only be run by the bot owner!",
            ephemeral=True
        )


async def setup(bot):
    """Register admin commands cog."""
    await bot.add_cog(AdminCommands(bot))
