"""Config flow for 511 Transit integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector

from .api import (
    Transit511ApiClient,
    Transit511ApiError,
    Transit511AuthError,
    Transit511RateLimitError,
)
from .const import (
    ALL_ENTITY_TYPES,
    CONF_API_KEY,
    CONF_ENABLED_ENTITIES,
    CONF_LINE_ID,
    CONF_MONITORING_TYPE,
    CONF_OPERATOR,
    CONF_STOP_CODE,
    CONF_VEHICLE_ID,
    DEFAULT_ENABLED_ENTITIES,
    DEFAULT_SCAN_INTERVAL,
    DIRECTION_FILTERED_ENTITY_TYPES,
    DOMAIN,
    ERROR_AUTH_FAILED,
    ERROR_CANNOT_CONNECT,
    ERROR_INVALID_OPERATOR,
    ERROR_INVALID_STOP,
    ERROR_RATE_LIMIT,
    ERROR_UNKNOWN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    MONITORING_TYPE_STOP,
    MONITORING_TYPE_VEHICLE,
)

_LOGGER = logging.getLogger(__name__)


class Transit511ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for 511 Transit."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._api_key: str | None = None
        self._client: Transit511ApiClient | None = None
        self._monitoring_type: str | None = None
        self._operators: dict[str, str] = {}
        self._lines: dict[str, str] = {}
        self._stops: dict[str, str] = {}

    def _get_existing_api_key(self) -> str | None:
        """Get API key from existing config entry if one exists."""
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if CONF_API_KEY in entry.data:
                _LOGGER.info("Found existing API key from config entry: %s", entry.title)
                return entry.data[CONF_API_KEY]
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - API key entry or reuse."""
        # Check if we already have an API key from another config entry
        existing_api_key = self._get_existing_api_key()

        if existing_api_key:
            # Reuse existing API key, skip to monitoring type
            self._api_key = existing_api_key
            session = async_get_clientsession(self.hass)
            self._client = Transit511ApiClient(existing_api_key, session)
            return await self.async_step_monitoring_type()

        # No existing API key, need to ask for it
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY]

            # Validate the API key
            session = async_get_clientsession(self.hass)
            client = Transit511ApiClient(api_key, session)

            try:
                await client.validate_api_key()
            except Transit511AuthError:
                errors["base"] = ERROR_AUTH_FAILED
            except Transit511RateLimitError:
                errors["base"] = ERROR_RATE_LIMIT
            except Transit511ApiError:
                errors["base"] = ERROR_CANNOT_CONNECT
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception validating API key")
                errors["base"] = ERROR_UNKNOWN

            if not errors:
                # Store API key and client for next steps
                self._api_key = api_key
                self._client = client
                return await self.async_step_monitoring_type()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
            description_placeholders={
                "note": "This is your first 511 Transit configuration. Your API key will be saved and reused for future stops/vehicles."
            },
        )

    async def async_step_monitoring_type(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle monitoring type selection."""
        if user_input is not None:
            monitoring_type = user_input[CONF_MONITORING_TYPE]

            # Support both types - start with stop monitoring
            if MONITORING_TYPE_STOP in monitoring_type:
                self._monitoring_type = MONITORING_TYPE_STOP
                return await self.async_step_stop_monitoring()
            else:
                self._monitoring_type = MONITORING_TYPE_VEHICLE
                return await self.async_step_vehicle_monitoring()

        return self.async_show_form(
            step_id="monitoring_type",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MONITORING_TYPE): vol.In(
                        {
                            MONITORING_TYPE_STOP: "Stop Monitoring (arrival predictions)",
                            MONITORING_TYPE_VEHICLE: "Vehicle Monitoring (GPS tracking)",
                        }
                    )
                }
            ),
            description_placeholders={
                "info": "You can add multiple stops and vehicles by adding this integration multiple times."
            },
        )

    async def async_step_stop_monitoring(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle stop monitoring configuration."""
        errors: dict[str, str] = {}

        # Load operators on first visit
        if not self._operators:
            try:
                operators_data = await self._client.get_operators()
                # Parse operators from response
                # Expected structure: {"Siri": {"DataObjectDelivery": {"dataObjects": [...]}}}
                data_objects = (
                    operators_data.get("Siri", {})
                    .get("ServiceDelivery", {})
                    .get("DataObjectDelivery", [])
                )
                if isinstance(data_objects, list) and len(data_objects) > 0:
                    operators_list = (
                        data_objects[0].get("dataObjects", {}).get("Operator", [])
                    )
                    if not isinstance(operators_list, list):
                        operators_list = [operators_list]

                    for operator in operators_list:
                        op_id = operator.get("id", "")
                        op_name = operator.get("Name", {}).get("Text", op_id)
                        if op_id:
                            self._operators[op_id] = op_name
                else:
                    # Fallback to common operators if parsing fails
                    self._operators = {
                        "SF": "San Francisco Muni",
                        "BA": "BART",
                        "AC": "AC Transit",
                        "CC": "County Connection",
                        "CM": "Caltrain",
                    }
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.warning("Could not fetch operators, using defaults: %s", err)
                self._operators = {
                    "SF": "San Francisco Muni",
                    "BA": "BART",
                    "AC": "AC Transit",
                }

        if user_input is not None:
            operator = user_input[CONF_OPERATOR]
            stop_code = user_input[CONF_STOP_CODE]
            line_id = user_input.get(CONF_LINE_ID)

            # Validate stop by fetching data
            try:
                data = await self._client.get_stop_monitoring(operator, stop_code)
                visits = (
                    data.get("ServiceDelivery", {})
                    .get("StopMonitoringDelivery", {})
                    .get("MonitoredStopVisit", [])
                )

                if not isinstance(visits, list):
                    visits = [visits] if visits else []

                # Get stop name from first visit if available
                stop_name = stop_code
                if visits:
                    stop_name = (
                        visits[0]
                        .get("MonitoredVehicleJourney", {})
                        .get("MonitoredCall", {})
                        .get("StopPointName", stop_code)
                    )

            except Transit511ApiError:
                errors["base"] = ERROR_INVALID_STOP
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception validating stop")
                errors["base"] = ERROR_UNKNOWN

            if not errors:
                # Move to entity selection
                return await self.async_step_entity_selection(
                    {
                        CONF_OPERATOR: operator,
                        CONF_STOP_CODE: stop_code,
                        CONF_LINE_ID: line_id,
                        "stop_name": stop_name,
                    }
                )

        # Build schema with operator dropdown
        schema = vol.Schema(
            {
                vol.Required(CONF_OPERATOR): vol.In(self._operators),
                vol.Required(CONF_STOP_CODE): str,
                vol.Optional(CONF_LINE_ID): str,
            }
        )

        return self.async_show_form(
            step_id="stop_monitoring",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "operator_help": "Select the transit operator/agency",
                "stop_help": "Enter the stop code (e.g., 18031 for Muni)",
            },
        )

    async def async_step_entity_selection(
        self, context_data: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle entity type selection."""
        if context_data is None:
            # This shouldn't happen, but handle gracefully
            return await self.async_step_stop_monitoring()

        # Build schema with checkboxes for each entity type
        entity_options = {}
        for entity_type in ALL_ENTITY_TYPES:
            entity_options[entity_type] = entity_type.replace("_", " ").title()

        direction_options = {}
        for entity_type in DIRECTION_FILTERED_ENTITY_TYPES:
            direction_options[entity_type] = entity_type.replace("_", " ").title()

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ENABLED_ENTITIES,
                    default=DEFAULT_ENABLED_ENTITIES,
                ): cv.multi_select(entity_options),
                vol.Optional(
                    "direction_filtered",
                    default=[],
                ): cv.multi_select(direction_options),
            }
        )

        # For now, just use the defaults and create the entry
        operator = context_data[CONF_OPERATOR]
        stop_code = context_data[CONF_STOP_CODE]
        line_id = context_data.get(CONF_LINE_ID)
        stop_name = context_data.get("stop_name", stop_code)

        # Create unique ID
        unique_id = f"{operator}_{stop_code}"
        if line_id:
            unique_id += f"_{line_id}"

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        # Create the config entry
        title = f"{self._operators.get(operator, operator)}"
        if line_id:
            title += f" {line_id}"
        title += f" @ {stop_name}"

        return self.async_create_entry(
            title=title,
            data={
                CONF_API_KEY: self._api_key,
                CONF_MONITORING_TYPE: MONITORING_TYPE_STOP,
                CONF_OPERATOR: operator,
                CONF_STOP_CODE: stop_code,
                CONF_LINE_ID: line_id,
                "stop_name": stop_name,
                "operator_name": self._operators.get(operator, operator),
            },
            options={
                CONF_ENABLED_ENTITIES: DEFAULT_ENABLED_ENTITIES,
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            },
        )

    async def async_step_vehicle_monitoring(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle vehicle monitoring configuration."""
        errors: dict[str, str] = {}

        # Load operators on first visit
        if not self._operators:
            try:
                operators_data = await self._client.get_operators()
                # Parse operators (same as in stop monitoring)
                data_objects = (
                    operators_data.get("Siri", {})
                    .get("ServiceDelivery", {})
                    .get("DataObjectDelivery", [])
                )
                if isinstance(data_objects, list) and len(data_objects) > 0:
                    operators_list = (
                        data_objects[0].get("dataObjects", {}).get("Operator", [])
                    )
                    if not isinstance(operators_list, list):
                        operators_list = [operators_list]

                    for operator in operators_list:
                        op_id = operator.get("id", "")
                        op_name = operator.get("Name", {}).get("Text", op_id)
                        if op_id:
                            self._operators[op_id] = op_name
                else:
                    self._operators = {
                        "SF": "San Francisco Muni",
                        "BA": "BART",
                        "AC": "AC Transit",
                    }
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.warning("Could not fetch operators: %s", err)
                self._operators = {
                    "SF": "San Francisco Muni",
                    "BA": "BART",
                    "AC": "AC Transit",
                }

        if user_input is not None:
            operator = user_input[CONF_OPERATOR]
            vehicle_id = user_input[CONF_VEHICLE_ID]

            # Validate by fetching vehicle data
            try:
                await self._client.get_vehicle_monitoring(operator, vehicle_id)
            except Transit511ApiError:
                errors["base"] = ERROR_CANNOT_CONNECT
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception validating vehicle")
                errors["base"] = ERROR_UNKNOWN

            if not errors:
                # Create unique ID
                unique_id = f"{operator}_vehicle_{vehicle_id}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                # Create the config entry
                title = f"{self._operators.get(operator, operator)} Vehicle {vehicle_id}"

                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_API_KEY: self._api_key,
                        CONF_MONITORING_TYPE: MONITORING_TYPE_VEHICLE,
                        CONF_OPERATOR: operator,
                        CONF_VEHICLE_ID: vehicle_id,
                        "operator_name": self._operators.get(operator, operator),
                    },
                    options={
                        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_OPERATOR): vol.In(self._operators),
                vol.Required(CONF_VEHICLE_ID): str,
            }
        )

        return self.async_show_form(
            step_id="vehicle_monitoring",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> Transit511OptionsFlow:
        """Get the options flow for this handler."""
        return Transit511OptionsFlow(config_entry)


class Transit511OptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for 511 Transit."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # If API key was provided, validate it and update config entry data
            if CONF_API_KEY in user_input and user_input[CONF_API_KEY]:
                new_api_key = user_input[CONF_API_KEY]

                # Validate the new API key
                session = async_get_clientsession(self.hass)
                client = Transit511ApiClient(new_api_key, session)

                try:
                    await client.validate_api_key()
                except Transit511AuthError:
                    errors["base"] = ERROR_AUTH_FAILED
                except Transit511RateLimitError:
                    errors["base"] = ERROR_RATE_LIMIT
                except Transit511ApiError:
                    errors["base"] = ERROR_CANNOT_CONNECT
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception validating API key")
                    errors["base"] = ERROR_UNKNOWN

                if not errors:
                    # Update the config entry data with new API key
                    new_data = dict(self.config_entry.data)
                    new_data[CONF_API_KEY] = new_api_key
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data=new_data,
                    )
                    _LOGGER.info("API key updated for config entry: %s", self.config_entry.title)

                    # Remove API key from options before saving
                    options_data = {k: v for k, v in user_input.items() if k != CONF_API_KEY}
                    return self.async_create_entry(title="", data=options_data)

            if not errors:
                return self.async_create_entry(title="", data=user_input)

        monitoring_type = self.config_entry.data.get(CONF_MONITORING_TYPE)

        # Get current API key
        current_api_key = self.config_entry.data.get(CONF_API_KEY, "")

        if monitoring_type == MONITORING_TYPE_STOP:
            # Build entity selection options
            entity_options = {}
            for entity_type in ALL_ENTITY_TYPES:
                entity_options[entity_type] = entity_type.replace("_", " ").title()

            direction_options = {}
            for entity_type in DIRECTION_FILTERED_ENTITY_TYPES:
                direction_options[entity_type] = entity_type.replace("_", " ").title()

            schema = vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                    vol.Optional(
                        CONF_ENABLED_ENTITIES,
                        default=self.config_entry.options.get(
                            CONF_ENABLED_ENTITIES, DEFAULT_ENABLED_ENTITIES
                        ),
                    ): cv.multi_select(entity_options),
                    vol.Optional(
                        CONF_API_KEY,
                        description={"suggested_value": current_api_key},
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                            autocomplete="off",
                        ),
                    ),
                }
            )
        else:
            # Vehicle monitoring - just scan interval and API key
            schema = vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                    vol.Optional(
                        CONF_API_KEY,
                        description={"suggested_value": current_api_key},
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                            autocomplete="off",
                        ),
                    ),
                }
            )

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)


# Import for multi_select
from homeassistant.helpers import config_validation as cv  # noqa: E402
