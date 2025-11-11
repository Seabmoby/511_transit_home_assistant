"""Config flow for 511 Transit integration - Version 2.0."""
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
from homeassistant.helpers import config_validation as cv

from .api import (
    Transit511ApiClient,
    Transit511ApiError,
    Transit511AuthError,
    Transit511RateLimitError,
)
from .const import (
    ALL_ENTITY_TYPES,
    CONF_API_KEY,
    CONF_ENABLE_API_LOGGING,
    CONF_ENABLED_ENTITIES,
    CONF_LINE_ID,
    CONF_MONITORING_TYPE,
    CONF_OPERATOR,
    CONF_STOP_CODE,
    CONF_STOPS,
    CONF_VEHICLE_ID,
    CONF_VEHICLES,
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
    """Handle a config flow for 511 Transit - creates operator+type services."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._api_key: str | None = None
        self._client: Transit511ApiClient | None = None
        self._operator: str | None = None
        self._operator_name: str | None = None
        self._monitoring_type: str | None = None

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
        existing_api_key = self._get_existing_api_key()

        if existing_api_key:
            self._api_key = existing_api_key
            session = async_get_clientsession(self.hass)
            self._client = Transit511ApiClient(existing_api_key, session)
            return await self.async_step_operator()

        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
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
            except Exception:
                _LOGGER.exception("Unexpected exception validating API key")
                errors["base"] = ERROR_UNKNOWN

            if not errors:
                self._api_key = api_key
                self._client = client
                return await self.async_step_operator()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
            description_placeholders={
                "note": "Enter your 511.org API key. It will be saved and reused for all services."
            },
        )

    async def async_step_operator(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle operator selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            operator_full = user_input[CONF_OPERATOR]
            # Format: "SF - San Francisco Muni"
            operator = operator_full.split(" - ")[0]
            operator_name = operator_full.split(" - ")[1] if " - " in operator_full else operator

            self._operator = operator
            self._operator_name = operator_name
            return await self.async_step_monitoring_type()

        # Fetch operators
        try:
            operators_data = await self._client.get_operators()
            operators_list = operators_data if isinstance(operators_data, list) else []
            operators_dict = {}
            for op in operators_list:
                op_id = op.get("Id", "")
                op_name = op.get("Name", op_id)
                operators_dict[f"{op_id} - {op_name}"] = f"{op_name} ({op_id})"
        except Exception:
            _LOGGER.exception("Error fetching operators")
            errors["base"] = ERROR_CANNOT_CONNECT
            operators_dict = {}

        return self.async_show_form(
            step_id="operator",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_OPERATOR): vol.In(operators_dict),
                }
            ),
            errors=errors,
        )

    async def async_step_monitoring_type(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle monitoring type selection."""
        if user_input is not None:
            self._monitoring_type = user_input[CONF_MONITORING_TYPE]

            # Check if this combination already exists
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if (
                    entry.data.get(CONF_OPERATOR) == self._operator
                    and entry.data.get(CONF_MONITORING_TYPE) == self._monitoring_type
                ):
                    return self.async_abort(reason="already_configured")

            # Create the service entry (initially empty, user adds stops/vehicles via options)
            title = f"{self._operator_name} - {'Stops' if self._monitoring_type == MONITORING_TYPE_STOP else 'Vehicles'}"

            data = {
                CONF_API_KEY: self._api_key,
                CONF_OPERATOR: self._operator,
                "operator_name": self._operator_name,
                CONF_MONITORING_TYPE: self._monitoring_type,
            }

            if self._monitoring_type == MONITORING_TYPE_STOP:
                data[CONF_STOPS] = []
            else:
                data[CONF_VEHICLES] = []

            return self.async_create_entry(title=title, data=data)

        return self.async_show_form(
            step_id="monitoring_type",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MONITORING_TYPE): vol.In(
                        {
                            MONITORING_TYPE_STOP: "Stop Monitoring (track arrivals at stops)",
                            MONITORING_TYPE_VEHICLE: "Vehicle Monitoring (track specific vehicles)",
                        }
                    ),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return Transit511OptionsFlowHandler(config_entry)


class Transit511OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for 511 Transit."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._client: Transit511ApiClient | None = None
        self._new_stop_data: dict[str, Any] = {}
        self._new_vehicle_data: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options - show main menu."""
        monitoring_type = self.config_entry.data.get(CONF_MONITORING_TYPE)

        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "add_stop" if monitoring_type == MONITORING_TYPE_STOP else "add_vehicle",
                "remove_stop" if monitoring_type == MONITORING_TYPE_STOP else "remove_vehicle",
                "settings",
            ],
        )

    async def async_step_add_stop(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a new stop to this service."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate stop code
            api_key = self.config_entry.data[CONF_API_KEY]
            operator = self.config_entry.data[CONF_OPERATOR]
            stop_code = user_input[CONF_STOP_CODE]
            line_id = user_input.get(CONF_LINE_ID, "")

            session = async_get_clientsession(self.hass)
            client = Transit511ApiClient(api_key, session)

            try:
                # Test the stop
                await client.get_stop_monitoring(operator, stop_code)

                # Add stop to config
                new_data = dict(self.config_entry.data)
                stops = list(new_data.get(CONF_STOPS, []))

                # Check if stop already exists
                if any(s.get("stop_code") == stop_code and s.get("line_id") == line_id for s in stops):
                    errors["base"] = "already_configured"
                else:
                    stops.append({
                        "stop_code": stop_code,
                        "line_id": line_id,
                        "stop_name": stop_code,  # Will be updated on first fetch
                    })
                    new_data[CONF_STOPS] = stops

                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data=new_data,
                    )
                    await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                    # Get scan interval from options
                    scan_interval = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

                    return self.async_abort(
                        reason="stop_added",
                        description_placeholders={
                            "stop_code": stop_code,
                            "scan_interval": str(scan_interval),
                        },
                    )
            except Exception:
                _LOGGER.exception("Error adding stop")
                errors["base"] = ERROR_INVALID_STOP

        return self.async_show_form(
            step_id="add_stop",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STOP_CODE): str,
                    vol.Optional(CONF_LINE_ID, default=""): str,
                }
            ),
            errors=errors,
        )

    async def async_step_add_vehicle(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a new vehicle to this service."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = self.config_entry.data[CONF_API_KEY]
            operator = self.config_entry.data[CONF_OPERATOR]
            vehicle_id = user_input[CONF_VEHICLE_ID]

            session = async_get_clientsession(self.hass)
            client = Transit511ApiClient(api_key, session)

            try:
                # Test the vehicle
                await client.get_vehicle_monitoring(operator, vehicle_id)

                # Add vehicle to config
                new_data = dict(self.config_entry.data)
                vehicles = list(new_data.get(CONF_VEHICLES, []))

                if vehicle_id in [v.get("vehicle_id") for v in vehicles]:
                    errors["base"] = "already_configured"
                else:
                    vehicles.append({"vehicle_id": vehicle_id})
                    new_data[CONF_VEHICLES] = vehicles

                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data=new_data,
                    )
                    await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                    # Get scan interval from options
                    scan_interval = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

                    return self.async_abort(
                        reason="vehicle_added",
                        description_placeholders={
                            "vehicle_id": vehicle_id,
                            "scan_interval": str(scan_interval),
                        },
                    )
            except Exception:
                _LOGGER.exception("Error adding vehicle")
                errors["base"] = "invalid_vehicle"

        return self.async_show_form(
            step_id="add_vehicle",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_VEHICLE_ID): str,
                }
            ),
            errors=errors,
        )

    async def async_step_remove_stop(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove a stop from this service."""
        stops = self.config_entry.data.get(CONF_STOPS, [])

        if not stops:
            return self.async_abort(reason="no_stops")

        if user_input is not None:
            stop_to_remove = user_input["stop_to_remove"]

            new_data = dict(self.config_entry.data)
            new_stops = [s for s in stops if f"{s['stop_code']}_{s.get('line_id', '')}" != stop_to_remove]
            new_data[CONF_STOPS] = new_stops

            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=new_data,
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        # Build stop options
        stop_options = {}
        for stop in stops:
            stop_code = stop.get("stop_code")
            line_id = stop.get("line_id", "")
            stop_name = stop.get("stop_name", stop_code)
            key = f"{stop_code}_{line_id}"
            label = f"{stop_name} ({stop_code})" + (f" - Line {line_id}" if line_id else "")
            stop_options[key] = label

        return self.async_show_form(
            step_id="remove_stop",
            data_schema=vol.Schema(
                {
                    vol.Required("stop_to_remove"): vol.In(stop_options),
                }
            ),
        )

    async def async_step_remove_vehicle(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove a vehicle from this service."""
        vehicles = self.config_entry.data.get(CONF_VEHICLES, [])

        if not vehicles:
            return self.async_abort(reason="no_vehicles")

        if user_input is not None:
            vehicle_to_remove = user_input["vehicle_to_remove"]

            new_data = dict(self.config_entry.data)
            new_vehicles = [v for v in vehicles if v["vehicle_id"] != vehicle_to_remove]
            new_data[CONF_VEHICLES] = new_vehicles

            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=new_data,
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        vehicle_options = {}
        for vehicle in vehicles:
            vehicle_id = vehicle["vehicle_id"]
            vehicle_options[vehicle_id] = f"Vehicle {vehicle_id}"

        return self.async_show_form(
            step_id="remove_vehicle",
            data_schema=vol.Schema(
                {
                    vol.Required("vehicle_to_remove"): vol.In(vehicle_options),
                }
            ),
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Handle API key update if provided
            if CONF_API_KEY in user_input and user_input[CONF_API_KEY]:
                new_api_key = user_input[CONF_API_KEY]
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
                except Exception:
                    _LOGGER.exception("Unexpected exception validating API key")
                    errors["base"] = ERROR_UNKNOWN

                if not errors:
                    new_data = dict(self.config_entry.data)
                    new_data[CONF_API_KEY] = new_api_key
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data=new_data,
                    )
                    _LOGGER.info("API key updated for config entry: %s", self.config_entry.title)

            if not errors:
                # Remove API key from options before saving
                options_data = {k: v for k, v in user_input.items() if k != CONF_API_KEY}
                return self.async_create_entry(title="", data=options_data)

        # Get current values
        current_api_key = self.config_entry.data.get(CONF_API_KEY, "")
        monitoring_type = self.config_entry.data.get(CONF_MONITORING_TYPE)

        schema_dict = {
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
                CONF_ENABLE_API_LOGGING,
                default=self.config_entry.options.get(
                    CONF_ENABLE_API_LOGGING, False
                ),
            ): selector.BooleanSelector(),
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

        # Add entity selection for stop monitoring
        if monitoring_type == MONITORING_TYPE_STOP:
            entity_options = {}
            for entity_type in ALL_ENTITY_TYPES:
                entity_options[entity_type] = entity_type.replace("_", " ").title()

            schema_dict[vol.Optional(
                CONF_ENABLED_ENTITIES,
                default=self.config_entry.options.get(
                    CONF_ENABLED_ENTITIES, DEFAULT_ENABLED_ENTITIES
                ),
            )] = cv.multi_select(entity_options)

        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )
