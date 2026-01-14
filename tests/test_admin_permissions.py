import sys
from pathlib import Path
import asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))

import discord
from discord import Interaction, Member, Guild, User
from unittest.mock import Mock, AsyncMock, patch

from backend.integrations.discord.permissions import (
    require_admin,
    require_bot_owner,
    get_permission_embed,
)


class MockCog:
    def __init__(self):
        self.bot = Mock()


def create_mock_interaction(user_id=999999999, guild_id=987654321, command_name="test_command", is_admin_user=False):
    interaction = Mock(spec=Interaction)
    interaction.user = Mock(spec=User)
    interaction.user.id = user_id
    interaction.user.name = "test_user"
    
    interaction.guild = Mock(spec=Guild)
    interaction.guild.id = guild_id
    
    member = Mock(spec=Member)
    member.guild_permissions = Mock()
    member.guild_permissions.administrator = is_admin_user
    interaction.guild.get_member = Mock(return_value=member)
    
    interaction.command = Mock()
    interaction.command.name = command_name
    
    interaction.response = Mock()
    interaction.response.is_done = Mock(return_value=False)
    interaction.response.send_message = AsyncMock()
    
    interaction.followup = Mock()
    interaction.followup.send = AsyncMock()
    
    return interaction


async def test_admin_decorator_allows_administrator():
    """Admin decorator should allow users with ADMINISTRATOR permission"""
    with patch("backend.integrations.discord.permissions.settings") as mock_settings, \
         patch("backend.integrations.discord.permissions.log_admin_action", new_callable=AsyncMock):
        
        mock_settings.bot_owner_id = 123456789
        
        interaction = create_mock_interaction(user_id=999999999, is_admin_user=True)
        cog = MockCog()
        
        called = False
        
        @require_admin
        async def test_command(self, interaction: Interaction):
            nonlocal called
            called = True
        
        await test_command(cog, interaction)
        
        assert called, "Command should execute for admin user"
        assert not interaction.response.send_message.called, "Should not send error message"
        print("✓ test_admin_decorator_allows_administrator passed")


async def test_admin_decorator_allows_bot_owner():
    """Bot owner should pass through admin decorator"""
    with patch("backend.integrations.discord.permissions.settings") as mock_settings, \
         patch("backend.integrations.discord.permissions.log_admin_action", new_callable=AsyncMock):
        
        mock_settings.bot_owner_id = 123456789
        
        interaction = create_mock_interaction(user_id=123456789, is_admin_user=False)
        cog = MockCog()
        
        called = False
        
        @require_admin
        async def test_command(self, interaction: Interaction):
            nonlocal called
            called = True
        
        await test_command(cog, interaction)
        
        assert called, "Command should execute for bot owner"
        assert not interaction.response.send_message.called, "Should not send error message"
        print("✓ test_admin_decorator_allows_bot_owner passed")


async def test_admin_decorator_denies_regular_user():
    """Regular users should be denied by admin decorator"""
    with patch("backend.integrations.discord.permissions.settings") as mock_settings, \
         patch("backend.integrations.discord.permissions.log_admin_action", new_callable=AsyncMock):
        
        mock_settings.bot_owner_id = 123456789
        
        interaction = create_mock_interaction(user_id=999999999, is_admin_user=False)
        cog = MockCog()
        
        called = False
        
        @require_admin
        async def test_command(self, interaction: Interaction):
            nonlocal called
            called = True
        
        await test_command(cog, interaction)
        
        assert not called, "Command should not execute"
        assert interaction.response.send_message.called, "Should send error message"
        call_kwargs = interaction.response.send_message.call_args.kwargs
        assert call_kwargs["ephemeral"] is True
        assert isinstance(call_kwargs["embed"], discord.Embed)
        print("✓ test_admin_decorator_denies_regular_user passed")


async def test_bot_owner_decorator_denies_admin():
    """Admin users without bot owner status should be denied"""
    with patch("backend.integrations.discord.permissions.settings") as mock_settings, \
         patch("backend.integrations.discord.permissions.log_admin_action", new_callable=AsyncMock):
        
        mock_settings.bot_owner_id = 123456789
        
        interaction = create_mock_interaction(user_id=999999999, is_admin_user=True)
        cog = MockCog()
        
        called = False
        
        @require_bot_owner
        async def test_command(self, interaction: Interaction):
            nonlocal called
            called = True
        
        await test_command(cog, interaction)
        
        assert not called, "Command should not execute for non-owner"
        assert interaction.response.send_message.called, "Should send error message"
        print("✓ test_bot_owner_decorator_denies_admin passed")


async def test_bot_owner_decorator_allows_owner():
    """Bot owner should pass through bot owner decorator"""
    with patch("backend.integrations.discord.permissions.settings") as mock_settings, \
         patch("backend.integrations.discord.permissions.log_admin_action", new_callable=AsyncMock):
        
        mock_settings.bot_owner_id = 123456789
        
        interaction = create_mock_interaction(user_id=123456789, is_admin_user=False)
        cog = MockCog()
        
        called = False
        
        @require_bot_owner
        async def test_command(self, interaction: Interaction):
            nonlocal called
            called = True
        
        await test_command(cog, interaction)
        
        assert called, "Command should execute for bot owner"
        assert not interaction.response.send_message.called, "Should not send error message"
        print("✓ test_bot_owner_decorator_allows_owner passed")


async def test_permission_check_logging():
    """All permission checks should be logged to database"""
    with patch("backend.integrations.discord.permissions.settings") as mock_settings, \
         patch("backend.integrations.discord.permissions.log_admin_action", new_callable=AsyncMock) as mock_log:
        
        mock_settings.bot_owner_id = 123456789
        
        interaction = create_mock_interaction(user_id=999999999, is_admin_user=False, command_name="stats")
        cog = MockCog()
        
        @require_admin
        async def test_command(self, interaction: Interaction):
            pass
        
        await test_command(cog, interaction)
        
        assert mock_log.called, "Should log permission check"
        call_kwargs = mock_log.call_args.kwargs
        assert call_kwargs["executor_id"] == "999999999"
        assert call_kwargs["command_name"] == "stats"
        assert call_kwargs["action_result"] == "failure"
        assert "Permission denied" in call_kwargs["error_message"]
        print("✓ test_permission_check_logging passed")


def test_error_embed_generation():
    """Error embeds should have helpful messages"""
    embed = get_permission_embed()
    
    assert embed.title == "Permission Denied"
    assert "don't have permission" in embed.description
    assert embed.color == discord.Color.red()
    assert len(embed.fields) >= 2
    
    required_field = embed.fields[0]
    assert required_field.name == "Required Permission"
    assert "Administrator" in required_field.value or "Bot Owner" in required_field.value
    
    contact_field = embed.fields[1]
    assert contact_field.name == "Contact"
    assert "bot owner" in contact_field.value.lower()
    print("✓ test_error_embed_generation passed")


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("Running Admin Permissions Tests")
    print("="*60 + "\n")
    
    tests_passed = 0
    tests_failed = 0
    
    test_functions = [
        test_admin_decorator_allows_administrator,
        test_admin_decorator_allows_bot_owner,
        test_admin_decorator_denies_regular_user,
        test_bot_owner_decorator_denies_admin,
        test_bot_owner_decorator_allows_owner,
        test_permission_check_logging,
    ]
    
    for test_func in test_functions:
        try:
            await test_func()
            tests_passed += 1
        except AssertionError as e:
            tests_failed += 1
            print(f"✗ {test_func.__name__} failed: {e}")
        except Exception as e:
            tests_failed += 1
            print(f"✗ {test_func.__name__} error: {e}")
    
    # Run sync test
    try:
        test_error_embed_generation()
        tests_passed += 1
    except AssertionError as e:
        tests_failed += 1
        print(f"✗ test_error_embed_generation failed: {e}")
    except Exception as e:
        tests_failed += 1
        print(f"✗ test_error_embed_generation error: {e}")
    
    print("\n" + "="*60)
    print(f"Results: {tests_passed} passed, {tests_failed} failed")
    print("="*60 + "\n")
    
    return tests_failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
