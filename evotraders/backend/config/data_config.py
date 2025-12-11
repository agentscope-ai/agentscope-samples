# -*- coding: utf-8 -*-
"""
Centralized Data Source Configuration

Auto-detects and manages data source based on available API keys.
Priority: FINNHUB_API_KEY > FINANCIAL_DATASETS_API_KEY
"""
import os
from dataclasses import dataclass
from typing import Literal, Optional

DataSource = Literal["finnhub", "financial_datasets"]


@dataclass
class DataSourceConfig:
    """Immutable data source configuration"""

    source: DataSource
    api_key: str


# Module-level cache for the resolved configuration
_config_cache: Optional[DataSourceConfig] = None


def _resolve_config() -> DataSourceConfig:
    """
    Resolve data source configuration based on available API keys.

    Priority:
    1. FINNHUB_API_KEY (if set)
    2. FINANCIAL_DATASETS_API_KEY (if set)
    3. Raises error if neither is available
    """
    # Check for Finnhub API key first (higher priority)
    finnhub_key = os.getenv("FINNHUB_API_KEY")
    if finnhub_key:
        return DataSourceConfig(source="finnhub", api_key=finnhub_key)

    # Fallback to Financial Datasets API
    fd_key = os.getenv("FINANCIAL_DATASETS_API_KEY")
    if fd_key:
        return DataSourceConfig(source="financial_datasets", api_key=fd_key)

    # No API key available
    raise ValueError(
        "No API key found. Please set either FINNHUB_API_KEY or "
        "FINANCIAL_DATASETS_API_KEY in your .env file.",
    )


def get_config() -> DataSourceConfig:
    """
    Get the resolved data source configuration (cached).

    Returns:
        DataSourceConfig with source and api_key

    Raises:
        ValueError: If no API key is configured
    """
    global _config_cache
    if _config_cache is None:
        _config_cache = _resolve_config()
    return _config_cache


def get_data_source() -> DataSource:
    """Get the configured data source name."""
    return get_config().source


def get_api_key() -> str:
    """Get the API key for the configured data source."""
    return get_config().api_key


def reset_config() -> None:
    """Reset the cached configuration (useful for testing)."""
    global _config_cache
    _config_cache = None
