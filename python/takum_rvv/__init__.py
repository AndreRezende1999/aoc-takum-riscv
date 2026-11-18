"""Functional Takum/RVV and numerical-format research model. See docs/05_solucao_python.md."""

from .codec import Takum, LogTakum, LOG_TAKUM8, LOG_TAKUM16, LOG_TAKUM32, LOG_TAKUM64
from .posit import Posit, POSIT8, POSIT8_2, POSIT16, POSIT16_2, POSIT32, POSIT64

__all__ = [
    "Takum",
    "LogTakum",
    "LOG_TAKUM8",
    "LOG_TAKUM16",
    "LOG_TAKUM32",
    "LOG_TAKUM64",
    "Posit",
    "POSIT8",
    "POSIT8_2",
    "POSIT16",
    "POSIT16_2",
    "POSIT32",
    "POSIT64",
]
