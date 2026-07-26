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

"""The OpencodeZen integration."""

from openai import AsyncOpenAI, AuthenticationError, OpenAIError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers.httpx_client import get_async_client

from .const import CONF_WEB_SEARCH, LOGGER

PLATFORMS = [Platform.AI_TASK, Platform.CONVERSATION]

type OpencodeZenConfigEntry = ConfigEntry[AsyncOpenAI]


async def async_setup_entry(hass: HomeAssistant, entry: OpencodeZenConfigEntry) -> bool:
    """Set up OpencodeZen from a config entry."""
    client = AsyncOpenAI(
        base_url="https://opencode.ai/zen/v1",
        api_key=entry.data[CONF_API_KEY],
        http_client=get_async_client(hass),
    )

    # Cache current platform data which gets added to each request
    # (caching done by library)
    _ = await hass.async_add_executor_job(client.platform_headers)

    try:
        async for _ in client.with_options(timeout=10.0).models.list():
            break
    except AuthenticationError as err:
        LOGGER.error("Invalid API key: %s", err)
        raise ConfigEntryError("Invalid API key") from err
    except OpenAIError as err:
        raise ConfigEntryNotReady(err) from err

    entry.runtime_data = client

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: OpencodeZenConfigEntry
) -> None:
    """Handle update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: OpencodeZenConfigEntry) -> bool:
    """Unload OpencodeZen."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(
    hass: HomeAssistant, entry: OpencodeZenConfigEntry
) -> bool:
    """Migrate config entry."""
    LOGGER.debug("Migrating from version %s.%s", entry.version, entry.minor_version)

    if entry.version == 1 and entry.minor_version < 2:
        for subentry in entry.subentries.values():
            if CONF_WEB_SEARCH in subentry.data:
                continue

            updated_data = {**subentry.data, CONF_WEB_SEARCH: False}

            hass.config_entries.async_update_subentry(
                entry, subentry, data=updated_data
            )

        hass.config_entries.async_update_entry(entry, minor_version=2)

    LOGGER.info(
        "Migration to version %s.%s successful", entry.version, entry.minor_version
    )

    return True
