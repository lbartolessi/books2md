"""A package containing concrete strategies for footnote and endnote processing."""

from .anomaly_strategy import AnomalyStrategy
from .aria_dpub_strategy import AriaDpubStrategy
from .base_strategy import BaseFootnoteStrategy, FootnoteStrategyError
from .native_convention_strategy import NativeConventionFootnoteStrategy
from .parameterized_strategy import ParameterizedFootnoteStrategy

__all__ = [
    "AnomalyStrategy",
    "AriaDpubStrategy",
    "BaseFootnoteStrategy",
    "FootnoteStrategyError",
    "NativeConventionFootnoteStrategy",
    "ParameterizedFootnoteStrategy",
]
