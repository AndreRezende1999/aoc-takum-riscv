#!/usr/bin/env python3
"""Validate that every BibTeX key has a verified audit row.

Offline (default): checks the committed audit CSV and the keys in refs.bib.
Online (--online): additionally resolves DOIs through Crossref/DataCite and
performs HTTP HEAD requests for URLs.
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
BIB = ROOT / "paper" / "refs.bib"
AUDIT = ROOT / "references" / "audit.csv"
KEY = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,")


def bib_keys() -> list[str]:
    if BIB.is_file():
        return KEY.findall(BIB.read_text(encoding="utf-8"))
    return list(audit_rows().keys())


def audit_rows() -> dict[str, dict[str, str]]:
    with AUDIT.open(newline="", encoding="utf-8") as handle:
        return {row["key"]: row for row in csv.DictReader(handle)}


def online_check(identifier: str) -> tuple[bool, str]:
    if identifier.startswith("10.48550/arXiv."):
        arxiv_id = identifier.rsplit("arXiv.", 1)[1]
        url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                body = response.read().decode("utf-8", "replace")
            return "<entry>" in body, "arXiv API resolved"
        except Exception as exc:  # noqa: BLE001
            return False, f"arXiv: {exc}"
    if identifier.startswith("10.5281/zenodo."):
        url = f"https://api.datacite.org/dois/{identifier}"
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                json.loads(response.read().decode("utf-8"))
            return True, "DataCite DOI resolved"
        except Exception as exc:  # noqa: BLE001
            return False, f"DataCite: {exc}"
    if identifier.startswith("10."):
        url = f"https://api.crossref.org/works/{identifier}"
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "aoc-takum-riscv/1.0"})
            with urllib.request.urlopen(request, timeout=20) as response:
                json.loads(response.read().decode("utf-8"))
            return True, "Crossref DOI resolved"
        except Exception as exc:  # noqa: BLE001
            return False, f"Crossref: {exc}"
    if identifier.startswith("http"):
        try:
            request = urllib.request.Request(
                identifier, method="HEAD", headers={"User-Agent": "aoc-takum-riscv/1.0"}
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                return 200 <= response.status < 400, f"HTTP {response.status}"
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 405):
                return True, f"HTTP {exc.code} (reachable, method blocked)"
            return False, f"HTTP {exc.code}"
        except Exception as exc:  # noqa: BLE001
            return False, f"HTTP: {exc}"
    return True, "not an HTTP/DOI identifier; skipped online check"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--json", type=pathlib.Path, default=None)
    args = parser.parse_args()

    keys = bib_keys()
    audit = audit_rows()
    missing = [key for key in keys if key not in audit]
    unverified = [
        key for key in keys
        if key in audit and not audit[key]["status"].startswith("verified")
    ]
    report = {
        "bib_keys": keys,
        "missing": missing,
        "unverified": unverified,
        "online": {},
    }
    failures = bool(missing or unverified)

    if args.online:
        for key in keys:
            row = audit.get(key)
            if not row:
                continue
            ok, detail = online_check(row["identifier"])
            report["online"][key] = {"ok": ok, "detail": detail}
            if not ok:
                failures = True

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if missing:
        print("missing audit rows:", ", ".join(missing))
    if unverified:
        print("unverified audit rows:", ", ".join(unverified))
    if args.online:
        for key, result in report["online"].items():
            print(f"{key}: {'ok' if result['ok'] else 'FAIL'} - {result['detail']}")
    print(f"checked {len(keys)} BibTeX keys against {AUDIT.relative_to(ROOT)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
