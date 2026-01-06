
from backend.integrations.discord.permissions import (
    is_bot_owner,
    is_admin,
    get_permission_embed,
    check_permissions
)
from discord import Interaction, Member, Guild, User
import discord
from unittest.mock import Mock, patch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def create_mock_interaction(user_id=999999999, guild_id=987654321, command_name="test_command"):
    """Create a mock Discord interaction."""
    interaction = Mock(spec=Interaction)
    interaction.user = Mock(spec=User)
    interaction.user.id = user_id
    interaction.guild = Mock(spec=Guild)
    interaction.guild_id = guild_id
    interaction.command = Mock()
    interaction.command.name = command_name
    interaction.response = Mock()
    interaction.response.is_done = Mock(return_value=False)
    interaction.response.send_message = Mock()
    interaction.followup = Mock()
    interaction.followup.send = Mock()
    return interaction


def create_mock_admin_member():
    """Create a mock member with administrator permissions."""
    member = Mock(spec=Member)
    member.guild_permissions = Mock()
    member.guild_permissions.administrator = True
    return member


def create_mock_regular_member():
    """Create a mock member without administrator permissions."""
    member = Mock(spec=Member)
    member.guild_permissions = Mock()
    member.guild_permissions.administrator = False
    return member


# Test is_bot_owner function
def test_bot_owner_returns_true():
    with patch("backend.integrations.discord.permissions.settings") as mock_settings:
        mock_settings.bot_owner_id = 123456789
        result = is_bot_owner(123456789)
        assert result is True, "Bot owner should return True"
        print("✓ test_bot_owner_returns_true")


def test_non_owner_returns_false():
    with patch("backend.integrations.discord.permissions.settings") as mock_settings:
        mock_settings.bot_owner_id = 123456789
        result = is_bot_owner(999999999)
        assert result is False, "Non-owner should return False"
        print("✓ test_non_owner_returns_false")


def test_no_bot_owner_configured():
    with patch("backend.integrations.discord.permissions.settings") as mock_settings:
        mock_settings.bot_owner_id = None
        result = is_bot_owner(123456789)
        assert result is False, "Should return False when owner not configured"
        print("✓ test_no_bot_owner_configured")


# Test is_admin function
def test_admin_member_returns_true():
    interaction = create_mock_interaction(user_id=111111111)
    admin_member = create_mock_admin_member()
    interaction.guild.get_member = Mock(return_value=admin_member)

    result = is_admin(interaction)
    assert result is True, "Admin member should return True"
    print("✓ test_admin_member_returns_true")


def test_regular_member_returns_false():
    interaction = create_mock_interaction(user_id=222222222)
    regular_member = create_mock_regular_member()
    interaction.guild.get_member = Mock(return_value=regular_member)

    result = is_admin(interaction)
    assert result is False, "Regular member should return False"
    print("✓ test_regular_member_returns_false")


def test_no_guild_returns_false():
    interaction = create_mock_interaction()
    interaction.guild = None

    result = is_admin(interaction)
    assert result is False, "No guild should return False"
    print("✓ test_no_guild_returns_false")


def test_member_not_found_returns_false():
    interaction = create_mock_interaction()
    interaction.guild.get_member = Mock(return_value=None)

    result = is_admin(interaction)
    assert result is False, "Missing member should return False"
    print("✓ test_member_not_found_returns_false")


# Test get_permission_embed function
def test_default_embed_creation():
    embed = get_permission_embed()

    assert embed.title == "❌ Permission Denied", "Default title should match"
    assert "don't have permission" in embed.description, "Default description should match"
    assert embed.color == discord.Color.red(), "Color should be red"
    assert len(embed.fields) == 2, "Should have 2 fields"
    print("✓ test_default_embed_creation")


def test_custom_embed_creation():
    embed = get_permission_embed(
        title="Custom Title",
        description="Custom description",
        required_permission="Custom Permission"
    )

    assert embed.title == "Custom Title", "Custom title should match"
    assert embed.description == "Custom description", "Custom description should match"
    assert "Custom Permission" in embed.fields[0].value, "Custom permission should be in field"
    print("✓ test_custom_embed_creation")


# Test check_permissions function
def test_check_permissions_bot_owner():
    with patch("backend.integrations.discord.permissions.settings") as mock_settings:
        mock_settings.bot_owner_id = 123456789

        interaction = create_mock_interaction(user_id=123456789)
        has_permission, reason = check_permissions(interaction)

        assert has_permission is True, "Bot owner should have permission"
        assert reason is None, "No reason for allowed access"
        print("✓ test_check_permissions_bot_owner")


def test_check_permissions_admin():
    with patch("backend.integrations.discord.permissions.settings") as mock_settings:
        mock_settings.bot_owner_id = 123456789

        interaction = create_mock_interaction(user_id=999999999)
        admin_member = create_mock_admin_member()
        interaction.guild.get_member = Mock(return_value=admin_member)

        has_permission, reason = check_permissions(interaction)

        assert has_permission is True, "Admin should have permission"
        assert reason is None, "No reason for allowed access"
        print("✓ test_check_permissions_admin")


def test_check_permissions_denied():
    with patch("backend.integrations.discord.permissions.settings") as mock_settings:
        mock_settings.bot_owner_id = 123456789

        interaction = create_mock_interaction(user_id=999999999)
        regular_member = create_mock_regular_member()
        interaction.guild.get_member = Mock(return_value=regular_member)

        has_permission, reason = check_permissions(interaction)

        assert has_permission is False, "Regular user should be denied"
        assert reason is not None, "Should have denial reason"
        assert "neither bot owner nor server administrator" in reason, "Reason should explain denial"
        print("✓ test_check_permissions_denied")


# Run all tests
def run_all_tests():
    """Run all permission system tests."""
    print("\n" + "="*50)
    print("Permission System Tests")
    print("="*50 + "\n")

    tests = [
        ("Bot Owner Checks", [
            test_bot_owner_returns_true,
            test_non_owner_returns_false,
            test_no_bot_owner_configured,
        ]),
        ("Admin Checks", [
            test_admin_member_returns_true,
            test_regular_member_returns_false,
            test_no_guild_returns_false,
            test_member_not_found_returns_false,
        ]),
        ("Embed Generation", [
            test_default_embed_creation,
            test_custom_embed_creation,
        ]),
        ("Permission Checks", [
            test_check_permissions_bot_owner,
            test_check_permissions_admin,
            test_check_permissions_denied,
        ]),
    ]

    total_tests = 0
    failed_tests = []

    for category, category_tests in tests:
        print(f"{category}:")
        for test in category_tests:
            total_tests += 1
            try:
                test()
            except AssertionError as e:
                print(f"  ✗ {test.__name__}: {e}")
                failed_tests.append((category, test.__name__, str(e)))
            except Exception as e:
                print(f"  ✗ {test.__name__}: Unexpected error - {e}")
                failed_tests.append((category, test.__name__, f"Unexpected error: {e}"))
        print()

    print("="*50)
    print(f"Results: {total_tests - len(failed_tests)}/{total_tests} tests passed")

    if failed_tests:
        print(f"\nFailed tests ({len(failed_tests)}):")
        for category, test_name, error in failed_tests:
            print(f"  [{category}] {test_name}: {error}")
        print("="*50)
        return False
    else:
        print("All tests passed! ✓")
        print("="*50)
        return True


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
