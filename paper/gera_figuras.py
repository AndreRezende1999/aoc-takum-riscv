"""Generate all vector figures (PDF and SVG) for the paper from verified models and CSVs.

Generates in paper/figures/:
  1. tapered-precision.{pdf,svg}    Precision bits vs dynamic range (8, 16, 32 bits)
  2. error-cdf.{pdf,svg}            Empirical CDFs: SpMV HB (unscaled & scaled) + SuiteSparse-100
  3. insn-csr-comparison.{pdf,svg}  Instructions, CSR writes, and active elements per NNZ

    python3 paper/gera_figuras.py
"""

from __future__ import annotations

import csv
import math
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
if not RESULTS.exists():
    RESULTS = ROOT / "sim" / "results"
OUT = ROOT / "paper" / "figures"

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 8.5,
    "axes.titlesize": 8.8,
    "axes.labelsize": 8.2,
    "legend.fontsize": 6.8,
    "xtick.labelsize": 7.6,
    "ytick.labelsize": 7.6,
    "axes.grid": True,
    "grid.linestyle": ":",
    "grid.alpha": 0.45,
})


def read_rows(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def takum_sig_bits(n: int, exp2: np.ndarray) -> np.ndarray:
    """Significant precision bits (1 + fraction bits) for linear Takum at exponent 2^exp2."""
    out = np.full_like(exp2, np.nan, dtype=float)
    max_exp = 239 if n == 8 else 254
    min_exp = -239 if n == 8 else -255
    for i, e in enumerate(exp2):
        ei = int(math.floor(e))
        if ei < min_exp or ei > max_exp:
            continue
        r = int(math.floor(math.log2(ei + 1))) if ei >= 0 else int(math.floor(math.log2(-ei)))
        p = n - 5 - r
        out[i] = max(0.0, float(p + 1))
    return out


def posit_sig_bits(n: int, es: int, exp2: np.ndarray) -> np.ndarray:
    """Significant precision bits (1 + fraction bits) for Posit<n, es>."""
    out = np.full_like(exp2, np.nan, dtype=float)
    max_exp = (1 << es) * (n - 2)
    min_exp = -max_exp
    for i, e in enumerate(exp2):
        ei = int(math.floor(e))
        if ei < min_exp or ei > max_exp:
            continue
        k = ei >> es
        reg_bits = (k + 2) if k >= 0 else (-k + 1)
        p = max(0, n - 1 - reg_bits - es)
        out[i] = float(p + 1) if (n - 1 - reg_bits) >= 0 else 0.0
    return out


def ieee_sig_bits(exp_bits: int, frac_bits: int, exp2: np.ndarray, finite_only: bool = False) -> np.ndarray:
    """Significant precision bits (1 + effective mantissa) for IEEE-like binary formats."""
    bias = (1 << (exp_bits - 1)) - 1
    e_max = (1 << exp_bits) - 1 - bias if finite_only else (1 << exp_bits) - 2 - bias
    e_min_norm = 1 - bias
    e_min_sub = e_min_norm - frac_bits
    out = np.full_like(exp2, np.nan, dtype=float)
    for i, e in enumerate(exp2):
        ei = int(math.floor(e))
        if ei < e_min_sub or ei > e_max:
            continue
        if ei >= e_min_norm:
            out[i] = float(frac_bits + 1)
        else:
            out[i] = float(frac_bits + 1 - (e_min_norm - ei))
    return out


def generate_tapered_precision(lang: str = "en") -> None:
    """Plot significant precision bits vs log10(|x|) for 8, 16, and 32-bit formats."""
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.45), sharey=False)
    exp2_wide = np.linspace(-260, 260, 4161)
    log10_x = exp2_wide * math.log10(2.0)

    t8 = "(a) 8-bit Formats" if lang == "en" else "(a) Formatos de 8 bits"
    t16 = "(b) 16-bit Formats" if lang == "en" else "(b) Formatos de 16 bits"
    t32 = "(c) 32-bit Formats" if lang == "en" else "(c) Formatos de 32 bits"
    ylab = "Significant precision (bits)" if lang == "en" else "Precisão significativa (bits)"
    suffix = "" if lang == "en" else "-pt"

    xticks = [-75, -20, -5, 0, 5, 20, 75]
    xtick_labels = ["-75", "-20", "-5", "0", "5", "20", "75"]

    # Panel (a): 8-bit
    ax = axes[0]
    ax.plot(log10_x, takum_sig_bits(8, exp2_wide), color="#006d77", lw=1.8, label="Takum8")
    ax.plot(log10_x, posit_sig_bits(8, 2, exp2_wide), color="#d97706", lw=1.4, ls="--", label="Posit8 (es=2)")
    ax.plot(log10_x, ieee_sig_bits(4, 3, exp2_wide, finite_only=True), color="#2563eb", lw=1.5, ls="-.", label="OFP8 E4M3")
    ax.plot(log10_x, ieee_sig_bits(5, 2, exp2_wide), color="#dc2626", lw=1.4, ls=":", label="OFP8 E5M2")
    ax.set_title(t8)
    ax.set_ylabel(ylab)
    ax.set_ylim(-0.2, 5.4)
    ax.legend(loc="upper left", frameon=True, framealpha=0.92, fontsize=5.5, handlelength=1.3, borderpad=0.3, labelspacing=0.25)

    # Panel (b): 16-bit
    ax = axes[1]
    ax.plot(log10_x, takum_sig_bits(16, exp2_wide), color="#006d77", lw=1.8, label="Takum16")
    ax.plot(log10_x, posit_sig_bits(16, 2, exp2_wide), color="#d97706", lw=1.4, ls="--", label="Posit16 (es=2)")
    ax.plot(log10_x, ieee_sig_bits(5, 10, exp2_wide), color="#2563eb", lw=1.5, ls="-.", label="IEEE FP16")
    ax.plot(log10_x, ieee_sig_bits(8, 7, exp2_wide), color="#dc2626", lw=1.4, ls=":", label="bfloat16")
    ax.set_title(t16)
    ax.set_ylim(0, 14.5)
    ax.legend(loc="lower center", frameon=True, framealpha=0.92, fontsize=5.6, handlelength=1.4, borderpad=0.3, labelspacing=0.25)

    # Panel (c): 32-bit
    ax = axes[2]
    ax.plot(log10_x, takum_sig_bits(32, exp2_wide), color="#006d77", lw=1.8, label="Takum32")
    ax.plot(log10_x, posit_sig_bits(32, 2, exp2_wide), color="#d97706", lw=1.4, ls="--", label="Posit32 (es=2)")
    ax.plot(log10_x, ieee_sig_bits(8, 23, exp2_wide), color="#2563eb", lw=1.5, ls="-.", label="IEEE FP32")
    ax.set_title(t32)
    ax.set_ylim(10, 30.5)
    ax.legend(loc="lower center", frameon=True, framealpha=0.92, fontsize=5.6, handlelength=1.4, borderpad=0.3, labelspacing=0.25)

    # Apply unified symmetric-log X scale centered on [-5, 5] across all three panels
    for ax in axes:
        ax.set_xscale("symlog", linthresh=5.0, linscale=1.5)
        ax.set_xlim(-82, 82)
        ax.set_xticks(xticks)
        ax.set_xticklabels(xtick_labels)
        ax.minorticks_off()
        ax.set_xlabel(r"$\log_{10}|x|$ (symlog)")
        ax.axvline(-5.0, color="#94a3b8", lw=0.7, ls=":", alpha=0.6)
        ax.axvline(5.0, color="#94a3b8", lw=0.7, ls=":", alpha=0.6)

    fig.tight_layout(pad=0.6)
    for ext in ("pdf", "svg"):
        fig.savefig(OUT / f"tapered-precision{suffix}.{ext}", bbox_inches="tight")
    plt.close(fig)


def plot_cdf_series(ax, values_map: dict[str, tuple[list[float], int]], styles: dict[str, dict]) -> None:
    """Plot empirical CDF where denominator includes non-finite failures."""
    for label, (finite_vals, total_count) in values_map.items():
        if total_count == 0 or not finite_vals:
            continue
        arr = np.sort(np.array([max(v, 1e-12) for v in finite_vals]))
        y = np.arange(1, len(arr) + 1) / float(total_count)
        ax.step(arr, y, where="post", label=label, **styles[label])


def generate_error_cdf(lang: str = "en") -> None:
    """Generate two-panel CDF figure: (a) SpMV HB row errors (none vs scaled), (b) SuiteSparse-100."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.25), sharey=True)
    suffix = "" if lang == "en" else "-pt"
    none_lbl = "none" if lang == "en" else "s/ esc."
    scaled_lbl = "scaled" if lang == "en" else "esc."

    # Panel (a): SpMV HB component-wise relative error vs Float128
    row_file = RESULTS / "spmv_row_errors_hb.csv"
    if row_file.exists():
        raw_rows = read_rows(row_file)
        series_defs = [
            ("Takum32", "none", "takum32", dict(color="#006d77", lw=1.7, ls="-")),
            ("Posit32", "none", "posit32", dict(color="#047857", lw=1.3, ls=":")),
            ("FP32", "none", "binary32", dict(color="#111827", lw=1.4, ls="--")),
            ("Takum16", "none", "takum16", dict(color="#0ea5e9", lw=1.6, ls="-")),
            ("Posit16,2", "none", "posit16", dict(color="#0284c7", lw=1.3, ls=":")),
            ("bfloat16", "none", "bfloat16", dict(color="#8b5cf6", lw=1.4, ls="-.")),
            (f"FP16 ({none_lbl})", "none", "binary16", dict(color="#2563eb", lw=1.3, ls=":")),
            (f"FP16 ({scaled_lbl})", "pow2-bound", "binary16", dict(color="#2563eb", lw=1.3, ls="--")),
            ("Takum8", "none", "takum8", dict(color="#d97706", lw=1.6, ls="-")),
            ("Posit8,2", "none", "posit8_2", dict(color="#b45309", lw=1.3, ls=":")),
            (f"E4M3 ({none_lbl})", "none", "e4m3", dict(color="#dc2626", lw=1.3, ls="-.")),
            (f"E5M2 ({none_lbl})", "none", "e5m2", dict(color="#991b1b", lw=1.3, ls="--")),
        ]
        vals_map = {}
        styles = {}
        for label, sc, fmt, style in series_defs:
            sub = [r["relative_error"] for r in raw_rows if r["scaling"] == sc and r["format"] == fmt]
            finite_vals = [float(v) for v in sub if v != "NF"]
            vals_map[label] = (finite_vals, len(sub))
            styles[label] = style
        plot_cdf_series(ax1, vals_map, styles)
        ax1.set_xscale("log")
        ax1.set_xlim(1e-10, 5.0)
        ax1.set_ylim(0.0, 1.04)
        if lang == "en":
            ax1.set_title(r"(a) SpMV Row Error vs. Float128 (8 HB Matrices)", pad=38)
            ax1.set_xlabel(r"Componentwise relative error $\varepsilon_{\mathrm{rel}, i}$ (log)")
            ax1.set_ylabel("Cumulative fraction of rows")
        else:
            ax1.set_title(r"(a) Erro por Linha na SpMV vs. Float128 (8 Matrizes HB)", pad=38)
            ax1.set_xlabel(r"Erro relativo por componente $\varepsilon_{\mathrm{rel}, i}$ (log)")
            ax1.set_ylabel("Fração acumulada de linhas")
        ax1.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=4,
                   fontsize=5.9, frameon=True, columnspacing=0.7, handlelength=1.4)

    # Panel (b): SuiteSparse 100 conversion benchmark (15 formats including Posit & Takum Log)
    ss_file = RESULTS / "suitesparse100_conversion.csv"
    if ss_file.exists():
        ss_rows = read_rows(ss_file)
        ss_defs = [
            ("Takum32", "takum32", dict(color="#006d77", lw=1.7, ls="-")),
            ("TakumLog32", "taklog32", dict(color="#0f766e", lw=1.3, ls="-.")),
            ("Posit32", "posit32", dict(color="#047857", lw=1.3, ls=":")),
            ("FP32", "f32", dict(color="#111827", lw=1.4, ls="--")),
            ("Takum16", "takum16", dict(color="#0ea5e9", lw=1.6, ls="-")),
            ("Posit16", "posit16", dict(color="#0284c7", lw=1.3, ls=":")),
            ("bfloat16", "bf16", dict(color="#8b5cf6", lw=1.4, ls="-.")),
            ("FP16", "f16", dict(color="#2563eb", lw=1.3, ls="--")),
            ("Takum8", "takum8", dict(color="#d97706", lw=1.6, ls="-")),
            ("Posit8", "posit8", dict(color="#b45309", lw=1.3, ls=":")),
            ("E4M3", "f8_e4m3", dict(color="#dc2626", lw=1.3, ls="-.")),
            ("E5M2", "f8_e5m2", dict(color="#991b1b", lw=1.3, ls="--")),
        ]
        ss_map = {}
        ss_styles = {}
        for label, col, style in ss_defs:
            vals = []
            for r in ss_rows:
                try:
                    v = float(r[col])
                except (KeyError, ValueError):
                    continue
                if math.isfinite(v):
                    vals.append(max(v, 1e-11))
            ss_map[label] = (vals, len(ss_rows))
            ss_styles[label] = style
        plot_cdf_series(ax2, ss_map, ss_styles)
        ax2.set_xscale("log")
        ax2.set_xlim(1e-11, 5.0)
        if lang == "en":
            ax2.set_title("(b) Matrix Conversion Error (100 SuiteSparse)", pad=38)
            ax2.set_xlabel(r"Relative $\ell_2$ conversion error (log)")
        else:
            ax2.set_title("(b) Erro de Conversão (100 Matrizes SuiteSparse)", pad=38)
            ax2.set_xlabel(r"Erro relativo $\ell_2$ de conversão (log)")
        ax2.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=4,
                   fontsize=5.9, frameon=True, columnspacing=0.7, handlelength=1.4)

    fig.tight_layout(pad=0.6)
    for ext in ("pdf", "svg"):
        fig.savefig(OUT / f"error-cdf{suffix}.{ext}", bbox_inches="tight")
    plt.close(fig)

    if lang == "en":
        # Diagnostic CSV preserving sample counts
        with (OUT / "error-cdf-data.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["source", "format", "finite_count", "total_count"])
            if row_file.exists():
                for fmt in ("takum32", "posit32", "binary32", "takum16", "posit16", "bfloat16", "binary16", "takum8", "posit8_2", "e4m3", "e5m2"):
                    sub = [r["relative_error"] for r in raw_rows if r["scaling"] == "none" and r["format"] == fmt]
                    writer.writerow(["spmv_hb_none", fmt, sum(v != "NF" for v in sub), len(sub)])
            if ss_file.exists():
                for col in ("takum32", "taklog32", "posit32", "f32", "takum16", "posit16", "bf16", "f16", "takum8", "posit8", "f8_e4m3", "f8_e5m2"):
                    fin = sum(1 for r in ss_rows if r[col].lower() != "nan")
                    writer.writerow(["suitesparse100", col, fin, len(ss_rows)])


def generate_insn_csr_comparison(lang: str = "en") -> None:
    """Plot instruction count, CSR writes, and active elements per NNZ across VLENs."""
    spmv_rows = read_rows(RESULTS / "spmv_hb.csv")
    formats = [("fp32", "FP32", "#374151"),
               ("takum32", "Takum32", "#006d77"),
               ("takum16", "Takum16", "#0ea5e9"),
               ("takum8", "Takum8", "#d97706")]
    vlens = ["128", "256", "512"]
    suffix = "" if lang == "en" else "-pt"

    def metric(fmt: str, vlen: str, key: str) -> float:
        sub = [r for r in spmv_rows if r["format"] == fmt and r["vlen"] == vlen]
        return sum(int(r[key]) for r in sub) / sum(int(r["nnz"]) for r in sub)

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.3))
    x = np.arange(len(vlens))
    width = 0.19

    if lang == "en":
        panels = [
            ("insn_total", "(a) Total Instructions / NNZ", "Instructions / NNZ", 7.3),
            ("csr_writes", "(b) CSR Writes / NNZ", "CSR writes / NNZ", 1.85),
            ("elem_active", "(c) Active Elements / NNZ", "Active elements / NNZ", 6.4),
        ]
    else:
        panels = [
            ("insn_total", "(a) Instruções Totais / NNZ", "Instruções / NNZ", 7.3),
            ("csr_writes", "(b) Escritas CSR / NNZ", "Escritas CSR / NNZ", 1.85),
            ("elem_active", "(c) Elementos Ativos / NNZ", "Elementos ativos / NNZ", 6.4),
        ]
    for ax, (key, title, ylabel, ymax) in zip(axes, panels):
        for idx, (fmt, label, color) in enumerate(formats):
            vals = [metric(fmt, v, key) for v in vlens]
            offset = (idx - 1.5) * width
            bars = ax.bar(x + offset, vals, width, label=label, color=color, edgecolor="black", linewidth=0.4)
            if key == "elem_active" and idx == 0:
                ax.text(bars[0].get_x() + bars[0].get_width() / 2, bars[0].get_height() + 0.12,
                        f"{bars[0].get_height():.2f}", ha="center", va="bottom", fontsize=6.4)
            elif key == "elem_active" and idx == 2:
                ax.text(bars[0].get_x() + bars[0].get_width() / 2, bars[0].get_height() + 0.12,
                        f"{bars[0].get_height():.2f}", ha="center", va="bottom", fontsize=6.4)
        ax.set_xticks(x)
        ax.set_xticklabels(vlens)
        ax.set_xlabel("VLEN (bits)")
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.set_ylim(0, ymax)

    axes[0].legend(loc="upper right", fontsize=6.3, frameon=True, framealpha=0.92)
    fig.tight_layout(pad=0.6)
    for ext in ("pdf", "svg"):
        fig.savefig(OUT / f"insn-csr-comparison{suffix}.{ext}", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for lang in ("en", "pt"):
        generate_tapered_precision(lang)
        generate_error_cdf(lang)
        generate_insn_csr_comparison(lang)
    print("gerado: paper/figures/{tapered-precision,error-cdf,insn-csr-comparison}[-pt].{pdf,svg}")


if __name__ == "__main__":
    main()
