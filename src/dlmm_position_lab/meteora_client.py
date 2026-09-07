"""Minimal read-only client for the Meteora DLMM Data API."""

import os
from typing import Any

import httpx
from pydantic import ValidationError

from dlmm_position_lab.models import Pool

DEFAULT_BASE_URL = "https://dlmm.datapi.meteora.ag"
DEFAULT_TIMEOUT_SECONDS = 10.0


class MeteoraAPIError(RuntimeError):
    """Raised when current pool data cannot be retrieved or parsed."""


def meteora_base_url() -> str:
    return os.getenv("METEORA_API_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def get_pool(
    pool_address: str,
    *,
    client: Any | None = None,
    base_url: str | None = None,
) -> Pool:
    """Fetch metadata and current state for one DLMM pool."""
    address = pool_address.strip()
    if not address:
        raise ValueError("pool_address must not be empty")

    owns_client = client is None
    http_client = client or httpx.Client(
        timeout=DEFAULT_TIMEOUT_SECONDS,
        transport=httpx.HTTPTransport(retries=2),
    )
    try:
        response = http_client.get(f"{base_url or meteora_base_url()}/pools/{address}")
        response.raise_for_status()
        return Pool.model_validate(response.json())
    except (httpx.HTTPError, ValidationError) as error:
        raise MeteoraAPIError(f"Meteora pool request failed: {error}") from error
    finally:
        if owns_client:
            http_client.close()
