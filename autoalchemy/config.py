import typing
from dataclasses import dataclass


@dataclass
class AutoInitConfig:
    """
    Config class for `auto_init` decorator.
    """

    get_attr: typing.Any = None
