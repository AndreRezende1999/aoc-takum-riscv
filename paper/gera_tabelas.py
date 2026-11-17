"""Generate paper tables and macros (English and Portuguese) from reproducible CSVs.

Outputs included by paper/main.tex (EN) and paper/main_pt.tex (PT):
  paper/tabelas-precisao32{,-pt}.tex
  paper/tabelas-precisao816{,-pt}.tex
  paper/tabelas-contagens{,-pt}.tex
  paper/tabela-modelo{,-pt}.tex
  paper/tabela-suitesparse100{,-pt}.tex
  paper/numeros.tex

    python3 paper/gera_tabelas.py
"""

from __future__ import annotations

import csv
import math
import pathlib
import statistics as st
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
if not RES.exists():
    RES = ROOT / "sim" / "results"
PAPER = ROOT / "paper"
SPMV = RES / "spmv_hb.csv"
NUMERIC = RES / "spmv_numerico_hb.csv"
SCALED = RES / "spmv_numerico_scaled_hb.csv"
MODEL = RES / "modelo_contagem.csv"
SS100 = RES / "suitesparse100_conversion.csv"

VLEN_REF = "256"
VLENS = ("128", "256", "512")
WORD = {"fp32": "FP", "takum32": "Trinta", "takum16": "Dez", "takum8": "Oito"}
VLEN_WORD = {"128": "Cento", "256": "Duzentos", "512": "Quinhentos"}


def load(path: pathlib.Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def comma(text: str) -> str:
    return text.replace(",", ".")


def sci(value: float) -> str:
    if value == 0.0:
        return "$0$"
    mantissa, exponent = f"{value:.2e}".split("e")
    return f"${comma(mantissa)} \\times 10^{{{int(exponent)}}}$"


def ratio(value: float) -> str:
    return comma(f"{value:.2f}")


def signed_percent(value: float) -> str:
    sign = "+" if value >= 0 else "$-$"
    return f"{sign}{comma(f'{abs(value):.1f}')}\\%"


def name(matrix: str) -> str:
    return matrix.replace("_", "\\_")


def num(row: dict) -> float | None:
    value = row["relative_l2"]
    return None if value in ("", "None") else float(value)


def cell(row: dict) -> str:
    value = num(row)
    if value is None:
        return f"NF({row['nonfinite']})"
    return sci(value)


def table_block(caption: str, label: str, columns: str, header: list[str], body: list[str],
                footer: list[str], star: bool = True) -> str:
    env = "table*" if star else "table"
    size_cmd = "\\footnotesize" if star else "\\scriptsize"
    lines = [
        f"\\begin{{{env}}}[t]",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        "\\centering",
        size_cmd,
    ]
    if not star:
        lines.extend([
            "\\setlength{\\tabcolsep}{3.0pt}",
            "\\renewcommand{\\arraystretch}{0.95}",
        ])
    lines.extend([
        f"\\begin{{tabular}}{{{columns}}}",
        "\\toprule",
        " & ".join(header) + " \\\\",
        "\\midrule",
        *body,
        *footer,
        "\\bottomrule",
        "\\end{tabular}",
        f"\\end{{{env}}}",
    ])
    return "\n".join(lines) + "\n"


def tabela_precisao32(spmv: dict, numeric: dict, scaled: dict, matrices: list[str], lang: str) -> str:
    body, cols = [], defaultdict(list)
    for m in matrices:
        base = spmv[(m, "fp32", VLEN_REF)]
        t32 = spmv[(m, "takum32", VLEN_REF)]
        b64 = numeric[(m, "binary32_acc64")]
        t32a32 = numeric[(m, "takum32_acc32")]
        t32sc = scaled[(m, "takum32")]
        for key, row in (("fp32", base), ("takum32", t32), ("b64", b64), ("t32a32", t32a32), ("t32sc", t32sc)):
            cols[key].append(num(row))
        body.append(
            f"{name(m)} & {base['nnz']} & {cell(base)} & {cell(t32)} & "
            f"{cell(b64)} & {cell(t32a32)} & {cell(t32sc)} \\\\"
        )
    med_lbl = "Median" if lang == "en" else "Mediana"
    footer = [
        "\\midrule",
        f"{med_lbl} & & " + " & ".join(
            sci(st.median(cols[k])) for k in ("fp32", "takum32", "b64", "t32a32", "t32sc")
        ) + " \\\\",
    ]
    if lang == "en":
        cap = (
            "Relative $\\ell_2$ SpMV error at 32 bits (VLEN = 256) against Float128, by matrix. "
            "FP32 and Takum32 are simulated RISC-V kernels (32-bit and 64-bit accumulators, respectively); "
            "controls isolate accumulator width and \\texttt{pow2-bound} input scaling."
        )
        hdr = ["Matrix", "nnz", "FP32 (32b acc.)", "Takum32 (64b acc.)", "FP32 (64b acc.)", "Takum32 (32b acc.)", "Takum32 (scaled)"]
    else:
        cap = (
            "Erro relativo $\\ell_2$ no SpMV em 32 bits (VLEN = 256) frente ao Float128, por matriz. "
            "FP32 e Takum32 são kernels RISC-V simulados (acumuladores de 32 e 64 bits); os controles isolam "
            "a largura do acumulador e o pré-escalonamento \\texttt{pow2-bound}."
        )
        hdr = ["Matriz", "nnz", "FP32 (ac. 32b)", "Takum32 (ac. 64b)", "FP32 (ac. 64b)", "Takum32 (ac. 32b)", "Takum32 (esc.)"]
    return table_block(cap, "tab:precisao32", "@{}lrccccc@{}", hdr, body, footer, star=True)


def tabela_precisao816(spmv: dict, numeric: dict, scaled: dict, matrices: list[str], lang: str) -> str:
    body = []
    for m in matrices:
        body.append(
            f"{name(m)} & {cell(numeric[(m, 'e4m3')])} & {cell(numeric[(m, 'e5m2')])} & "
            f"{cell(numeric[(m, 'binary16')])} & {cell(numeric[(m, 'bfloat16')])} & "
            f"{cell(spmv[(m, 'takum16', VLEN_REF)])} & {cell(spmv[(m, 'takum8', VLEN_REF)])} \\\\"
        )

    fmts = ("e4m3", "e5m2", "binary16", "bfloat16", "takum16", "takum8")
    med_none = []
    med_scaled = []
    fin_none = []
    for f in fmts:
        vals_n = [num(numeric[(m, f)]) for m in matrices if num(numeric[(m, f)]) is not None]
        vals_s = [num(scaled[(m, f)]) for m in matrices if num(scaled[(m, f)]) is not None]
        med_none.append(sci(st.median(vals_n)) if vals_n else "---")
        med_scaled.append(sci(st.median(vals_s)) if vals_s else "---")
        fin_none.append(f"{len(vals_n)}/8")

    if lang == "en":
        footer = [
            "\\midrule",
            "Finite (unscaled) & " + " & ".join(fin_none) + " \\\\",
            "Median (unscaled, finite) & " + " & ".join(med_none) + " \\\\",
            "Median (\\texttt{pow2-bound}, 8/8) & " + " & ".join(med_scaled) + " \\\\",
        ]
        cap = (
            "Relative $\\ell_2$ SpMV error at 8 and 16 bits against Float128 (VLEN = 256). "
            "NF($k$) denotes $k$ non-finite rows (overflow). Accumulators: 16-bit for E4M3, E5M2, Takum8; "
            "32-bit for FP16, BF16, Takum16. Bottom rows summarize finite counts and \\texttt{pow2-bound} scaling."
        )
        hdr = ["Matrix", "E4M3", "E5M2", "FP16", "bfloat16", "Takum16", "Takum8"]
    else:
        footer = [
            "\\midrule",
            "Finitas (sem escala) & " + " & ".join(fin_none) + " \\\\",
            "Mediana (sem escala, finitas) & " + " & ".join(med_none) + " \\\\",
            "Mediana (\\texttt{pow2-bound}, 8/8) & " + " & ".join(med_scaled) + " \\\\",
        ]
        cap = (
            "Erro relativo $\\ell_2$ no SpMV em 8 e 16 bits frente ao Float128 (VLEN = 256). "
            "NF($k$) indica $k$ linhas não finitas (overflow). Acumuladores: 16 bits para E4M3, E5M2 e Takum8; "
            "32 bits para FP16, bfloat16 e Takum16. O rodapé resume o efeito do escalonamento \\texttt{pow2-bound}."
        )
        hdr = ["Matriz", "E4M3", "E5M2", "FP16", "bfloat16", "Takum16", "Takum8"]
    return table_block(cap, "tab:precisao816", "@{}lcccccc@{}", hdr, body, footer, star=True)


def tabela_suitesparse100(ss_rows: list[dict], lang: str) -> str:
    cols = [
        ("f8_e4m3", "OFP8 E4M3"),
        ("f8_e5m2", "OFP8 E5M2"),
        ("posit8", "Posit8"),
        ("takum8", "Takum8 (Lin.)"),
        ("taklog8", "Takum8 (Log)"),
        ("f16", "IEEE FP16"),
        ("bf16", "bfloat16"),
        ("posit16", "Posit16"),
        ("takum16", "Takum16 (Lin.)"),
        ("taklog16", "Takum16 (Log)"),
        ("f32", "IEEE FP32"),
        ("posit32", "Posit32"),
        ("takum32", "Takum32 (Lin.)"),
        ("taklog32", "Takum32 (Log)"),
    ]
    body = []
    for idx, (col, label) in enumerate(cols):
        vals = sorted(
            float(r[col]) for r in ss_rows
            if r[col].lower() != "nan" and math.isfinite(float(r[col]))
        )
        med = st.median(vals)
        p90 = vals[int(0.9 * len(vals)) - 1]
        mx = max(vals)
        body.append(f"{label} & {len(vals)}/100 & {sci(med)} & {sci(p90)} & {sci(mx)} \\\\")
        if idx in (4, 9):
            body.append("\\midrule")
    if lang == "en":
        cap = (
            "Conversion viability across 100 SuiteSparse matrices ($\\mathrm{nnz} \\le 50\\,000$): "
            "Takum (Linear and Logarithmic), Posit ($es=2$), and IEEE/OCP formats."
        )
        hdr = ["Format", "Fin.", "Median", "P90", "Max"]
    else:
        cap = (
            "Viabilidade de conversão em 100 matrizes SuiteSparse ($\\mathrm{nnz} \\le 50\\,000$): "
            "Takum (Linear e Logarítmico), Posit ($es=2$) e formatos IEEE/OCP."
        )
        hdr = ["Fmt.", "Fin.", "Mediana", "P90", "Máx."]
    return table_block(cap, "tab:suitesparse100", "@{}lcccc@{}", hdr, body, [], star=False)


def tabela_contagens(spmv_rows: list[dict], lang: str) -> str:
    grouped = defaultdict(list)
    for r in spmv_rows:
        grouped[(r["format"], r["vlen"])].append(r)

    def per_nnz(rows: list[dict], key: str) -> float:
        return sum(int(r[key]) for r in rows) / sum(int(r["nnz"]) for r in rows)

    keys = ("insn_total", "insn_zvtakum", "csr_writes", "elem_active")
    body = []
    for fmt, label in (("fp32", "FP32"), ("takum32", "Takum32"), ("takum16", "Takum16"), ("takum8", "Takum8")):
        for vlen in VLENS:
            rows = grouped[(fmt, vlen)]
            values = " & ".join(comma(f"{per_nnz(rows, key):.3f}") for key in keys)
            body.append(f"{label} & {vlen} & {values} \\\\")
        body.append("\\midrule")
    body = body[:-1]
    if lang == "en":
        cap = (
            "Dynamic instructions, \\texttt{Zvtakum} instructions, CSR writes, and active elements per nonzero, "
            "aggregated over all eight Harwell--Boeing matrices."
        )
        hdr = ["Fmt", "VLEN", "Insn/nnz", "Zvt./nnz", "CSR/nnz", "Elem./nnz"]
    else:
        cap = (
            "Instruções dinâmicas, instruções \\texttt{Zvtakum}, escritas em CSR e elementos ativos por não nulo, "
            "agregados nas oito matrizes Harwell--Boeing."
        )
        hdr = ["Fmt", "VLEN", "Insn/nnz", "Zvt./nnz", "CSR/nnz", "Elem./nnz"]
    return table_block(cap, "tab:contagens", "@{}llcccc@{}", hdr, body, [], star=False)


def tabela_modelo(model_rows: list[dict], lang: str) -> str:
    body = []
    for row in model_rows:
        label = {"fp32": "FP32", "takum32": "Takum32", "takum16": "Takum16", "takum8": "Takum8"}[row["formato"]]
        body.append(
            f"{label} & {row['r']} & {row['c']} & {row['k']} & "
            f"{row['sinteticos_ok']}/{row['sinteticos_total']} & "
            f"{row['exatas']}/{row['execucoes']} \\\\"
        )
    if lang == "en":
        cap = (
            "Parameters of the analytic instruction-count model $N_f = r_f R + c_f S + K$, "
            "where $R$ is row count and $S$ is total nonempty-row strip count across all 96 simulator runs."
        )
        hdr = ["Format", "$r$", "$c$", "$K$", "Synthetic", "Exact runs"]
    else:
        cap = (
            "Parâmetros do modelo analítico de contagem $N_f = r_f R + c_f S + K$, em que $R$ é o número de linhas "
            "e $S$ o total de faixas não vazias nas 96 execuções do simulador."
        )
        hdr = ["Formato", "$r$", "$c$", "$K$", "Sintéticos", "Execuções exatas"]
    return table_block(cap, "tab:modelo", "@{}lcccrr@{}", hdr, body, [], star=False)


def pair_stats(takum: list[tuple], other: list[tuple]) -> dict:
    stats = {"Ambos": 0, "TakumVence": 0, "OutroVence": 0, "Empates": 0,
             "TakumNF": 0, "OutroNF": 0}
    for (tv, _), (ov, _) in zip(takum, other):
        stats["TakumNF"] += int(tv is None)
        stats["OutroNF"] += int(ov is None)
        if tv is None or ov is None:
            continue
        stats["Ambos"] += 1
        if tv < ov:
            stats["TakumVence"] += 1
        elif ov < tv:
            stats["OutroVence"] += 1
        else:
            stats["Empates"] += 1
    return stats


def instruction_pairs(spmv_rows: list[dict]) -> dict:
    idx = {(r["matrix"], r["format"], r["vlen"]): r for r in spmv_rows}
    out = {}
    for fmt in ("takum32", "takum16", "takum8"):
        less = equal = more = 0
        for (m, f, v), row in idx.items():
            if f != fmt:
                continue
            delta = int(row["insn_total"]) - int(idx[(m, "fp32", v)]["insn_total"])
            less += int(delta < 0)
            equal += int(delta == 0)
            more += int(delta > 0)
        out[fmt] = (less, equal, more)
    return out


def macros(spmv_rows: list[dict], numeric_rows: list[dict], scaled_rows: list[dict], model_rows: list[dict]) -> str:
    spmv = {(r["matrix"], r["format"], r["vlen"]): r for r in spmv_rows}
    numeric = {(r["matrix"], r["format"]): r for r in numeric_rows}
    scaled = {(r["matrix"], r["format"]): r for r in scaled_rows}
    matrices = sorted({r["matrix"] for r in spmv_rows})
    out = ["% Gerado por paper/gera_tabelas.py. Não editar à mão."]

    def add(key: str, value: str) -> None:
        out.append(f"\\newcommand{{\\{key}}}{{{value}\\xspace}}")

    def med_spmv(fmt: str, vlen: str = VLEN_REF) -> float:
        return st.median([num(spmv[(m, fmt, vlen)]) for m in matrices if num(spmv[(m, fmt, vlen)]) is not None])

    def med_num(src: dict, fmt: str) -> float:
        return st.median([num(src[(m, fmt)]) for m in matrices if num(src[(m, fmt)]) is not None])

    def per_nnz(fmt: str, vlen: str, key: str) -> float:
        rows = [r for r in spmv_rows if r["format"] == fmt and r["vlen"] == vlen]
        return sum(int(r[key]) for r in rows) / sum(int(r["nnz"]) for r in rows)

    add("NumMatrizes", str(len(matrices)))
    add("NumExecSpmv", str(len(spmv_rows)))
    add("NumBitExatas", str(sum(r["bit_exact"] == "True" for r in spmv_rows)))
    add("MinLinhas", str(min(int(r["rows"]) for r in spmv_rows)))
    add("MaxLinhas", str(max(int(r["rows"]) for r in spmv_rows)))
    add("MaxNnz", str(max(int(r["nnz"]) for r in spmv_rows)))

    add("MedFPtrinta", sci(med_spmv("fp32")))
    add("MedTakumTrinta", sci(med_spmv("takum32")))
    add("MedFPtrintaAcSes", sci(med_num(numeric, "binary32_acc64")))
    add("MedTakumTrintaAcTrinta", sci(med_num(numeric, "takum32_acc32")))
    add("MedTakumTrintaScaled", sci(med_num(scaled, "takum32")))
    add("MedBF", sci(med_num(numeric, "bfloat16")))
    add("MedTakumDez", sci(med_spmv("takum16")))
    add("MedTakumDezScaled", sci(med_num(scaled, "takum16")))
    add("MedTakumOito", sci(med_spmv("takum8")))
    add("MedTakumOitoScaled", sci(med_num(scaled, "takum8")))

    add("RazaoFormatoAcTrinta", ratio(med_num(numeric, "binary32") / med_num(numeric, "takum32_acc32")))
    add("RazaoAcumuladorTakum", ratio(med_num(numeric, "takum32_acc32") / med_spmv("takum32")))
    add("RazaoKernelTrinta", ratio(med_spmv("fp32") / med_spmv("takum32")))
    add("RazaoAcAmpliadoTrinta", ratio(med_num(numeric, "binary32_acc64") / med_spmv("takum32")))
    add("RazaoTakumBF", ratio(med_num(numeric, "bfloat16") / med_spmv("takum16")))
    add("RazaoTakumBFScaled", ratio(med_num(scaled, "bfloat16") / med_num(scaled, "takum16")))

    takum8 = [(num(spmv[(m, "takum8", VLEN_REF)]), 0) for m in matrices]
    takum16 = [(num(spmv[(m, "takum16", VLEN_REF)]), 0) for m in matrices]
    takum32 = [(num(spmv[(m, "takum32", VLEN_REF)]), 0) for m in matrices]
    takum32_acc32 = [(num(numeric[(m, "takum32_acc32")]), 0) for m in matrices]

    def other(src: dict, fmt_key: str) -> list[tuple]:
        return [(num(src[(m, fmt_key)]), 0) for m in matrices]

    pares = {
        "TrintaFP": (takum32, [(num(spmv[(m, "fp32", VLEN_REF)]), 0) for m in matrices]),
        "TrintaAcFP": (takum32_acc32, other(numeric, "binary32")),
        "DezFP": (takum16, other(numeric, "binary16")),
        "DezBF": (takum16, other(numeric, "bfloat16")),
        "OitoEquatrom": (takum8, other(numeric, "e4m3")),
        "OitoCincodois": (takum8, other(numeric, "e5m2")),
    }
    for tag, (takum, reference) in pares.items():
        stats = pair_stats(takum, reference)
        for key, value in stats.items():
            add(f"Par{tag}{key}", str(value))

    add("NFTakumOito", str(sum(1 for m in matrices if num(spmv[(m, "takum8", VLEN_REF)]) is None)))
    add("NFTakumDez", str(sum(1 for m in matrices if num(spmv[(m, "takum16", VLEN_REF)]) is None)))
    add("NFEquatrom", str(sum(1 for m in matrices if int(numeric[(m, "e4m3")]["nonfinite"]) > 0)))
    add("NFCincodois", str(sum(1 for m in matrices if int(numeric[(m, "e5m2")]["nonfinite"]) > 0)))
    add("NFDez", str(sum(1 for m in matrices if int(numeric[(m, "binary16")]["nonfinite"]) > 0)))
    add("NFBF", str(sum(1 for m in matrices if int(numeric[(m, "bfloat16")]["nonfinite"]) > 0)))

    add("ElemNnzFP", comma(f"{per_nnz('fp32', VLEN_REF, 'elem_active'):.2f}"))
    add("ElemNnzTakum", comma(f"{per_nnz('takum32', VLEN_REF, 'elem_active'):.2f}"))

    for fmt, word in WORD.items():
        for vlen, vword in VLEN_WORD.items():
            add(f"InsnNnz{word}{vword}", comma(f"{per_nnz(fmt, vlen, 'insn_total'):.2f}"))
            add(f"CsrNnz{word}{vword}", comma(f"{per_nnz(fmt, vlen, 'csr_writes'):.2f}"))
            if fmt != "fp32":
                rel_insn = 100 * (per_nnz(fmt, vlen, "insn_total") / per_nnz("fp32", vlen, "insn_total") - 1)
                rel_csr = 100 * (per_nnz(fmt, vlen, "csr_writes") / per_nnz("fp32", vlen, "csr_writes") - 1)
                add(f"RelInsn{word}{vword}", signed_percent(rel_insn))
                add(f"RelCsr{word}{vword}", signed_percent(rel_csr))
                if fmt == "takum32":
                    add(f"Economia{vword}", comma(f"{-rel_insn:.1f}") + "\\%")
                add(f"ZvtNnz{word}{vword}", comma(f"{per_nnz(fmt, vlen, 'insn_zvtakum'):.2f}"))

    for fmt, (less, equal, more) in instruction_pairs(spmv_rows).items():
        add(f"InsnMenor{WORD[fmt]}", str(less))
        add(f"InsnIgual{WORD[fmt]}", str(equal))
        add(f"InsnMaior{WORD[fmt]}", str(more))
    add("InsnPares", str(len(matrices) * len(VLENS)))

    for row in model_rows:
        word = WORD[row["formato"]]
        add(f"ModR{word}", row["r"])
        add(f"ModC{word}", row["c"])
        add(f"ModK{word}", row["k"])
    add("ModExatas", str(sum(int(r["exatas"]) for r in model_rows)))
    add("ModExec", str(sum(int(r["execucoes"]) for r in model_rows)))
    add("ModSinteticosOk", str(sum(int(r["sinteticos_ok"]) for r in model_rows)))
    add("ModSinteticosTotal", str(sum(int(r["sinteticos_total"]) for r in model_rows)))
    add("ModResiduoMax", str(max(int(r["residuo_max"]) for r in model_rows)))
    return "\n".join(out) + "\n"


def main() -> None:
    spmv_rows = load(SPMV)
    numeric_rows = load(NUMERIC)
    scaled_rows = load(SCALED)
    model_rows = load(MODEL)
    ss_rows = load(SS100)
    spmv = {(r["matrix"], r["format"], r["vlen"]): r for r in spmv_rows}
    numeric = {(r["matrix"], r["format"]): r for r in numeric_rows}
    scaled = {(r["matrix"], r["format"]): r for r in scaled_rows}
    matrices = sorted({r["matrix"] for r in spmv_rows})

    for lang, suffix in (("en", ""), ("pt", "-pt")):
        (PAPER / f"tabelas-precisao32{suffix}.tex").write_text(
            tabela_precisao32(spmv, numeric, scaled, matrices, lang), encoding="utf-8"
        )
        (PAPER / f"tabelas-precisao816{suffix}.tex").write_text(
            tabela_precisao816(spmv, numeric, scaled, matrices, lang), encoding="utf-8"
        )
        (PAPER / f"tabelas-contagens{suffix}.tex").write_text(
            tabela_contagens(spmv_rows, lang), encoding="utf-8"
        )
        (PAPER / f"tabela-modelo{suffix}.tex").write_text(
            tabela_modelo(model_rows, lang), encoding="utf-8"
        )
        (PAPER / f"tabela-suitesparse100{suffix}.tex").write_text(
            tabela_suitesparse100(ss_rows, lang), encoding="utf-8"
        )

    (PAPER / "numeros.tex").write_text(
        macros(spmv_rows, numeric_rows, scaled_rows, model_rows), encoding="utf-8"
    )
    print("gerado: paper/tabelas-*.tex, paper/tabela-*.tex e paper/numeros.tex (EN/PT)")


if __name__ == "__main__":
    main()
