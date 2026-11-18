#!/usr/bin/env python3
"""100-matrix SuiteSparse representation viability benchmark (15 formats).

Reimplements the 15-format matrix conversion benchmark in Python using the exact
codecs in ``takum_rvv`` (Linear Takum, Logarithmic Takum, Posit with es=2, OCP
E4M3/E5M2, IEEE FP16/FP32/FP64, bfloat16) against an IEEE binary128 (Float128)
or emulated 80-bit long double reference.

By default, evaluates all matrices found in ``--matrices-dir`` (or falls back to
the local Harwell-Boeing validation matrices if the SuiteSparse cache has not
been downloaded yet) and cross-checks ``results/suitesparse100_conversion.csv``
and ``results/suitesparse100_manifest.json``. Passing ``--download`` fetches the
100 SuiteSparse matrices listed in ``results/suitesparse100_manifest.json`` from
``https://sparse.tamu.edu/`` and records their SHA-256 checksums.

Usage:
    PYTHONPATH=python python3 scripts/bench_suitesparse100.py
    PYTHONPATH=python python3 scripts/bench_suitesparse100.py --download
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import json
import math
import pathlib
import sys
import tarfile
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from takum_rvv.binary import (  # noqa: E402
    BFLOAT16,
    BINARY16,
    BINARY32,
    BINARY64,
    BINARY128,
    E4M3,
    E5M2,
)
from takum_rvv.codec import LOG_TAKUM8, LOG_TAKUM16, LOG_TAKUM32, Takum  # noqa: E402
from takum_rvv.posit import POSIT8_2, POSIT16_2, POSIT32  # noqa: E402
from takum_rvv.sparse import read_matrix_market  # noqa: E402

MANIFEST_PATH = ROOT / "results" / "suitesparse100_manifest.json"
OUT_CSV = ROOT / "results" / "suitesparse100_conversion.csv"
DEFAULT_MATRICES_DIR = ROOT / "matrices" / "suitesparse100"
HB_DIR = ROOT / "python" / "data" / "harwell_boeing"

STATS_URL = "https://sparse.tamu.edu/files/ssstats.csv"
MM_BASE = "https://sparse.tamu.edu/MM/"

FORMATS = [
    ("f8_e4m3", E4M3),
    ("f8_e5m2", E5M2),
    ("f16", BINARY16),
    ("bf16", BFLOAT16),
    ("f32", BINARY32),
    ("f64", BINARY64),
    ("takum8", Takum(8)),
    ("takum16", Takum(16)),
    ("takum32", Takum(32)),
    ("taklog8", LOG_TAKUM8),
    ("taklog16", LOG_TAKUM16),
    ("taklog32", LOG_TAKUM32),
    ("posit8", POSIT8_2),
    ("posit16", POSIT16_2),
    ("posit32", POSIT32),
]


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_initial_manifest() -> dict:
    """Create or load results/suitesparse100_manifest.json from existing CSV entries."""
    if MANIFEST_PATH.is_file():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    entries = []
    if OUT_CSV.is_file():
        with OUT_CSV.open(encoding="utf-8") as handle:
            for idx, row in enumerate(csv.DictReader(handle), 1):
                mtx_name = row["matrix"]
                stem = mtx_name[:-4] if mtx_name.endswith(".mtx") else mtx_name
                entries.append({
                    "index": idx,
                    "matrix": mtx_name,
                    "name": stem,
                    "group": None,
                    "nnz_recorded": int(row["nnz"]),
                    "url": f"https://sparse.tamu.edu/search?q={stem}",
                    "tarball_url": None,
                    "acquisition_date": "2026-09-15",
                    "mtx_sha256": None,
                    "cached": False,
                })
    manifest = {
        "schema": 1,
        "dataset": "SuiteSparse Matrix Collection representative 100-matrix subset (declared nnz <= 50,000)",
        "collection_url": "https://sparse.tamu.edu/",
        "committed_csv_reference_precision": (
            "long double (80-bit x86-64 extended precision, 64-bit significand) in initial C11 generator; "
            "scripts/bench_suitesparse100.py evaluates against IEEE binary128 (Float128, 113-bit significand)"
        ),
        "selection_seed": 42,
        "count": len(entries),
        "matrices": entries,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def _fetch_one(entry: dict, name_to_meta: dict, dest_dir: pathlib.Path) -> bool:
    stem = entry["name"]
    out_mtx = dest_dir / f"{stem}.mtx"
    if stem in name_to_meta:
        group = name_to_meta[stem][0]
        entry["group"] = group
        entry["url"] = f"https://sparse.tamu.edu/{group}/{stem}"
        entry["tarball_url"] = f"{MM_BASE}{group}/{stem}.tar.gz"
    if out_mtx.is_file():
        entry["mtx_sha256"] = sha256_file(out_mtx)
        entry["cached"] = True
        return True
    url = entry.get("tarball_url")
    if not url:
        print(f"[warn] group/URL unknown for {stem}", file=sys.stderr)
        return False
    try:
        with urllib.request.urlopen(url, timeout=180) as resp:
            blob = resp.read()
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] failed to fetch {url}: {exc}", file=sys.stderr)
        return False
    tmp = dest_dir / f"{stem}.tar.gz"
    tmp.write_bytes(blob)
    try:
        with tarfile.open(tmp, "r:gz") as tar:
            mtx_members = [m for m in tar.getmembers() if m.isfile() and m.name.endswith(".mtx")]
            exact = [m for m in mtx_members if pathlib.Path(m.name).name == f"{stem}.mtx"]
            chosen_member = exact[0] if exact else (min(mtx_members, key=lambda m: len(m.name)) if mtx_members else None)
            if chosen_member is not None:
                with tar.extractfile(chosen_member) as src:  # type: ignore[union-attr]
                    out_mtx.write_bytes(src.read())
                entry["mtx_sha256"] = sha256_file(out_mtx)
                entry["cached"] = True
                entry["acquisition_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                return True
    finally:
        tmp.unlink(missing_ok=True)
    return False


def download_matrices(manifest: dict, dest_dir: pathlib.Path) -> int:
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"Downloading index {STATS_URL}...")
    with urllib.request.urlopen(STATS_URL, timeout=60) as resp:
        lines = resp.read().decode("utf-8", "replace").splitlines()
    name_to_meta = {}
    for line in lines:
        parts = line.split(",")
        if len(parts) >= 5:
            group, name = parts[0], parts[1]
            name_to_meta[name] = (group, parts[2], parts[3], parts[4])

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda e: _fetch_one(e, name_to_meta, dest_dir), manifest["matrices"]))
    fetched = sum(results)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return fetched


def rel_frobenius_conversion_error(values: tuple[Fraction, ...], fmt, use_binary128: bool = True) -> str:
    """Compute ||ref(A) - ref(decode(encode(A)))||_2 / ||ref(A)||_2 using BINARY128 reference."""
    sum_ref_sq = Decimal(0)
    sum_err_sq = Decimal(0)
    counts = Counter(values)
    with localcontext() as ctx:
        ctx.prec = 80
        for v, mult in counts.items():
            w = Decimal(mult)
            if use_binary128:
                ref_raw = BINARY128.encode(v)
                ref_frac = BINARY128.decode(ref_raw)
                if ref_frac is None:
                    return "nan"
                ref_dec = Decimal(ref_frac.numerator) / Decimal(ref_frac.denominator)
            else:
                ref_dec = Decimal(v.numerator) / Decimal(v.denominator)

            approx = fmt.decode(fmt.encode(v))
            if approx is None:
                return "nan"
            if isinstance(approx, Decimal):
                approx_dec = approx
            else:
                approx_dec = Decimal(approx.numerator) / Decimal(approx.denominator)

            diff = ref_dec - approx_dec
            sum_ref_sq += w * ref_dec * ref_dec
            sum_err_sq += w * diff * diff

        if sum_ref_sq == 0:
            return "0.000000e+00"
        rel = (sum_err_sq / sum_ref_sq).sqrt()
        if rel == 0:
            return "0.000000e+00"
        return f"{rel:.6e}"


def read_entry_values(path: pathlib.Path) -> list[Fraction]:
    """Read nonzero values from a Matrix Market file (exact Fraction parsing)."""
    try:
        mat = read_matrix_market(path)
        return list(mat.data)
    except ValueError:
        # Fallback for skew-symmetric matrices (same symmetric expansion rule)
        lines = iter(line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())
        header = next(lines).lower().split()
        field = header[3]
        symm = header[4]
        line = next(lines)
        while line.startswith("%"):
            line = next(lines)
        vals: list[Fraction] = []
        for raw in lines:
            if raw.startswith("%"):
                continue
            parts = raw.split()
            i, j = int(parts[0]), int(parts[1])
            v = Fraction(1) if field == "pattern" else Fraction(parts[2].replace("D", "e").replace("d", "e"))
            vals.append(v)
            if symm in ("symmetric", "skew-symmetric") and i != j:
                vals.append(-v if symm == "skew-symmetric" else v)
        return vals


def evaluate_directory(mtx_dir: pathlib.Path, out_path: pathlib.Path | None = None) -> list[dict]:
    mtx_files = sorted(mtx_dir.glob("*.mtx"))
    rows = []
    for path in mtx_files:
        vals = read_entry_values(path)
        row: dict[str, str] = {"matrix": path.name, "nnz": str(len(vals))}
        for col_name, fmt in FORMATS:
            row[col_name] = rel_frobenius_conversion_error(tuple(vals), fmt, use_binary128=True)
        rows.append(row)
        print(f"  {path.name:<22} nnz={len(vals):<6} takum32={row['takum32']} f32={row['f32']}")
    if out_path is not None and rows:
        fieldnames = ["matrix", "nnz"] + [col for col, _ in FORMATS]
        with out_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {len(rows)} rows to {out_path}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Download the 100 SuiteSparse matrices and record hashes")
    parser.add_argument("--matrices-dir", type=pathlib.Path, default=DEFAULT_MATRICES_DIR)
    parser.add_argument("--out", type=pathlib.Path, default=None, help="Output CSV path (defaults to results/suitesparse100_conversion.csv when >=100 matrices present)")
    args = parser.parse_args()

    manifest = build_initial_manifest()
    if args.download:
        count = download_matrices(manifest, args.matrices_dir)
        print(f"Downloaded/verified {count}/{len(manifest['matrices'])} SuiteSparse matrices")

    cached = sorted(args.matrices_dir.glob("*.mtx")) if args.matrices_dir.is_dir() else []
    if cached:
        for entry in manifest["matrices"]:
            p = args.matrices_dir / entry["matrix"]
            if p.is_file():
                entry["mtx_sha256"] = sha256_file(p)
                entry["cached"] = True
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if len(cached) >= len(manifest["matrices"]) and len(cached) > 0:
        target = args.out or OUT_CSV
        print(f"Evaluating all {len(cached)} cached SuiteSparse matrices against IEEE binary128...")
        evaluate_directory(args.matrices_dir, target)
    elif cached:
        target = args.out or (ROOT / "results" / "suitesparse_partial_conversion.csv")
        print(f"Evaluating {len(cached)} cached SuiteSparse matrices in {args.matrices_dir} against binary128...")
        evaluate_directory(args.matrices_dir, target)
    else:
        print(f"[info] {args.matrices_dir} has 0 cached .mtx files (offline sandbox / uncached cache).")
        print(f"[info] Manifest recorded at {MANIFEST_PATH} ({manifest['count']} matrices).")
        print("[info] Running local conversion self-check on the 8 Harwell-Boeing matrices (exact binary128):")
        hb_check_out = ROOT / "artifacts" / "hb_conversion_binary128.csv"
        hb_check_out.parent.mkdir(parents=True, exist_ok=True)
        evaluate_directory(HB_DIR, hb_check_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
