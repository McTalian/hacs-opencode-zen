# OpencodeZen - Home Assistant integration for OpenCode AI
# Copyright (C) 2026 Rob "McTalian" Anderson
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Config flow for OpencodeZen integration."""

import logging
from typing import Any, override

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_USER,
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_API_KEY, CONF_LLM_HASS_API, CONF_MODEL
from homeassistant.core import callback
from homeassistant.helpers import llm
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TemplateSelector,
)

from .const import (
    CONF_PROMPT,
    CONF_WEB_SEARCH,
    DOMAIN,
    RECOMMENDED_CONVERSATION_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)

ZEN_BASE_URL = "https://opencode.ai/zen/v1"


async def _validate_key(hass, api_key: str) -> str:
    session = async_get_clientsession(hass)
    async with session.get(
        f"{ZEN_BASE_URL}/models",
        headers={"Authorization": f"Bearer {api_key}"},
    ) as resp:
        if resp.status == 401:
            raise ValueError("Invalid API key")
        resp.raise_for_status()
    return f"OpencodeZen ({api_key[:8]}...)"


async def _fetch_models(hass, api_key: str) -> list[dict[str, Any]]:
    session = async_get_clientsession(hass)
    async with session.get(
        f"{ZEN_BASE_URL}/models",
        headers={"Authorization": f"Bearer {api_key}"},
    ) as resp:
        resp.raise_for_status()
        data = await resp.json()
    return data.get("data", [])


class OpencodeZenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpencodeZen."""

    VERSION = 1
    MINOR_VERSION = 2

    @classmethod
    @callback
    @override
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this handler."""
        return {
            "conversation": ConversationFlowHandler,
            "ai_task_data": AITaskDataFlowHandler,
        }

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            self._async_abort_entries_match(user_input)
            try:
                label = await _validate_key(self.hass, user_input[CONF_API_KEY])
            except ValueError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=label,
                    data=user_input,
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                }
            ),
            errors=errors,
        )


class OpencodeZenSubentryFlowHandler(ConfigSubentryFlow):
    """Handle subentry flow for OpencodeZen."""

    def __init__(self) -> None:
        """Initialize the subentry flow."""
        self.models: dict[str, dict[str, Any]] = {}

    async def _get_models(self) -> None:
        """Fetch models from OpencodeZen."""
        entry = self._get_entry()
        models = await _fetch_models(self.hass, entry.data[CONF_API_KEY])
        self.models = {model["id"]: model for model in models}


class ConversationFlowHandler(OpencodeZenSubentryFlowHandler):
    """Handle conversation subentry flow."""

    def __init__(self) -> None:
        """Initialize the subentry flow."""
        super().__init__()
        self.options: dict[str, Any] = {}

    @property
    def _is_new(self) -> bool:
        """Return if this is a new subentry."""
        return self.source == SOURCE_USER

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """User flow to create a conversation agent."""
        self.options = RECOMMENDED_CONVERSATION_OPTIONS.copy()
        return await self.async_step_init(user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Handle reconfiguration of a conversation agent."""
        self.options = self._get_reconfigure_subentry().data.copy()
        return await self.async_step_init(user_input)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Manage conversation agent configuration."""
        if self._get_entry().state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")

        if user_input is not None:
            if not user_input.get(CONF_LLM_HASS_API):
                user_input.pop(CONF_LLM_HASS_API, None)
            if self._is_new:
                return self.async_create_entry(
                    title=self.models[user_input[CONF_MODEL]].get(
                        "name", self.models[user_input[CONF_MODEL]]["id"]
                    ),
                    data=user_input,
                )
            return self.async_update_and_abort(
                self._get_entry(),
                self._get_reconfigure_subentry(),
                data=user_input,
            )

        try:
            await self._get_models()
        except Exception:
            _LOGGER.exception("Unexpected exception")
            return self.async_abort(reason="cannot_connect")

        options = [
            SelectOptionDict(value=model["id"], label=model.get("name", model["id"]))
            for model in self.models.values()
        ]

        hass_apis: list[SelectOptionDict] = [
            SelectOptionDict(
                label=api.name,
                value=api.id,
            )
            for api in llm.async_get_apis(self.hass)
        ]

        if suggested_llm_apis := self.options.get(CONF_LLM_HASS_API):
            valid_api_ids = {api["value"] for api in hass_apis}
            self.options[CONF_LLM_HASS_API] = [
                api for api in suggested_llm_apis if api in valid_api_ids
            ]

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MODEL, default=self.options.get(CONF_MODEL)
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=options, mode=SelectSelectorMode.DROPDOWN, sort=True
                        ),
                    ),
                    vol.Optional(
                        CONF_PROMPT,
                        description={
                            "suggested_value": self.options.get(
                                CONF_PROMPT,
                                RECOMMENDED_CONVERSATION_OPTIONS[CONF_PROMPT],
                            )
                        },
                    ): TemplateSelector(),
                    vol.Optional(
                        CONF_LLM_HASS_API,
                        default=self.options.get(
                            CONF_LLM_HASS_API,
                            RECOMMENDED_CONVERSATION_OPTIONS[CONF_LLM_HASS_API],
                        ),
                    ): SelectSelector(
                        SelectSelectorConfig(options=hass_apis, multiple=True)
                    ),
                    vol.Optional(
                        CONF_WEB_SEARCH,
                        default=self.options.get(
                            CONF_WEB_SEARCH,
                            RECOMMENDED_CONVERSATION_OPTIONS[CONF_WEB_SEARCH],
                        ),
                    ): BooleanSelector(),
                }
            ),
        )


class AITaskDataFlowHandler(OpencodeZenSubentryFlowHandler):
    """Handle AI task subentry flow."""

    def __init__(self) -> None:
        """Initialize the subentry flow."""
        super().__init__()
        self.options: dict[str, Any] = {}

    @property
    def _is_new(self) -> bool:
        """Return if this is a new subentry."""
        return self.source == SOURCE_USER

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """User flow to create an AI task."""
        self.options = {}
        return await self.async_step_init(user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Handle reconfiguration of an AI task."""
        self.options = self._get_reconfigure_subentry().data.copy()
        return await self.async_step_init(user_input)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Manage AI task configuration."""
        if self._get_entry().state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")

        if user_input is not None:
            if self._is_new:
                return self.async_create_entry(
                    title=self.models[user_input[CONF_MODEL]].get(
                        "name", self.models[user_input[CONF_MODEL]]["id"]
                    ),
                    data=user_input,
                )
            return self.async_update_and_abort(
                self._get_entry(),
                self._get_reconfigure_subentry(),
                data=user_input,
            )

        try:
            await self._get_models()
        except Exception:
            _LOGGER.exception("Unexpected exception")
            return self.async_abort(reason="cannot_connect")

        options = [
            SelectOptionDict(value=model["id"], label=model.get("name", model["id"]))
            for model in self.models.values()
            if "STRUCTURED_OUTPUTS" in model.get("supported_parameters", [])
        ]

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MODEL, default=self.options.get(CONF_MODEL)
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=options, mode=SelectSelectorMode.DROPDOWN, sort=True
                        ),
                    ),
                }
            ),
        )
