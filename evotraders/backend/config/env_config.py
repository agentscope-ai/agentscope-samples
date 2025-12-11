#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple environment config helpers
"""
import os


def get_env_list(key: str, default: list = None) -> list:
    """Get comma-separated list from env"""
    value = os.getenv(key, "")
    if not value:
        return default or []
    return [item.strip() for item in value.split(",") if item.strip()]


def get_env_float(key: str, default: float = 0.0) -> float:
    """Get float from env"""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def get_env_int(key: str, default: int = 0) -> int:
    """Get int from env"""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default
