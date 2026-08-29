import re
from datetime import datetime


class ValidationError(Exception):
    """A custom error we raise when user input is invalid."""
    pass


LOCATION_NAME_PATTERN = re.compile(r"^[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-',]{1,79}$")

DECIMAL_NUMBER_PATTERN = re.compile(r"^-?\d{1,3}(\.\d+)?$")

DATE_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")


def validate_location_name(name: str) -> str:
    name = name.strip()
    if not LOCATION_NAME_PATTERN.match(name):
        raise ValidationError("Location name must be 2-80 letters, spaces, hyphens, apostrophes, or commas.")
    return name


def validate_coordinate(value: str, kind: str = "latitude") -> float:
    value = str(value).strip()
    if not DECIMAL_NUMBER_PATTERN.match(value):
        raise ValidationError(f"{kind} must be a decimal number, e.g. '9.0765'.")
    number = float(value)
    if kind == "latitude" and not