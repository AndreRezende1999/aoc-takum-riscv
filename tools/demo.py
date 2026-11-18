#!/usr/bin/env python3
"""Small, dependency-free demo for the 15-minute presentation.

Shows Takum T8/T16/T32 codes, LogTakum comparison, SpMV on the dynamic-range
fixture across Takum, Posit, bfloat16, OFP8, and FP32, and the verified
repository summary without requiring LLVM or QEMU.
"""

from __future__ import annotations

import csv
import pathlib
import random
import sys
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from takum_rvv.binary import BINARY32, BFLOAT16, E4M3  # noqa: E402
from takum_rvv.codec import LOG_TAKUM8, Takum  # noqa: E402
from takum_rvv.posit import POSIT8_2, POSIT16_2, POSIT32  # noqa: E402
from takum_rvv.sparse import (  # noqa: E402
    error_metrics,
    read_matrix_market,
    reference_spmv,
    scalar_spmv,
)


def x_vector(cols: int) -> list[Fraction]:
    rng = random.Random(2026)
    denominator = 1 << 52
    return [Fraction(rng.randint(-denominator, denominator), denominator) for _ in range(cols)]


def fmt_error(value: str | None) -> str:
    if value in (None, "", "None"):
        return "n/d (não finito)"
    return f"{float(value):.3e}"


def main() -> int:
    print("=" * 68)
    print("DEMO - Takum T8/T16/T32, Zvtakum e SpMV (modelo funcional exato)")
    print("=" * 68)

    print("\n[1] Códigos T8: prefixo completo de escala em 12 bits")
    t8 = Takum(8)
    for label, raw, text in (
        ("1.0", t8.encode(1), "1"),
        ("maxpos", 0x7F, "2^239"),
        ("minpos", 1, "2^-239"),
        ("NaR", 0x80, "NaR"),
    ):
        value = text if label in ("maxpos", "minpos", "NaR") else t8.decode(raw)
        print(f"  {label:7s} = 0x{raw:02x}  ->  {value}")
    print(f"  LogTakum8(0x40) = {LOG_TAKUM8.decode(0x40)}, mul(0x41, 0x3f) = 0x{LOG_TAKUM8.mul(0x41, 0x3f):02x}")

    print("\n[2] SpMV em python/examples/dynamic_range.mtx (referência binary128)")
    matrix = read_matrix_market(ROOT / "python" / "examples" / "dynamic_range.mtx")
    xs = x_vector(matrix.cols)
    reference = reference_spmv(matrix, xs)
    formats = [
        ("FP32", BINARY32, BINARY32),
        ("bfloat16", BFLOAT16, BINARY32),
        ("E4M3", E4M3, BFLOAT16),
        ("Takum8", Takum(8), Takum(16)),
        ("Takum16", Takum(16), Takum(32)),
        ("Takum32", Takum(32), Takum(64)),
        ("posit8,2", POSIT8_2, POSIT16_2),
        ("posit16,2", POSIT16_2, POSIT32),
    ]
    print(f"  {'formato':10s} {'não finitos':>12s} {'erro L2 rel.':>16s}")
    for name, storage, accumulator in formats:
        raw = scalar_spmv(matrix, xs, storage, accumulator)
        actual = [storage.decode(value) for value in raw]
        metrics = error_metrics(actual, reference)
        print(
            f"  {name:10s} {metrics['nonfinite_count']:>12d} "
            f"{fmt_error(metrics['relative_l2']):>16s}"
        )

    print("\n[3] Resumo versionado")
    spmv = ROOT / "results" / "spmv_hb.csv"
    if spmv.is_file():
        with spmv.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        exact = sum(row["bit_exact"] == "True" for row in rows)
        print(f"  SpMV: {exact}/{len(rows)} execuções bit-exatas vs modelo Python")
    model = ROOT / "results" / "modelo_contagem.csv"
    if model.is_file():
        with model.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        residual = max(int(row["residuo_max"]) for row in rows)
        print(f"  Modelo N=rR+cS+K: resíduo máximo = {residual}")

    print("\n[4] Escopo da demonstração")
    print("  - T8 atinge faixa 2^+-239; T16 e T32 chegam a 2^+-255.")
    print("  - Takum e posit mantêm resultados finitos; E4M3 e bfloat16 estouram em dinâmicas amplas.")
    print("  - Contagens do simulador são funcionais (instruções e CSRs), sem ciclos/área em RTL.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
