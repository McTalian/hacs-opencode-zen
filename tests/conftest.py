"""Fixtures for OpencodeZen integration tests."""

import asyncio
from collections.abc import Generator
import os
from pathlib import Path
import shutil
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.opencode_zen.const import (
    CONF_PROMPT,
    CONF_WEB_SEARCH,
    DOMAIN,
)
from homeassistant.config_entries import ConfigEntryState, ConfigSubentryData
from homeassistant.const import CONF_API_KEY, CONF_LLM_HASS_API, CONF_MODEL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm, storage
from homeassistant.setup import async_setup_component

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_test_home_assistant,
)

TEST_MODEL_1 = "test-model-1"
TEST_MODEL_2 = "test-model-2"
TEST_MODELS = [
    {"id": TEST_MODEL_1, "name": "Test Model One"},
    {"id": TEST_MODEL_2, "name": "Test Model Two"},
]


@pytest.fixture(autouse=True)
def mock_openai_client() -> Generator[None]:
    """Mock AsyncOpenAI client to prevent real API calls during tests."""
    with patch(
        "custom_components.opencode_zen.AsyncOpenAI",
    ) as mock:
        instance = mock.return_value
        instance.with_options.return_value = instance
        models_result = AsyncMock()
        models_result.__aiter__.return_value = AsyncMock()
        models_result.__aiter__.return_value.__anext__.side_effect = StopAsyncIteration
        instance.models.list.return_value = models_result
        yield


@pytest.fixture
async def hass(tmp_path: Path) -> HomeAssistant:
    """Create a test instance of Home Assistant with custom component loaded."""
    from homeassistant.loader import DATA_CUSTOM_COMPONENTS

    loop = asyncio.get_running_loop()

    cc_src = os.path.join(os.path.dirname(__file__), "..", "custom_components")
    cc_dst = os.path.join(str(tmp_path), "custom_components")
    shutil.copytree(cc_src, cc_dst, symlinks=True)

    with patch.object(storage.Store, "_async_schedule_callback_delayed_write"):
        async with async_test_home_assistant(loop, config_dir=str(tmp_path)) as hass:
            hass.data.pop(DATA_CUSTOM_COMPONENTS, None)
            await async_setup_component(hass, "homeassistant", {})
            yield hass
            loaded_entries = [
                entry
                for entry in hass.config_entries.async_entries()
                if entry.state is ConfigEntryState.LOADED
            ]
            if loaded_entries:
                await asyncio.gather(
                    *(
                        hass.config_entries.async_unload(
                            config_entry.entry_id
                        )
                        for config_entry in loaded_entries
                    )
                )
            await hass.async_stop(force=True)


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.opencode_zen.async_setup_entry",
        return_value=True,
    ) as mock:
        yield mock


@pytest.fixture
def mock_validate_key() -> Generator[AsyncMock]:
    """Mock _validate_key to return success."""
    with patch(
        "custom_components.opencode_zen.config_flow._validate_key",
        return_value="OpencodeZen (sk-test-k...)",
    ) as mock:
        yield mock


@pytest.fixture
def mock_fetch_models() -> Generator[AsyncMock]:
    """Mock _fetch_models to return test models."""
    with patch(
        "custom_components.opencode_zen.config_flow._fetch_models",
        return_value=TEST_MODELS,
    ) as mock:
        yield mock


@pytest.fixture
def enable_assist() -> bool:
    """Whether to enable assist API in conversation subentry."""
    return False


@pytest.fixture
def web_search() -> bool:
    """Mock web search setting."""
    return False


@pytest.fixture
def conversation_subentry_data(enable_assist: bool, web_search: bool) -> dict[str, Any]:
    """Mock conversation subentry data."""
    res: dict[str, Any] = {
        CONF_MODEL: TEST_MODEL_1,
        CONF_PROMPT: "You are a helpful assistant.",
        CONF_WEB_SEARCH: web_search,
    }
    if enable_assist:
        res[CONF_LLM_HASS_API] = [llm.LLM_API_ASSIST]
    return res


@pytest.fixture
def ai_task_data_subentry_data() -> dict[str, Any]:
    """Mock AI task subentry data."""
    return {
        CONF_MODEL: TEST_MODEL_2,
    }


@pytest.fixture
def mock_config_entry(
    hass: HomeAssistant,
    conversation_subentry_data: dict[str, Any],
    ai_task_data_subentry_data: dict[str, Any],
) -> MockConfigEntry:
    """Mock a config entry."""
    return MockConfigEntry(
        title="OpencodeZen",
        domain=DOMAIN,
        data={
            CONF_API_KEY: "sk-test-key",
        },
        subentries_data=[
            ConfigSubentryData(
                data=conversation_subentry_data,
                subentry_id="ABCDEF",
                subentry_type="conversation",
                title="Test Model One",
                unique_id=None,
            ),
            ConfigSubentryData(
                data=ai_task_data_subentry_data,
                subentry_id="ABCDEG",
                subentry_type="ai_task_data",
                title="Test Model Two",
                unique_id=None,
            ),
        ],
    )
