"""A package containing concrete strategies for footnote and endnote processing."""

from .anomaly_strategy import AnomalyStrategy
from .aria_dpub_strategy import AriaDpubStrategy
from .base_strategy import (
    Anomaly,
    AnomalyCollector,
    BaseFootnoteStrategy,
    FootnoteStrategyError,
    normalize_href_attr,
)
from .native_convention_strategy import NativeConventionFootnoteStrategy
from .parameterized_strategy import ParameterizedFootnoteStrategy

__all__ = [
    "Anomaly",
    "AnomalyCollector",
    "AnomalyStrategy",
    "AriaDpubStrategy",
    "BaseFootnoteStrategy",
    "FootnoteStrategyError",
    "NativeConventionFootnoteStrategy",
    "ParameterizedFootnoteStrategy",
    "normalize_href_attr",
]
