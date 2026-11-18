#!/usr/bin/env python3
"""Write a reproducibility manifest with tool versions, git state, logs and hashes."""

from __future__ import annotations

import hashlib
import json
import pathlib
import platform
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
LOGS = ARTIFACTS / "logs"


def command(*args: str) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, check=False)
        output = (result.stdout or result.stderr).strip()
        return output.splitlines()[0] if output else "clean"
    except Exception as exc:  # noqa: BLE001
        return f"unavailable: {exc}"


def sha256(path: pathlib.Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def log_summary(name: str) -> dict[str, str]:
    path = LOGS / name
    if not path.is_file():
        return {"status": "missing"}
    text = path.read_text(encoding="utf-8", errors="replace")
    summary: dict[str, str] = {"status": "present"}
    for pattern, key in (
        (r"(\d+) verificações, (\d+) falhas", "cpp_tests"),
        (r"Ran (\d+) tests", "python_tests"),
        (r"(\d+) divergências", "divergences"),
        (r"(\d+) execuções, (\d+) divergências", "differential"),
    ):
        matches = re.findall(pattern, text)
        if matches:
            summary[key] = ", ".join(
                m if isinstance(m, str) else "/".join(m) for m in matches
            )
    return summary


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    git_head = command("git", "-C", str(ROOT), "rev-parse", "HEAD")
    git_branch = command("git", "-C", str(ROOT), "rev-parse", "--abbrev-ref", "HEAD")
    git_status = command("git", "-C", str(ROOT), "status", "--porcelain")
    skipped_path = ARTIFACTS / "skipped.txt"
    skipped = (
        [line for line in skipped_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if skipped_path.is_file()
        else []
    )
    manifest = {
        "project": "aoc-takum-riscv",
        "date_utc": command("date", "-u", "+%Y-%m-%dT%H:%M:%SZ"),
        "platform": platform.platform(),
        "python": sys.version,
        "git_branch": git_branch,
        "git_head": git_head,
        "git_status": git_status or "clean",
        "versions": {
            "g++": command("g++", "--version"),
            "qemu-riscv64": command("qemu-riscv64", "--version"),
            "llvm-mc": command("llvm-mc", "--version"),
            "pdflatex": command("pdflatex", "--version"),
            "latexmk": command("latexmk", "--version"),
            "pdfinfo": command("pdfinfo", "-v"),
        },
        "skipped": skipped,
        "logs": {
            name: log_summary(name)
            for name in (
                "cpp-tests.log",
                "python-tests.log",
                "difftest.log",
                "numeric.log",
                "closure.log",
                "references-offline.log",
                "references-online.log",
            )
        },
        "artifacts_sha256": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (
                ROOT / "paper" / "figures" / "tapered-precision.pdf",
                ROOT / "paper" / "figures" / "tapered-precision-pt.pdf",
                ROOT / "paper" / "figures" / "error-cdf.pdf",
                ROOT / "paper" / "figures" / "error-cdf-pt.pdf",
                ROOT / "paper" / "figures" / "insn-csr-comparison.pdf",
                ROOT / "paper" / "figures" / "insn-csr-comparison-pt.pdf",
                ROOT / "paper" / "figures" / "datapath_zvtakum.pdf",
                ROOT / "paper" / "figures" / "datapath_zvtakum_pt.pdf",
                ROOT / "results" / "spmv_hb.csv",
                ROOT / "results" / "spmv_numerico_hb.csv",
                ROOT / "results" / "spmv_numerico_scaled_hb.csv",
                ROOT / "results" / "spmv_row_errors_hb.csv",
                ROOT / "results" / "closure_takum_linear_log.csv",
                ROOT / "results" / "suitesparse100_conversion.csv",
                ROOT / "results" / "suitesparse100_manifest.json",
                ROOT / "results" / "modelo_contagem.csv",
                ROOT / "references" / "audit.csv",
            )
        },
    }
    output = ARTIFACTS / "manifest.json"
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"manifesto: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
