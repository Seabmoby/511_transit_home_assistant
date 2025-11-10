"""API client for 511 Transit."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import async_timeout

from .const import (
    API_BASE_URL,
    ENDPOINT_HOLIDAYS,
    ENDPOINT_LINES,
    ENDPOINT_OPERATORS,
    ENDPOINT_PATTERNS,
    ENDPOINT_STOP_MONITORING,
    ENDPOINT_STOP_PLACES,
    ENDPOINT_STOP_TIMETABLE,
    ENDPOINT_STOPS,
    ENDPOINT_TIMETABLE,
    ENDPOINT_VEHICLE_MONITORING,
)

_LOGGER = logging.getLogger(__name__)


class Transit511ApiError(Exception):
    """Base exception for 511 Transit API errors."""


class Transit511AuthError(Transit511ApiError):
    """Exception for authentication errors."""


class Transit511RateLimitError(Transit511ApiError):
    """Exception for rate limit errors."""


class Transit511ApiClient:
    """Client for interacting with the 511 Transit API."""

    def __init__(
        self,
        api_key: str,
        session: aiohttp.ClientSession,
        enable_api_logging: bool = False,
    ) -> None:
        """Initialize the API client.

        Args:
            api_key: The 511 API key
            session: The aiohttp client session
            enable_api_logging: Whether to log API calls

        """
        self._api_key = api_key
        self._session = session
        self.enable_api_logging = enable_api_logging

    async def _make_request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a request to the 511 API.

        Args:
            endpoint: The API endpoint
            params: Query parameters

        Returns:
            The JSON response

        Raises:
            Transit511AuthError: If authentication fails
            Transit511RateLimitError: If rate limit is exceeded
            Transit511ApiError: For other API errors

        """
        url = f"{API_BASE_URL}/{endpoint}"

        # Add API key and JSON format to params
        request_params = {"api_key": self._api_key, "format": "JSON"}
        if params:
            request_params.update(params)

        # Log API call with clear marker (if enabled)
        if self.enable_api_logging:
            _LOGGER.info(
                "🚀 API CALL - Endpoint: %s | Params: %s",
                endpoint,
                {k: v for k, v in params.items() if k != "api_key"} if params else {}
            )

        try:
            async with async_timeout.timeout(20):
                _LOGGER.debug("Making request to %s with params: %s", url, request_params)
                response = await self._session.get(url, params=request_params)
                _LOGGER.debug("Response status: %s", response.status)

                # Check for rate limit
                if response.status == 429:
                    _LOGGER.error("Rate limit exceeded for 511 API")
                    raise Transit511RateLimitError("Rate limit exceeded")

                # Check for auth errors
                if response.status == 401 or response.status == 403:
                    _LOGGER.error("Authentication failed for 511 API")
                    raise Transit511AuthError("Authentication failed")

                response.raise_for_status()

                # Get response text and strip BOM if present
                text = await response.text()
                text = text.replace("\ufeff", "").strip()

                # Check for rate limit message in response
                if text.startswith("The allowed number of requests"):
                    _LOGGER.error("Rate limit message in response: %s", text)
                    raise Transit511RateLimitError(text)

                # Parse JSON
                if not text:
                    _LOGGER.error("Empty response from API")
                    raise Transit511ApiError("Empty response from API")

                if not text.startswith("{") and not text.startswith("["):
                    _LOGGER.error("Invalid JSON response (first 200 chars): %s", text[:200])
                    raise Transit511ApiError(f"Invalid JSON response: {text[:100]}")

                try:
                    import json
                    return json.loads(text)
                except json.JSONDecodeError as err:
                    _LOGGER.error("JSON decode error: %s, Response: %s", err, text[:200])
                    raise Transit511ApiError(f"Failed to parse JSON: {err}") from err

        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout fetching data from 511 API: %s", err)
            raise Transit511ApiError("Timeout fetching data") from err
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching data from 511 API: %s", err)
            raise Transit511ApiError(f"Error fetching data: {err}") from err

    async def validate_api_key(self) -> bool:
        """Validate the API key by making a simple test request.

        Returns:
            True if the API key is valid

        Raises:
            Transit511AuthError: If authentication fails
            Transit511ApiError: For other errors

        """
        try:
            # Use StopMonitoring with SF agency as a simple validation
            # This is more reliable than operators endpoint
            await self.get_stop_monitoring("SF")
            return True
        except Transit511AuthError:
            raise
        except Transit511ApiError:
            raise

    async def get_stop_monitoring(
        self,
        agency: str,
        stop_code: str | None = None,
    ) -> dict[str, Any]:
        """Get stop monitoring data.

        Args:
            agency: The transit agency/operator ID
            stop_code: The stop code (optional)

        Returns:
            The stop monitoring data

        """
        params = {"agency": agency}
        if stop_code:
            params["stopCode"] = stop_code

        return await self._make_request(ENDPOINT_STOP_MONITORING, params)

    async def get_vehicle_monitoring(
        self,
        agency: str,
        vehicle_id: str | None = None,
    ) -> dict[str, Any]:
        """Get vehicle monitoring data.

        Args:
            agency: The transit agency/operator ID
            vehicle_id: The vehicle ID (optional)

        Returns:
            The vehicle monitoring data

        """
        params = {"agency": agency}
        if vehicle_id:
            params["vehicleID"] = vehicle_id

        return await self._make_request(ENDPOINT_VEHICLE_MONITORING, params)

    async def get_operators(
        self,
        operator_id: str | None = None,
    ) -> dict[str, Any]:
        """Get list of transit operators.

        Args:
            operator_id: The operator ID (optional)

        Returns:
            The operators data

        """
        params = {}
        if operator_id:
            params["operator_id"] = operator_id

        return await self._make_request(ENDPOINT_OPERATORS, params)

    async def get_lines(
        self,
        operator_id: str,
        line_id: str | None = None,
    ) -> dict[str, Any]:
        """Get lines/routes for an operator.

        Args:
            operator_id: The operator ID
            line_id: The line ID (optional)

        Returns:
            The lines data

        """
        params = {"operator_id": operator_id}
        if line_id:
            params["line_id"] = line_id

        return await self._make_request(ENDPOINT_LINES, params)

    async def get_stops(
        self,
        operator_id: str,
        line_id: str | None = None,
        direction_id: str | None = None,
    ) -> dict[str, Any]:
        """Get stops for an operator.

        Args:
            operator_id: The operator ID
            line_id: The line ID (optional)
            direction_id: The direction ID (optional)

        Returns:
            The stops data

        """
        params = {"operator_id": operator_id}
        if line_id:
            params["line_id"] = line_id
        if direction_id:
            params["Direction_id"] = direction_id

        return await self._make_request(ENDPOINT_STOPS, params)

    async def get_stop_places(
        self,
        operator_id: str,
        stop_id: str | None = None,
    ) -> dict[str, Any]:
        """Get stop places for an operator.

        Args:
            operator_id: The operator ID
            stop_id: The stop ID (optional)

        Returns:
            The stop places data

        """
        params = {"operator_id": operator_id}
        if stop_id:
            params["stop_id"] = stop_id

        return await self._make_request(ENDPOINT_STOP_PLACES, params)

    async def get_patterns(
        self,
        operator_id: str,
        line_id: str,
        pattern_id: str | None = None,
    ) -> dict[str, Any]:
        """Get patterns for a line.

        Args:
            operator_id: The operator ID
            line_id: The line ID
            pattern_id: The pattern ID (optional)

        Returns:
            The patterns data

        """
        params = {"operator_id": operator_id, "line_id": line_id}
        if pattern_id:
            params["pattern_id"] = pattern_id

        return await self._make_request(ENDPOINT_PATTERNS, params)

    async def get_timetable(
        self,
        operator_id: str,
        line_id: str,
    ) -> dict[str, Any]:
        """Get timetable for a line.

        Args:
            operator_id: The operator ID
            line_id: The line ID

        Returns:
            The timetable data

        """
        params = {"operator_id": operator_id, "line_id": line_id}
        return await self._make_request(ENDPOINT_TIMETABLE, params)

    async def get_stop_timetable(
        self,
        operator_ref: str,
        monitoring_ref: str,
        line_ref: str | None = None,
    ) -> dict[str, Any]:
        """Get scheduled departures at a stop.

        Args:
            operator_ref: The operator reference
            monitoring_ref: The stop monitoring reference
            line_ref: The line reference (optional)

        Returns:
            The stop timetable data

        """
        params = {"operatorref": operator_ref, "monitoringref": monitoring_ref}
        if line_ref:
            params["lineref"] = line_ref

        return await self._make_request(ENDPOINT_STOP_TIMETABLE, params)

    async def get_holidays(
        self,
        operator_id: str,
    ) -> dict[str, Any]:
        """Get service holidays for an operator.

        Args:
            operator_id: The operator ID

        Returns:
            The holidays data

        """
        params = {"operator_id": operator_id}
        return await self._make_request(ENDPOINT_HOLIDAYS, params)
