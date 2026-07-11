"""Weather lookup utilities."""

from __future__ import annotations

import os
from typing import Any


def get_weather_current(location: str, timeout: int = 10) -> dict[str, Any]:
    """
    Get current weather

    Args:
        location (str): Location
        timeout (int): Timeout in seconds

    Returns:
        str: Weather
    """
    # Lazy import requests
    import requests

    if location == "auto":
        location = "auto:ip"

    response = requests.get(
        f"https://api.weatherapi.com/v1/current.json?key={os.environ.get('WEATHERAPI_KEY')}&q={location}&aqi=no",
        timeout=timeout,
    )
    return response.json()


def get_weather_forecast(location: str, num_days: int, timeout: int = 10) -> dict[str, Any]:
    """
    Get weather forecast for next days

    Args:
        location (str): Location
        num_days (int): Number of days
        timeout (int): Timeout in seconds

    Returns:
        str: Weather
    """
    # Lazy import requests
    import requests

    if location == "auto":
        location = "auto:ip"

    response = requests.get(
        f"https://api.weatherapi.com/v1/forecast.json?key={os.environ.get('WEATHERAPI_KEY')}&q={location}&days={num_days}&aqi=no&alerts=no",
        timeout=timeout,
    )
    return response.json()
