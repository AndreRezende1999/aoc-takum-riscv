"""Erro SpMV de formatos IEEE 754, OCP FP8, bfloat16 e Takum contra binary128.

Avalia todas as 8 matrizes Harwell-Boeing frente ao oráculo binary128 (Float128)
nos regimes sem escala (``none``) e com pré-escalonamento em potência de dois
(``pow2-bound``). Além do erro relativo L2 por matriz, registra o erro relativo
componente a componente por linha (para construção de CDFs suaves) em:
  - results/spmv_numerico_hb.csv          (sem escala)
  - results/spmv_numerico_scaled_hb.csv   (com escala pow2-bound)
  - results/spmv_row_errors_hb.csv        (distribuição por linha, ambos regimes)

    python3 kernels/numeric_baselines.py
"""

from __future__ import annotations

import csv
import pathlib
import sys
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kernels"))
sys.path.insert(0, str(ROOT / "python"))

from spmv import MATRIX_DIR, x_vector  # noqa: E402
from takum_rvv.binary import (  # noqa: E402
    BFLOAT16,
    BINARY16,
    BINARY32,
    BINARY64,
    E4M3,
    E4M3_SAT,
    E5M2,
    E5M2_SAT,
)
from takum_rvv.codec import Takum  # noqa: E402
from takum_rvv.posit import (  # noqa: E402
    POSIT8,
    POSIT8_2,
    POSIT16,
    POSIT16_2,
    POSIT32,
    POSIT64,
)
from takum_rvv.scaling import prepare_scaled_inputs, rescale_values  # noqa: E402
from takum_rvv.sparse import (  # noqa: E402
    error_metrics,
    read_matrix_market,
    reference_spmv,
    scalar_spmv,
)

OUT_NONE = ROOT / "results" / "spmv_numerico_hb.csv"
OUT_SCALED = ROOT / "results" / "spmv_numerico_scaled_hb.csv"
OUT_ROWS = ROOT / "results" / "spmv_row_errors_hb.csv"

FORMATS = [
    # Política padrão (acumulador 2n para Takum/Posit e largura estendida padrão para FP/BF16).
    ("e4m3", E4M3, BINARY16),
    ("e4m3_sat", E4M3_SAT, BINARY16),
    ("e5m2", E5M2, BINARY16),
    ("e5m2_sat", E5M2_SAT, BINARY16),
    ("binary16", BINARY16, BINARY32),
    ("bfloat16", BFLOAT16, BINARY32),
    ("binary32", BINARY32, BINARY32),
    ("takum8", Takum(8), Takum(16)),
    ("takum16", Takum(16), Takum(32)),
    ("takum32", Takum(32), Takum(64)),
    ("posit8_0", POSIT8, POSIT16),
    ("posit8_2", POSIT8_2, POSIT16_2),
    ("posit16", POSIT16_2, POSIT32),
    ("posit16_1", POSIT16, POSIT32),
    ("posit32", POSIT32, POSIT64),
    # Controles de acumulação (mesma largura 1x e acumulador FP64).
    ("e4m3_acc8", E4M3, E4M3),
    ("e5m2_acc8", E5M2, E5M2),
    ("binary16_acc16", BINARY16, BINARY16),
    ("bfloat16_acc16", BFLOAT16, BFLOAT16),
    ("binary32_acc64", BINARY32, BINARY64),
    ("takum8_acc8", Takum(8), Takum(8)),
    ("takum16_acc16", Takum(16), Takum(16)),
    ("takum32_acc32", Takum(32), Takum(32)),
    ("posit8_0_acc8", POSIT8, POSIT8),
    ("posit8_2_acc8", POSIT8_2, POSIT8_2),
    ("posit16_acc16", POSIT16_2, POSIT16_2),
    ("posit16_1_acc16", POSIT16, POSIT16),
    ("posit32_acc32", POSIT32, POSIT32),
]

CDF_FORMATS = {
    "e4m3",
    "e4m3_sat",
    "e5m2",
    "binary16",
    "bfloat16",
    "binary32",
    "binary32_acc64",
    "takum8",
    "takum16",
    "takum32",
    "takum32_acc32",
    "posit8_2",
    "posit16",
    "posit32",
}


def acc_name(accumulator) -> str:
    return getattr(accumulator, "name", None) or f"takum_linear{accumulator.bits}"


def evaluate_policy(policy: str) -> tuple[list[dict], list[dict]]:
    summary_rows: list[dict] = []
    component_rows: list[dict] = []

    for path in sorted(MATRIX_DIR.glob("*.mtx")):
        matrix = read_matrix_market(path)
        xs = x_vector(matrix.cols)
        reference = reference_spmv(matrix, xs)
        scaled_a, scaled_x, sa, sx = prepare_scaled_inputs(matrix, xs, policy)
        out_scale = sa * sx

        for name, storage, accumulator in FORMATS:
            raw = scalar_spmv(scaled_a, scaled_x, storage, accumulator)
            actual = rescale_values([storage.decode(val) for val in raw], out_scale)
            metrics = error_metrics(actual, reference)

            # Erro de representação pura da matriz A no formato de armazenamento
            mat_quant = rescale_values(
                [storage.decode(storage.encode(v)) for v in scaled_a.data], sa
            )
            mat_metrics = error_metrics(mat_quant, matrix.data)

            summary_rows.append({
                "matrix": path.stem,
                "format": name,
                "accumulator": acc_name(accumulator),
                "relative_l2": metrics["relative_l2"],
                "nonfinite": metrics["nonfinite_count"],
                "matrix_rel_l2": mat_metrics["relative_l2"],
                "matrix_nonfinite": mat_metrics["nonfinite_count"],
                "scale_a": str(sa),
                "scale_x": str(sx),
            })

            if name in CDF_FORMATS:
                for row_idx, (act_v, ref_v) in enumerate(zip(actual, reference)):
                    if ref_v is None or ref_v == 0:
                        continue
                    if act_v is None:
                        rel_str = "NF"
                    else:
                        err = abs(act_v - ref_v) / abs(ref_v)
                        rel_str = f"{float(err):.6e}"
                    component_rows.append({
                        "scaling": policy,
                        "matrix": path.stem,
                        "row": row_idx,
                        "format": name,
                        "relative_error": rel_str,
                    })

        print(f"[{policy:<10}] {path.stem:<10} concluído ({matrix.rows} linhas)")

    return summary_rows, component_rows


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    rows_none, comp_none = evaluate_policy("none")
    rows_scaled, comp_scaled = evaluate_policy("pow2-bound")
    write_csv(OUT_NONE, rows_none)
    write_csv(OUT_SCALED, rows_scaled)
    write_csv(OUT_ROWS, comp_none + comp_scaled)
    print(f"\n{len(rows_none)} avaliações sem escala -> {OUT_NONE}")
    print(f"{len(rows_scaled)} avaliações com escala -> {OUT_SCALED}")
    print(f"{len(comp_none) + len(comp_scaled)} erros por linha -> {OUT_ROWS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
