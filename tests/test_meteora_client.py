from unittest.mock import MagicMock

import pytest

from dlmm_position_lab.meteora_client import get_pool


def pool_payload() -> dict[str, object]:
    token = {
        "address": "token-address",
        "name": "Token",
        "symbol": "TOK",
        "decimals": 6,
        "price": 1.0,
    }
    return {
        "address": "pool-address",
        "name": "TOK-USDC",
        "current_price": 1.01,
        "tvl": 5000,
        "dynamic_fee_pct": 0.2,
        "token_x": token,
        "token_y": {**token, "symbol": "USDC"},
        "pool_config": {
            "bin_step": 10,
            "base_fee_pct": 0.1,
            "max_fee_pct": 1,
            "collect_fee_mode": 0,
        },
        "volume": {"24h": 1000},
        "fees": {"24h": 10},
        "unused_api_field": "ignored",
    }


def test_get_pool_fetches_and_parses_current_state() -> None:
    response = MagicMock()
    response.json.return_value = pool_payload()
    client = MagicMock()
    client.get.return_value = response

    pool = get_pool(
        " pool-address ", client=client, base_url="https://meteora.test"
    )

    client.get.assert_called_once_with("https://meteora.test/pools/pool-address")
    response.raise_for_status.assert_called_once()
    assert pool.address == "pool-address"
    assert pool.token_y.symbol == "USDC"
    assert pool.pool_config.bin_step == 10


def test_get_pool_requires_an_address() -> None:
    with pytest.raises(ValueError, match="pool_address must not be empty"):
        get_pool(" ")
