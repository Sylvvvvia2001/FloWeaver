

import re

from aiohomeconnect.model.error import HomeConnectError

RE_CAMEL_CASE = re.compile(r"(?<!^)(?=[A-Z])|(?=\d)(?<=\D)")


def get_dict_from_home_connect_error(
    err: HomeConnectError,
) -> dict[str, str]:

    return {"error": str(err)}


def bsh_key_to_translation_key(bsh_key: str) -> str:





    return "_".join(
        RE_CAMEL_CASE.sub("_", split) for split in bsh_key.split(".")
    ).lower()
