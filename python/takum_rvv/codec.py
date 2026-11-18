"""Independent exact-rational linear Takum codec and scalar ALU.

Representation: Hunhold, arXiv:2404.18603v2, Definition 8.
Tie-to-even bit rounding: arXiv:2408.10594v4, section 5.5.
No upstream implementation code is copied. None denotes NaR, never zero.
"""

from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from functools import lru_cache


_LOG_DEC_PREC = 80


def power2(exponent: int) -> Fraction:
    return Fraction(1 << exponent) if exponent >= 0 else Fraction(1, 1 << -exponent)


@dataclass(frozen=True)
class Fields:
    sign: int
    direction: int
    regime: int
    characteristic_bits: int
    characteristic: int
    fraction: Fraction
    fraction_width: int


def _fields(raw: int, bits: int) -> Fields:
    # Ghost bits to the right are zero when the characteristic is truncated.
    width = max(bits, 12)
    raw <<= width - bits
    sign = raw >> (width - 1)
    direction = (raw >> (width - 2)) & 1
    regime_code = (raw >> (width - 5)) & 7
    regime = regime_code if direction else 7 - regime_code
    p = width - 5 - regime
    characteristic_bits = (raw >> p) & ((1 << regime) - 1)
    c = ((1 << regime) - 1 if direction else 1 - (1 << (regime + 1)))
    return Fields(sign, direction, regime, characteristic_bits,
                  c + characteristic_bits,
                  Fraction(raw & ((1 << p) - 1), 1 << p), p)


@lru_cache(maxsize=32768)
def _decode(raw: int, bits: int) -> Fraction | None:
    if raw == 0:
        return Fraction(0)
    if raw == 1 << (bits - 1):
        return None
    f = _fields(raw, bits)
    exponent = (-1 if f.sign else 1) * (f.characteristic + f.sign)
    return (1 - 3 * f.sign + f.fraction) * power2(exponent)


@dataclass(frozen=True)
class Takum:
    bits: int

    def __post_init__(self):
        if self.bits not in (8, 16, 32, 64):
            raise ValueError("Takum supports 8, 16, 32 or 64 bits")

    @property
    def name(self):
        return f"takum_linear{self.bits}"

    @property
    def nar(self):
        return 1 << (self.bits - 1)

    def _check(self, raw):
        if not isinstance(raw, int) or not 0 <= raw < (1 << self.bits):
            raise ValueError("raw bit pattern outside the format width")

    def fields(self, raw: int) -> Fields:
        self._check(raw)
        return _fields(raw, self.bits)

    def decode(self, raw: int) -> Fraction | None:
        self._check(raw)
        return _decode(raw, self.bits)

    def encode(self, value) -> int:
        if value is None:
            return self.nar
        if not isinstance(value, (Fraction, int, str)):
            raise TypeError('encode expects Fraction, int, str or None; convert host floats explicitly')
        x = Fraction(value)
        if not x:
            return 0
        negative = x < 0
        x = abs(x)
        lo, hi = 1, self.nar - 1
        # Positive bit strings are strictly ordered. Find the lower neighbour.
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if _decode(mid, self.bits) <= x:
                lo = mid
            else:
                hi = mid - 1
        result = lo
        if lo < self.nar - 1:
            # A guard-bit boundary, including characteristic bits for T8.
            threshold = _decode(2 * lo + 1, self.bits + 1)
            if x > threshold or (x == threshold and lo & 1):
                result += 1
        return (-result) & ((1 << self.bits) - 1) if negative else result

    def convert(self, raw: int, target: "Takum") -> int:
        return target.encode(self.decode(raw))

    def add(self, a: int, b: int) -> int:
        x, y = self.decode(a), self.decode(b)
        return self.encode(None if x is None or y is None else x + y)

    def sub(self, a: int, b: int) -> int:
        x, y = self.decode(a), self.decode(b)
        return self.encode(None if x is None or y is None else x - y)

    def mul(self, a: int, b: int) -> int:
        x, y = self.decode(a), self.decode(b)
        return self.encode(None if x is None or y is None else x * y)


@lru_cache(maxsize=32768)
def _log_ell_pos(raw: int, bits: int) -> Fraction:
    """Exact rational logarithmic coordinate ell = c + m for 1 <= raw < 2^(bits-1)."""
    f = _fields(raw, bits)
    return f.characteristic + f.fraction


def _dec_fraction(value: Fraction) -> Decimal:
    return Decimal(value.numerator) / Decimal(value.denominator)


@lru_cache(maxsize=32768)
def _log_decode(raw: int, bits: int) -> Decimal | None:
    if raw == 0:
        return Decimal(0)
    if raw == 1 << (bits - 1):
        return None
    f = _fields(raw, bits)
    ell = f.characteristic + f.fraction
    if f.sign:
        ell = -ell
    with localcontext() as ctx:
        ctx.prec = _LOG_DEC_PREC
        mag = (_dec_fraction(ell) / Decimal(2)).exp()
        return -mag if f.sign else mag


@dataclass(frozen=True)
class LogTakum:
    """Logarithmic Takum codec and scalar ALU (Hunhold, arXiv:2404.18603v2, Def. 2)."""

    bits: int

    def __post_init__(self):
        if self.bits not in (8, 16, 32, 64):
            raise ValueError("LogTakum supports 8, 16, 32 or 64 bits")

    @property
    def name(self) -> str:
        return f"takum_log{self.bits}"

    @property
    def nar(self) -> int:
        return 1 << (self.bits - 1)

    def _check(self, raw: int) -> None:
        if not isinstance(raw, int) or not 0 <= raw < (1 << self.bits):
            raise ValueError("raw bit pattern outside the format width")

    def fields(self, raw: int) -> Fields:
        self._check(raw)
        return _fields(raw, self.bits)

    def decode(self, raw: int) -> Decimal | None:
        """Decode to high-precision Decimal (~80 digits); None denotes NaR."""
        self._check(raw)
        return _log_decode(raw, self.bits)

    def decode_ell(self, raw: int) -> tuple[int, Fraction] | None:
        """Return (sign_bit, signed_ell) for finite nonzero codes, else special."""
        self._check(raw)
        if raw == 0 or raw == self.nar:
            return None
        f = _fields(raw, self.bits)
        ell = f.characteristic + f.fraction
        return (f.sign, -ell if f.sign else ell)

    def encode_ell(self, ell: Fraction, negative: bool = False) -> int:
        """Encode a finite nonzero magnitude given exact ell = 2 * ln(|x|)."""
        lo, hi = 1, self.nar - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if _log_ell_pos(mid, self.bits) <= ell:
                lo = mid
            else:
                hi = mid - 1
        result = lo
        if lo < self.nar - 1:
            threshold = _log_ell_pos(2 * lo + 1, self.bits + 1)
            if ell > threshold or (ell == threshold and (lo & 1)):
                result += 1
        return (-result) & ((1 << self.bits) - 1) if negative else result

    def encode(self, value) -> int:
        """Encode Fraction, int, str, Decimal, or None using code-space RNE."""
        if value is None:
            return self.nar
        if isinstance(value, Decimal):
            if value.is_nan() or value.is_infinite():
                return self.nar
            if value == 0:
                return 0
            negative = value < 0
            dx = abs(value)
        elif isinstance(value, (Fraction, int, str)):
            x = Fraction(value)
            if not x:
                return 0
            negative = x < 0
            ax = abs(x)
            with localcontext() as ctx:
                ctx.prec = _LOG_DEC_PREC
                dx = Decimal(ax.numerator) / Decimal(ax.denominator)
        else:
            raise TypeError("encode expects Fraction, int, str, Decimal, or None")

        with localcontext() as ctx:
            ctx.prec = _LOG_DEC_PREC
            target_ell = Decimal(2) * dx.ln()
            lo, hi = 1, self.nar - 1
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if _dec_fraction(_log_ell_pos(mid, self.bits)) <= target_ell:
                    lo = mid
                else:
                    hi = mid - 1
            result = lo
            if lo < self.nar - 1:
                th_ell = _log_ell_pos(2 * lo + 1, self.bits + 1)
                th_dec = _dec_fraction(th_ell)
                if th_ell == 0 and isinstance(value, (Fraction, int, str)) and abs(Fraction(value)) == 1:
                    if lo & 1:
                        result += 1
                elif target_ell > th_dec:
                    result += 1
            return (-result) & ((1 << self.bits) - 1) if negative else result

    def add(self, a: int, b: int) -> int:
        x, y = self.decode(a), self.decode(b)
        if x is None or y is None:
            return self.nar
        with localcontext() as ctx:
            ctx.prec = _LOG_DEC_PREC
            return self.encode(x + y)

    def sub(self, a: int, b: int) -> int:
        x, y = self.decode(a), self.decode(b)
        if x is None or y is None:
            return self.nar
        with localcontext() as ctx:
            ctx.prec = _LOG_DEC_PREC
            return self.encode(x - y)

    def mul(self, a: int, b: int) -> int:
        self._check(a)
        self._check(b)
        if a == self.nar or b == self.nar:
            return self.nar
        if a == 0 or b == 0:
            return 0
        sa, la = self.decode_ell(a)  # type: ignore[misc]
        sb, lb = self.decode_ell(b)  # type: ignore[misc]
        return self.encode_ell(la + lb, negative=bool(sa ^ sb))

    def div(self, a: int, b: int) -> int:
        self._check(a)
        self._check(b)
        if a == self.nar or b == self.nar or b == 0:
            return self.nar
        if a == 0:
            return 0
        sa, la = self.decode_ell(a)  # type: ignore[misc]
        sb, lb = self.decode_ell(b)  # type: ignore[misc]
        return self.encode_ell(la - lb, negative=bool(sa ^ sb))


LOG_TAKUM8 = LogTakum(8)
LOG_TAKUM16 = LogTakum(16)
LOG_TAKUM32 = LogTakum(32)
LOG_TAKUM64 = LogTakum(64)
