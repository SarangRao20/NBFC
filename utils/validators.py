"""Input validation utilities."""

import re


def normalize_phone(phone: str) -> str:
    """Normalize phone input to a 10-digit Indian mobile number when possible."""
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if len(digits) > 10:
        # Handle +91/91 prefixes and generic country codes by keeping the last 10 digits.
        digits = digits[-10:]
    return digits


def validate_phone(phone: str) -> tuple[bool, str]:
    phone = normalize_phone(phone)
    if not re.fullmatch(r"\d{10}", phone):
        return False, "Phone must be exactly 10 digits."
    return True, ""


def validate_email(email: str) -> tuple[bool, str]:
    email = email.strip()
    if email == "":
        return True, ""
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return False, "Invalid email format."
    return True, ""


def validate_pan(pan: str) -> tuple[bool, str]:
    pan = pan.strip().upper()
    if not re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", pan):
        return False, "PAN must be in format ABCDE1234F."
    return True, ""


def validate_pin(pin: str) -> tuple[bool, str]:
    pin = pin.strip()
    if not re.fullmatch(r"\d{4}", pin):
        return False, "PIN must be exactly 4 digits."
    return True, ""


def validate_positive_number(value: str, field_name: str = "Value") -> tuple[bool, str]:
    try:
        num = float(value.strip())
        if num <= 0:
            return False, f"{field_name} must be greater than 0."
        return True, ""
    except ValueError:
        return False, f"{field_name} must be a valid number."


