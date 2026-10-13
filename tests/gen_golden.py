"""Gera os vetores dourados do núcleo Takum (C++) a partir do modelo Python.

O modelo Python (python/takum/codec.py) usa racionais exatos e é o gabarito
da Fase 1.  Os vetores são comprometidos no repositório; este script só precisa
ser reexecutado se o modelo de referência mudar (alvo `make golden`).

Gera:
  - t8_add.bin, t8_sub.bin, t8_mul.bin: T8 exaustivo (256x256 pares por op);
  - takum_ops_sampled.txt: amostras de T16 e T32 (4000 pares por op e
    largura), no formato "op bits a b resultado" em hexadecimal.

Ver docs/fase1.md para a especificação e a estratégia de verificação.

Uso:

    python3 tests/gen_golden.py
"""

from __future__ import annotations

import pathlib
import random
import sys
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from takum.codec import Takum  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent / "golden"
SAMPLES = {16: 4000, 32: 4000}


def write_t8_tables(t8: Takum) -> None:
    """Grava as tabelas exaustivas de T8 (add, sub, mul) em 256*256 bytes."""
    for name, op in (("add", t8.add), ("sub", t8.sub), ("mul", t8.mul)):
        table = bytearray(256 * 256)
        for a in range(256):
            for b in range(256):
                table[a * 256 + b] = op(a, b)
        (OUT / f"t8_{name}.bin").write_bytes(bytes(table))


def random_code(rng: random.Random, takum: Takum) -> int:
    """Sorteia um código: metade totalmente aleatório, metade de valores de
    magnitude moderada, que exercitam as fronteiras de regime mais comuns."""
    if rng.random() < 0.5:
        return rng.getrandbits(takum.bits)
    value = Fraction(rng.randint(1, 1 << 20), rng.randint(1, 1 << 12))
    if rng.random() < 0.5:
        value = -value
    return takum.encode(value)


def write_sampled(rng: random.Random) -> None:
    """Grava as amostras de add/sub/mul em T16 e T32 (uma linha por caso)."""
    lines: list[str] = []
    for bits, count in SAMPLES.items():
        takum = Takum(bits)
        for _ in range(count):
            a = random_code(rng, takum)
            b = random_code(rng, takum)
            lines.append(f"add {bits} {a:x} {b:x} {takum.add(a, b):x}")
            lines.append(f"sub {bits} {a:x} {b:x} {takum.sub(a, b):x}")
            lines.append(f"mul {bits} {a:x} {b:x} {takum.mul(a, b):x}")
    (OUT / "takum_ops_sampled.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    # Semente fixa: os vetores comprometidos devem ser reproduzíveis bit a bit.
    rng = random.Random(2026)
    write_t8_tables(Takum(8))
    write_sampled(rng)
    print(f"vetores gravados em {OUT}")


if __name__ == "__main__":
    main()
