# -*- coding: utf-8 -*-
from datetime import datetime, timezone

from sqlmodel import Field


def email_field():
    """The email field"""
    return Field(unique=True, index=True, max_length=255)


def username_field():
    """The username field"""
    return Field(default=None, min_length=1, max_length=255)


def password_field():
    """The password field"""
    return Field(default=None, min_length=2, max_length=40)


def utc_datetime_field():
    """The utc datetime field"""
    return Field(default_factory=lambda: datetime.now(timezone.utc))


def formatted_datetime_field():
    """The formatted datetime field"""
    return Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )


def verification_code_field():
    """The verification code field"""
    return Field(min_length=6, max_length=6)
