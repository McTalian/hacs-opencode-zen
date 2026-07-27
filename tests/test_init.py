"""Tests for the OpencodeZen integration."""

from unittest.mock import patch

from custom_components.opencode_zen.const import (
    CONF_PROMPT,
    CONF_WEB_SEARCH,
    DOMAIN,
)
from homeassistant.config_entries import ConfigEntryState, ConfigSubentryData
from homeassistant.const import CONF_API_KEY, CONF_LLM_HASS_API, CONF_MODEL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm

from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_migrate_entry_from_v1_1_to_v1_2(
    hass: HomeAssistant,
) -> None:
    """Test migration from version 1.1 to 1.2."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_API_KEY: "sk-test-key",
        },
        version=1,
        minor_version=1,
        subentries_data=[
            ConfigSubentryData(
                data={
                    CONF_MODEL: "test-model-1",
                    CONF_PROMPT: "You are a helpful assistant.",
                    CONF_LLM_HASS_API: [llm.LLM_API_ASSIST],
                },
                subentry_id="conversation_subentry",
                subentry_type="conversation",
                title="Test Model One",
                unique_id=None,
            ),
            ConfigSubentryData(
                data={
                    CONF_MODEL: "test-model-2",
                },
                subentry_id="ai_task_subentry",
                subentry_type="ai_task_data",
                title="Test Model Two",
                unique_id=None,
            ),
        ],
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.opencode_zen.async_setup_entry",
        return_value=True,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.version == 1
    assert entry.minor_version == 2

    conversation_subentry = entry.subentries["conversation_subentry"]
    assert conversation_subentry.data[CONF_MODEL] == "test-model-1"
    assert conversation_subentry.data[CONF_PROMPT] == "You are a helpful assistant."
    assert conversation_subentry.data[CONF_LLM_HASS_API] == [llm.LLM_API_ASSIST]
    assert conversation_subentry.data[CONF_WEB_SEARCH] is False

    ai_task_subentry = entry.subentries["ai_task_subentry"]
    assert ai_task_subentry.data[CONF_MODEL] == "test-model-2"
    assert ai_task_subentry.data[CONF_WEB_SEARCH] is False


async def test_migrate_entry_already_migrated(
    hass: HomeAssistant,
) -> None:
    """Test migration is skipped when already on version 1.2."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_API_KEY: "sk-test-key",
        },
        version=1,
        minor_version=1,
        subentries_data=[
            ConfigSubentryData(
                data={
                    CONF_MODEL: "test-model-1",
                    CONF_PROMPT: "You are a helpful assistant.",
                    CONF_WEB_SEARCH: True,
                },
                subentry_id="conversation_subentry",
                subentry_type="conversation",
                title="Test Model One",
                unique_id=None,
            ),
        ],
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.opencode_zen.async_setup_entry",
        return_value=True,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.version == 1
    assert entry.minor_version == 2

    conversation_subentry = entry.subentries["conversation_subentry"]
    assert conversation_subentry.data[CONF_MODEL] == "test-model-1"
    assert conversation_subentry.data[CONF_WEB_SEARCH] is True


async def test_migrate_entry_from_future_version_fails(
    hass: HomeAssistant,
) -> None:
    """Test migration fails for future versions."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_API_KEY: "sk-test-key",
        },
        version=100,
        minor_version=99,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 100
    assert entry.minor_version == 99
    assert entry.state is ConfigEntryState.MIGRATION_ERROR
