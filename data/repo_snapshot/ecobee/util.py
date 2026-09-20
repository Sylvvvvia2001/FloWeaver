

from datetime import date, datetime, timedelta

import voluptuous as vol


def ecobee_date(date_string):

    try:
        datetime.strptime(date_string, "%Y-%m-%d")
    except ValueError as err:
        raise vol.Invalid("Date does not match ecobee date format YYYY-MM-DD") from err
    return date_string


def ecobee_time(time_string):

    try:
        datetime.strptime(time_string, "%H:%M:%S")
    except ValueError as err:
        raise vol.Invalid(
            "Time does not match ecobee 24-hour time format HH:MM:SS"
        ) from err
    return time_string


def is_indefinite_hold(start_date_string: str, end_date_string: str) -> bool:




    return date.fromisoformat(end_date_string) - date.fromisoformat(
        start_date_string
    ) > timedelta(days=365)
