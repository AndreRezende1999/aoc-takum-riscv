#!/usr/bin/env python3
"""Closure benchmark: Linear vs Logarithmic Takum (T8 exhaustive, T16 sampled).

Reproduces Section 5.6 of Hunhold (arXiv:2404.18603v2) in pure Python without
requiring libtakum or C host floating-point heuristics:
  - Evaluates all positive representable values in the corresponding posit
    dynamic range: [2^-24, 2^24] for T8, [2^-56, 2^56] for T16.
  - Checks whether the exact mathematical result of {add, sub, mul, div, inv,
    sqrt, square} is exactly representable (as 0 or a nonzero finite code) in
    the full format (T8 or T16).
  - T8: exhaustive enumeration (N^2 binary pairs; N*(N+1)/2 for x >= y in sub).
  - T16: deterministic xorshift64 sampling (2,000,000 pairs per binary op, seed
    0x9E3779B97F4A7C15) and exhaustive enumeration for unary ops.

Usage:
    PYTHONPATH=python python3 scripts/bench_closure.py
"""

from __future__ import annotations

import bisect
import csv
import math
import pathlib
import sys
from decimal import Decimal, localcontext
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from takum_rvv.codec import LogTakum, Takum, _log_ell_pos  # noqa: E402

OUT_CSV = ROOT / "results" / "closure_takum_linear_log.csv"
SEED = 0x9E3779B97F4A7C15
SAMPLES = 2_000_000
OPS = ("add", "sub", "mul", "div", "inv", "sqrt", "square")


def xorshift64(state: list[int]) -> int:
    x = state[0]
    x = (x ^ ((x << 13) & 0xFFFFFFFFFFFFFFFF)) & 0xFFFFFFFFFFFFFFFF
    x ^= x >> 7
    x = (x ^ ((x << 17) & 0xFFFFFFFFFFFFFFFF)) & 0xFFFFFFFFFFFFFFFF
    state[0] = x
    return x


def collect_linear(bits: int, lo_exp: int, hi_exp: int):
    fmt = Takum(bits)
    lo = Fraction(1, 1 << (-lo_exp))
    hi = Fraction(1 << hi_exp)
    all_pos = [fmt.decode(c) for c in range(1, fmt.nar)]
    # All representable positive fractions stored as reduced (num, den) tuples
    all_set = set(all_pos)
    all_floats = [float(v) for v in all_pos]
    vals = [v for v in all_pos if lo <= v <= hi]
    val_floats = [float(v) for v in vals]
    return all_set, all_floats, vals, val_floats


def collect_log(bits: int, lo_exp: int, hi_exp: int):
    fmt = LogTakum(bits)
    # 12 fractional bits max -> scale ell by 2^13 = 8192 so every ell becomes an int,
    # and dividing by 2 for sqrt stays exact when even.
    scale = 1 << 13
    all_ells = [_log_ell_pos(c, bits) for c in range(1, fmt.nar)]
    all_ints = [int(ell * scale) for ell in all_ells]
    all_int_set = set(all_ints)
    with localcontext() as ctx:
        ctx.prec = _DEC_PREC if False else 80
        dlo = Decimal(2) ** lo_exp
        dhi = Decimal(2) ** hi_exp
        all_decs = []
        vals_ell = []
        vals_int = []
        vals_float = []
        vals_dec = []
        all_floats = []
        for idx, c in enumerate(range(1, fmt.nar)):
            dec = fmt.decode(c)
            all_decs.append(dec)
            all_floats.append(float(dec))
            if dlo <= dec <= dhi:
                vals_ell.append(all_ells[idx])
                vals_int.append(all_ints[idx])
                vals_float.append(float(dec))
                vals_dec.append(dec)
    return all_int_set, all_floats, set(all_decs), vals_ell, vals_int, vals_float, vals_dec


def near_in_sorted(sorted_floats: list[float], x: float, tol: float = 1e-11) -> bool:
    if x == 0.0:
        return True
    idx = bisect.bisect_left(sorted_floats, x)
    if idx < len(sorted_floats):
        cand = sorted_floats[idx]
        if abs(cand - x) <= tol * abs(x):
            return True
    if idx > 0:
        cand = sorted_floats[idx - 1]
        if abs(cand - x) <= tol * abs(x):
            return True
    return False


def eval_linear(bits: int, lo_exp: int, hi_exp: int, rng_state: list[int]) -> list[dict]:
    all_set, all_floats, vals, val_floats = collect_linear(bits, lo_exp, hi_exp)
    n = len(vals)
    sampled = bits != 8
    # Integer representation of fractions via exact cross-check only when float filter hits
    # Precompute exact squares / sqrts for unary ops quickly
    rows = []
    # Precompute integer scaled values for mul/div: every Linear Takum is an exact dyadic fraction!
    # Map each Fraction v to (odd_mant, exp2) where v = odd_mant * 2^exp2.
    def to_dyadic(f: Fraction) -> tuple[int, int]:
        num, den = f.numerator, f.denominator
        # den is a power of 2
        e2 = den.bit_length() - 1
        tz = (num & -num).bit_length() - 1
        return (num >> tz, tz - e2)

    all_dyadic = {to_dyadic(v) for v in all_set}
    val_dyadic = [to_dyadic(v) for v in vals]

    print(f"  (linear T{bits}: {n} valores; {'pares amostrados' if sampled else 'exaustivo'})")
    for op in OPS:
        exact = 0
        total = 0
        if op in ("inv", "sqrt", "square"):
            for i in range(n):
                total += 1
                v = vals[i]
                if op == "inv":
                    ok = (Fraction(1, 1) / v) in all_set
                elif op == "square":
                    ok = (v * v) in all_set
                else:
                    num, den = v.numerator, v.denominator
                    sn = math.isqrt(num)
                    sd = math.isqrt(den)
                    ok = (sn * sn == num and sd * sd == den and Fraction(sn, sd) in all_set)
                exact += int(ok)
        elif not sampled:
            for i in range(n):
                vi = vals[i]
                fi = val_floats[i]
                j_end = i + 1 if op == "sub" else n
                for j in range(j_end):
                    vj = vals[j]
                    fj = val_floats[j]
                    total += 1
                    if op == "add":
                        if near_in_sorted(all_floats, fi + fj) and (vi + vj) in all_set:
                            exact += 1
                    elif op == "sub":
                        if i == j or (near_in_sorted(all_floats, fi - fj) and (vi - vj) in all_set):
                            exact += 1
                    elif op == "mul":
                        mi, ei = val_dyadic[i]
                        mj, ej = val_dyadic[j]
                        if near_in_sorted(all_floats, fi * fj):
                            if (vi * vj) in all_set:
                                exact += 1
                    elif op == "div":
                        if near_in_sorted(all_floats, fi / fj):
                            if (vi / vj) in all_set:
                                exact += 1
        else:
            for _ in range(SAMPLES):
                i = xorshift64(rng_state) % n
                j = xorshift64(rng_state) % n
                if op == "sub" and vals[i] < vals[j]:
                    continue
                total += 1
                vi, vj = vals[i], vals[j]
                fi, fj = val_floats[i], val_floats[j]
                if op in ("add", "sub"):
                    big, small = (fi, fj) if fi >= fj else (fj, fi)
                    if small != 0.0 and small < big * 2e-15:
                        continue
                if op == "add":
                    if near_in_sorted(all_floats, fi + fj) and (vi + vj) in all_set:
                        exact += 1
                elif op == "sub":
                    if i == j or (near_in_sorted(all_floats, fi - fj) and (vi - vj) in all_set):
                        exact += 1
                elif op == "mul":
                    if near_in_sorted(all_floats, fi * fj) and (vi * vj) in all_set:
                        exact += 1
                elif op == "div":
                    if near_in_sorted(all_floats, fi / fj) and (vi / vj) in all_set:
                        exact += 1

        pct = 100.0 * exact / total
        mode = "amostrado" if sampled else "exaustivo"
        print(f"  linear T{bits:<3} {op:<7} {exact:>6}/{total:<7} = {pct:6.2f}% ({mode})")
        rows.append({
            "variant": "linear",
            "width": str(bits),
            "op": op,
            "exact": str(exact),
            "total": str(total),
            "pct_exact": f"{pct:.4f}",
            "modo": mode,
        })
    return rows


def eval_log(bits: int, lo_exp: int, hi_exp: int, rng_state: list[int]) -> list[dict]:
    all_int_set, all_floats, all_dec_set, vals_ell, vals_int, val_floats, vals_dec = collect_log(bits, lo_exp, hi_exp)
    n = len(vals_int)
    sampled = bits != 8
    fmt = LogTakum(bits)

    rows = []
    print(f"  (log T{bits}: {n} valores; {'pares amostrados' if sampled else 'exaustivo'})")
    for op in OPS:
        exact = 0
        total = 0
        if op in ("inv", "sqrt", "square"):
            for i in range(n):
                total += 1
                iv = vals_int[i]
                if op == "inv":
                    ok = (-iv) in all_int_set
                elif op == "square":
                    ok = (2 * iv) in all_int_set
                else:
                    ok = (iv % 2 == 0) and ((iv // 2) in all_int_set)
                exact += int(ok)
        elif not sampled:
            for i in range(n):
                fi = val_floats[i]
                ivi = vals_int[i]
                j_end = i + 1 if op == "sub" else n
                for j in range(j_end):
                    fj = val_floats[j]
                    ivj = vals_int[j]
                    total += 1
                    if op == "add":
                        if near_in_sorted(all_floats, fi + fj):
                            with localcontext() as ctx:
                                ctx.prec = 80
                                if (vals_dec[i] + vals_dec[j]) in all_dec_set:
                                    exact += 1
                    elif op == "sub":
                        if i == j:
                            exact += 1
                        elif near_in_sorted(all_floats, fi - fj):
                            with localcontext() as ctx:
                                ctx.prec = 80
                                if (vals_dec[i] - vals_dec[j]) in all_dec_set:
                                    exact += 1
                    elif op == "mul":
                        if (ivi + ivj) in all_int_set:
                            exact += 1
                    elif op == "div":
                        if (ivi - ivj) in all_int_set:
                            exact += 1
        else:
            for _ in range(SAMPLES):
                i = xorshift64(rng_state) % n
                j = xorshift64(rng_state) % n
                if op == "sub" and vals_int[i] < vals_int[j]:
                    continue
                total += 1
                if op == "add":
                    fi, fj = val_floats[i], val_floats[j]
                    big, small = (fi, fj) if fi >= fj else (fj, fi)
                    if small != 0.0 and small < big * 2e-15:
                        continue
                    if near_in_sorted(all_floats, fi + fj):
                        with localcontext() as ctx:
                            ctx.prec = 80
                            s = vals_dec[i] + vals_dec[j]
                            c = fmt.encode(s)
                            if abs(fmt.decode(c) - s) <= Decimal("1e-70") * s:
                                exact += 1
                elif op == "sub":
                    if i == j:
                        exact += 1
                    else:
                        fi, fj = val_floats[i], val_floats[j]
                        big, small = (fi, fj) if fi >= fj else (fj, fi)
                        if small != 0.0 and small < big * 2e-15:
                            continue
                        if near_in_sorted(all_floats, fi - fj):
                            with localcontext() as ctx:
                                ctx.prec = 80
                                d = vals_dec[i] - vals_dec[j]
                                c = fmt.encode(d)
                                if abs(fmt.decode(c) - d) <= Decimal("1e-70") * d:
                                    exact += 1
                elif op == "mul":
                    if (vals_int[i] + vals_int[j]) in all_int_set:
                        exact += 1
                elif op == "div":
                    if (vals_int[i] - vals_int[j]) in all_int_set:
                        exact += 1

        pct = 100.0 * exact / total
        mode = "amostrado" if sampled else "exaustivo"
        print(f"  log    T{bits:<3} {op:<7} {exact:>6}/{total:<7} = {pct:6.2f}% ({mode})")
        rows.append({
            "variant": "log",
            "width": str(bits),
            "op": op,
            "exact": str(exact),
            "total": str(total),
            "pct_exact": f"{pct:.4f}",
            "modo": mode,
        })
    return rows


def main() -> int:
    rng_state = [SEED]
    rows: list[dict] = []
    for bits, lo_exp, hi_exp in ((8, -24, 24), (16, -56, 56)):
        rows.extend(eval_linear(bits, lo_exp, hi_exp, rng_state))
    for bits, lo_exp, hi_exp in ((8, -24, 24), (16, -56, 56)):
        rows.extend(eval_log(bits, lo_exp, hi_exp, rng_state))

    # Cross-validate against committed baseline if present before overwriting
    if OUT_CSV.exists():
        with OUT_CSV.open(encoding="utf-8") as handle:
            prev = list(csv.DictReader(handle))
        prev_map = {(r["variant"], r["width"], r["op"]): r for r in prev}
        diffs = []
        for r in rows:
            k = (r["variant"], r["width"], r["op"])
            if k in prev_map:
                pe, pt = int(prev_map[k]["exact"]), int(prev_map[k]["total"])
                ne, nt = int(r["exact"]), int(r["total"])
                if pe != ne or pt != nt:
                    diffs.append((k, (pe, pt), (ne, nt)))
        if diffs:
            print(f"[nota] {len(diffs)} diferenças frente ao CSV C11 anterior (long double vs aritmética exata):")
            for k, old_v, new_v in diffs[:10]:
                print(f"  {k}: C11={old_v} -> Python={new_v}")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["variant", "width", "op", "exact", "total", "pct_exact", "modo"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"gravado: {OUT_CSV} ({len(rows)} linhas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
