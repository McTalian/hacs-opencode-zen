"""Tests for the OpencodeZen config flow."""

from unittest.mock import AsyncMock

import pytest

from custom_components.opencode_zen.const import (
    CONF_PROMPT,
    CONF_WEB_SEARCH,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_API_KEY, CONF_LLM_HASS_API, CONF_MODEL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import llm

from . import get_subentry_id, setup_integration

from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.mark.usefixtures("mock_setup_entry")
async def test_full_flow(
    hass: HomeAssistant,
    mock_validate_key: AsyncMock,
) -> None:
    """Test the full config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: "sk-test-key"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "OpencodeZen (sk-test-k...)"
    assert result["data"] == {CONF_API_KEY: "sk-test-key"}


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (ValueError("Invalid API key"), "cannot_connect"),
        (Exception, "unknown"),
    ],
)
@pytest.mark.usefixtures("mock_setup_entry")
async def test_form_errors(
    hass: HomeAssistant,
    mock_validate_key: AsyncMock,
    exception: Exception,
    error: str,
) -> None:
    """Test we handle errors from the OpencodeZen API."""
    mock_validate_key.side_effect = exception

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_API_KEY: "sk-test-key"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    mock_validate_key.side_effect = None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "sk-test-key"},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.usefixtures("mock_setup_entry")
async def test_duplicate_entry(
    hass: HomeAssistant,
    mock_validate_key: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test aborting the flow if an entry already exists."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "sk-test-key"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_create_conversation_agent(
    hass: HomeAssistant,
    mock_fetch_models: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test creating a conversation agent."""
    await setup_integration(hass, mock_config_entry)

    result = await hass.config_entries.subentries.async_init(
        (mock_config_entry.entry_id, "conversation"),
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]
    assert result["step_id"] == "init"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_MODEL: "test-model-1",
            CONF_PROMPT: "you are an assistant",
            CONF_LLM_HASS_API: ["assist"],
            CONF_WEB_SEARCH: False,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_MODEL: "test-model-1",
        CONF_PROMPT: "you are an assistant",
        CONF_LLM_HASS_API: ["assist"],
        CONF_WEB_SEARCH: False,
    }


async def test_create_conversation_agent_no_control(
    hass: HomeAssistant,
    mock_fetch_models: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test creating a conversation agent without control over the LLM API."""
    await setup_integration(hass, mock_config_entry)

    result = await hass.config_entries.subentries.async_init(
        (mock_config_entry.entry_id, "conversation"),
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]
    assert result["step_id"] == "init"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_MODEL: "test-model-1",
            CONF_PROMPT: "you are an assistant",
            CONF_LLM_HASS_API: [],
            CONF_WEB_SEARCH: False,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_MODEL: "test-model-1",
        CONF_PROMPT: "you are an assistant",
        CONF_WEB_SEARCH: False,
    }


async def test_create_ai_task(
    hass: HomeAssistant,
    mock_fetch_models: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test creating an AI Task."""
    await setup_integration(hass, mock_config_entry)

    result = await hass.config_entries.subentries.async_init(
        (mock_config_entry.entry_id, "ai_task_data"),
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]
    assert result["step_id"] == "init"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {CONF_MODEL: "test-model-1"},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_MODEL: "test-model-1"}


@pytest.mark.parametrize(
    "subentry_type",
    ["conversation", "ai_task_data"],
)
async def test_subentry_exceptions(
    hass: HomeAssistant,
    mock_fetch_models: AsyncMock,
    mock_config_entry: MockConfigEntry,
    subentry_type: str,
) -> None:
    """Test subentry flow exceptions."""
    await setup_integration(hass, mock_config_entry)

    mock_fetch_models.side_effect = Exception("Connection failed")

    result = await hass.config_entries.subentries.async_init(
        (mock_config_entry.entry_id, subentry_type),
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_reconfigure_conversation_agent(
    hass: HomeAssistant,
    mock_fetch_models: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test reconfiguring a conversation agent."""
    await setup_integration(hass, mock_config_entry)

    subentry_id = get_subentry_id(mock_config_entry, "conversation")

    result = await mock_config_entry.start_subentry_reconfigure_flow(hass, subentry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_MODEL: "test-model-2",
            CONF_PROMPT: "updated prompt",
            CONF_LLM_HASS_API: ["assist"],
            CONF_WEB_SEARCH: True,
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    subentry = mock_config_entry.subentries[subentry_id]
    assert subentry.data[CONF_MODEL] == "test-model-2"
    assert subentry.data[CONF_PROMPT] == "updated prompt"
    assert subentry.data[CONF_LLM_HASS_API] == ["assist"]
    assert subentry.data[CONF_WEB_SEARCH] is True


async def test_reconfigure_ai_task(
    hass: HomeAssistant,
    mock_fetch_models: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test reconfiguring an AI task."""
    await setup_integration(hass, mock_config_entry)

    subentry_id = get_subentry_id(mock_config_entry, "ai_task_data")

    result = await mock_config_entry.start_subentry_reconfigure_flow(hass, subentry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {CONF_MODEL: "test-model-2"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


@pytest.mark.parametrize(
    "subentry_type",
    ["conversation", "ai_task_data"],
)
async def test_subentry_entry_not_loaded(
    hass: HomeAssistant,
    mock_fetch_models: AsyncMock,
    mock_config_entry: MockConfigEntry,
    subentry_type: str,
) -> None:
    """Test subentry aborts when entry is not loaded."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.subentries.async_init(
        (mock_config_entry.entry_id, subentry_type),
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "entry_not_loaded"


@pytest.mark.parametrize(
    ("web_search", "expected_web_search"),
    [(True, True), (False, False)],
    indirect=["web_search"],
)
@pytest.mark.usefixtures("mock_setup_entry")
async def test_create_conversation_agent_web_search(
    hass: HomeAssistant,
    mock_fetch_models: AsyncMock,
    mock_config_entry: MockConfigEntry,
    web_search: bool,
    expected_web_search: bool,
) -> None:
    """Test creating a conversation agent with web search enabled/disabled."""
    await setup_integration(hass, mock_config_entry)

    result = await hass.config_entries.subentries.async_init(
        (mock_config_entry.entry_id, "conversation"),
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    schema = result["data_schema"].schema
    key = next(k for k in schema if k == CONF_WEB_SEARCH)
    assert key.default() is False

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_MODEL: "test-model-1",
            CONF_PROMPT: "you are an assistant",
            CONF_LLM_HASS_API: ["assist"],
            CONF_WEB_SEARCH: expected_web_search,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_WEB_SEARCH] is expected_web_search
