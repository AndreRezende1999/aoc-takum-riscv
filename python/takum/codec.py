"""Codec Takum linear em racionais exatos e ALU escalar (gabarito da Fase 1).

Representação: Hunhold, arXiv:2404.18603v2, Definição 8 (variante linear).
Arredondamento para o par no código: arXiv:2408.10594v4, seção 5.5.
Nenhum código da implementação de origem foi copiado.  ``None`` representa o
NaR (nunca o zero); ``Fraction(0)`` representa o zero.

Este módulo é o gabarito independente do núcleo C++ (src/takum.cpp): os
vetores dourados de tests/golden/ são gerados a partir dele, e os testes de
python/tests/ o conferem, inclusive contra a tabela externa da libtakum.
A especificação usada aqui está em docs/fase1.md.
"""

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache


def power2(exponent: int) -> Fraction:
    """Devolve 2^exponent como Fraction exata (o expoente pode ser negativo)."""
    return Fraction(1 << exponent) if exponent >= 0 else Fraction(1, 1 << -exponent)


@dataclass(frozen=True)
class Fields:
    """Campos S, D, R, C e F extraídos de um código Takum de n bits.

    - sign: S (0 positivo, 1 negativo);
    - direction: D (0 abaixo de 1, 1 acima de 1);
    - regime: r efetivo (R se D = 1; 7 - R se D = 0);
    - characteristic_bits: C (os r bits de característica);
    - characteristic: c combinada, usada na fórmula do expoente;
    - fraction: F como fração exata (bits crus divididos por 2^p);
    - fraction_width: p, o número de bits de fração.
    """

    sign: int
    direction: int
    regime: int
    characteristic_bits: int
    characteristic: int
    fraction: Fraction
    fraction_width: int


def _fields(raw: int, bits: int) -> Fields:
    # Zeros fantasmas à direita quando a característica é truncada (n < 12).
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
    """Decodifica exatamente: 0 -> Fraction(0); NaR -> None (com cache)."""
    if raw == 0:
        return Fraction(0)
    if raw == 1 << (bits - 1):
        return None
    f = _fields(raw, bits)
    exponent = (-1 if f.sign else 1) * (f.characteristic + f.sign)
    return (1 - 3 * f.sign + f.fraction) * power2(exponent)


@dataclass(frozen=True)
class Takum:
    """Codec e ALU de Takum linear para uma largura fixa (8, 16, 32 ou 64).

    Os métodos recebem e devolvem códigos inteiros (não o valor); os
    intermediários são frações exatas e o arredondamento acontece uma única
    vez, na codificação.  Ver docs/fase1.md para os algoritmos.
    """

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
        """Extrai S, D, R, C e F do código, sem resolver zero/NaR nem o valor."""
        self._check(raw)
        return _fields(raw, self.bits)

    def decode(self, raw: int) -> Fraction | None:
        """Decodifica o código no valor exato; zero -> 0 e NaR -> None."""
        self._check(raw)
        return _decode(raw, self.bits)

    def encode(self, value) -> int:
        """Codifica um valor exato, arredondando para o par no código.

        Aceita Fraction, int ou str (convertidos exatamente); None gera o NaR.
        Valores acima do máximo saturam e valores positivos abaixo do mínimo
        saturam no menor positivo; não há infinito.
        """
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
        # As cadeias de bits positivas são estritamente ordenadas: busca
        # binária pelo vizinho de baixo do valor.
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if _decode(mid, self.bits) <= x:
                lo = mid
            else:
                hi = mid - 1
        result = lo
        if lo < self.nar - 1:
            # Fronteira de bit de guarda, já na largura n+1 (inclui bits de
            # característica em T8); empate sobe apenas se lo for ímpar.
            threshold = _decode(2 * lo + 1, self.bits + 1)
            if x > threshold or (x == threshold and lo & 1):
                result += 1
        return (-result) & ((1 << self.bits) - 1) if negative else result

    def add(self, a: int, b: int) -> int:
        """Soma exata de dois códigos, arredondada uma vez (NaR se propaga)."""
        x, y = self.decode(a), self.decode(b)
        return self.encode(None if x is None or y is None else x + y)

    def sub(self, a: int, b: int) -> int:
        """Subtração exata de dois códigos, arredondada uma vez (NaR se propaga)."""
        x, y = self.decode(a), self.decode(b)
        return self.encode(None if x is None or y is None else x - y)

    def mul(self, a: int, b: int) -> int:
        """Multiplicação exata de dois códigos, arredondada uma vez (NaR se propaga)."""
        x, y = self.decode(a), self.decode(b)
        return self.encode(None if x is None or y is None else x * y)
