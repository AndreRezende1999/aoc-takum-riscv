"""Exact posit codec and scalar ALU used as a numerical comparator.

The implementation follows the posit definition of Gustafson and Yonemoto
(2017): sign-magnitude, a variable-length regime, an optional exponent field
with ``es`` bits, and a fraction field.  Values are decoded to exact
``Fraction`` objects; arithmetic rounds once to the destination posit.
There is no quire and no IEEE-style infinity/NaN state: zero and NaR are the
only special values, and finite overflow saturates at maxpos.

The encoder searches the monotone positive code space and chooses the nearest
representable value, breaking exact ties by the even code.  That rule is
documented here because posit libraries differ in tie handling and because this
project uses posit only as a numerical baseline, not as an ISA proposal.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache


def _pow2(exponent: int) -> Fraction:
    return Fraction(1 << exponent) if exponent >= 0 else Fraction(1, 1 << -exponent)


def _floor_log2(value: Fraction) -> int:
    """Return floor(log2(value)) for a positive rational, without floats."""
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if value < _pow2(exponent):
        exponent -= 1
    return exponent


@lru_cache(maxsize=1 << 20)
def _decode_positive(nbits: int, es: int, raw: int) -> Fraction:
    """Decode an unsigned posit magnitude (1 <= raw < 2**(nbits-1))."""
    if not 1 <= raw < (1 << (nbits - 1)):
        raise ValueError("posit magnitude outside the positive code space")
    pos = nbits - 2
    first = (raw >> pos) & 1
    if first:
        run = 0
        while pos >= 0 and ((raw >> pos) & 1):
            run += 1
            pos -= 1
        regime = run - 1
        if pos >= 0:
            pos -= 1  # terminating zero
    else:
        run = 0
        while pos >= 0 and not ((raw >> pos) & 1):
            run += 1
            pos -= 1
        regime = -run
        if pos >= 0:
            pos -= 1  # terminating one

    exponent = 0
    for _ in range(es):
        exponent = (exponent << 1) | (1 if pos >= 0 and ((raw >> pos) & 1) else 0)
        pos -= 1

    fraction = 0
    fraction_width = 0
    while pos >= 0:
        fraction = (fraction << 1) | ((raw >> pos) & 1)
        fraction_width += 1
        pos -= 1

    scale = regime * (1 << es) + exponent
    significand = Fraction(1)
    if fraction_width:
        significand += Fraction(fraction, 1 << fraction_width)
    return significand * _pow2(scale)


@dataclass(frozen=True)
class Posit:
    """A posit format with ``nbits`` total bits and ``es`` exponent bits."""

    nbits: int
    es: int
    name: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.nbits, int) or not isinstance(self.es, int):
            raise TypeError("posit width and es must be integers")
        if self.nbits < 3 or self.es < 0 or self.es > self.nbits - 3:
            raise ValueError("invalid posit configuration")
        if not self.name:
            object.__setattr__(self, "name", f"posit{self.nbits},{self.es}")

    @property
    def _max_code(self) -> int:
        return (1 << (self.nbits - 1)) - 1

    @property
    def nar(self) -> int:
        return 1 << (self.nbits - 1)

    @property
    def maxpos(self) -> Fraction:
        return _decode_positive(self.nbits, self.es, self._max_code)

    @property
    def minpos(self) -> Fraction:
        return _decode_positive(self.nbits, self.es, 1)

    def _check(self, raw: int) -> None:
        if not isinstance(raw, int):
            raise TypeError("raw posit codes must be integers")
        if not 0 <= raw < (1 << self.nbits):
            raise ValueError("raw posit code outside the format width")

    def decode(self, raw: int) -> Fraction | None:
        self._check(raw)
        if raw == 0:
            return Fraction(0)
        if raw == self.nar:
            return None
        sign = raw >> (self.nbits - 1)
        magnitude = raw & self._max_code
        if magnitude == 0:
            return Fraction(0)
        value = _decode_positive(self.nbits, self.es, magnitude)
        return -value if sign else value

    def _encode_positive(self, value: Fraction) -> int:
        """Encode a positive finite value, saturating at maxpos."""
        if value <= 0:
            return 0
        maximum = self.maxpos
        if value >= maximum:
            return self._max_code
        minimum = self.minpos
        if value < minimum / 2:
            return 0
        if value == minimum / 2:
            return 0  # tie between zero (even) and minpos (odd)
        if value < minimum:
            return 1
        lo, hi = 1, self._max_code
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if _decode_positive(self.nbits, self.es, mid) <= value:
                lo = mid
            else:
                hi = mid - 1
        lower = _decode_positive(self.nbits, self.es, lo)
        if value == lower or lo == self._max_code:
            return lo
        upper = _decode_positive(self.nbits, self.es, lo + 1)
        midpoint = (lower + upper) / 2
        if value < midpoint:
            return lo
        if value > midpoint:
            return lo + 1
        return lo if lo % 2 == 0 else lo + 1

    def encode(self, value: Fraction | int | str | None) -> int:
        if value is None:
            return self.nar
        if not isinstance(value, (Fraction, int, str)):
            raise TypeError("encode expects Fraction, int, str, or None")
        number = Fraction(value)
        if number == 0:
            return 0
        negative = number < 0
        magnitude = self._encode_positive(abs(number))
        if magnitude == 0:
            return 0
        return (self.nar | magnitude) if negative else magnitude

    def add(self, left: int, right: int) -> int:
        a, b = self.decode(left), self.decode(right)
        return self.encode(None if a is None or b is None else a + b)

    def sub(self, left: int, right: int) -> int:
        a, b = self.decode(left), self.decode(right)
        return self.encode(None if a is None or b is None else a - b)

    def mul(self, left: int, right: int) -> int:
        a, b = self.decode(left), self.decode(right)
        return self.encode(None if a is None or b is None else a * b)


POSIT8 = Posit(8, 0)
POSIT8_2 = Posit(8, 2)
POSIT16 = Posit(16, 1)
POSIT16_2 = Posit(16, 2)
POSIT32 = Posit(32, 2)
POSIT64 = Posit(64, 3)
