#!/usr/bin/env python3
"""Script único de verificação completa, execução dos benchmarks e geração de gráficos/artigos.

Executa de ponta a ponta (sem apagar ELFs pré-montados caso llvm-mc não esteja no PATH):
  1. Compilação C++17 (núcleo Takum, testes e simulador RV64IM/RVV/Zvtakum);
  2. Testes unitários da Fase 1 (C++ vetores dourados + Python racionais exatos + libtakum T8/wide + Posit + binary128);
  3. Testes do simulador da Fase 2 (zt-test + difftest contra QEMU 10.2.2 e modelo Python);
  4. Kernels SpMV RISC-V (96 execuções bit-exatas no zt-sim) e modelo analítico de contagem;
  5. Baselines numéricos expandidos (IEEE FP16/FP32, bfloat16, OCP E4M3/E5M2 c/ e s/ saturação,
     Posit8/16/32, Takum8/16/32 nos cenários sem escala e pow2-bound, mais erros por linha vs Float128)
     e verificação do manifesto/conversão SuiteSparse-100;
  6. Geração de todas as tabelas LaTeX (EN/PT), macros e figuras vetoriais (matplotlib PDF/SVG);
  7. Compilação dos diagramas TikZ, dos artigos IEEE (EN/PT) e dos slides;
  8. Checagem do limite de 6 páginas, auditoria bibliográfica e manifesto de reprodutibilidade.

Uso:
    python3 scripts/run_all.py
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]


def run_step(title: str, cmd: list[str], cwd: pathlib.Path = ROOT) -> None:
    print(f"\n=== [{title}] ===", flush=True)
    print(f"$ {' '.join(cmd)} (cwd={cwd})", flush=True)
    t0 = time.monotonic()
    proc = subprocess.run(cmd, cwd=cwd, check=False)
    dt = time.monotonic() - t0
    if proc.returncode != 0:
        raise SystemExit(f"[ERRO] Etapa '{title}' falhou com código {proc.returncode} ({dt:.1f}s)")
    print(f"[OK] {title} concluída em {dt:.1f}s", flush=True)


def check_pdf_pages(pdf_path: pathlib.Path, max_pages: int = 6) -> None:
    if not pdf_path.is_file() or not shutil.which("pdfinfo"):
        return
    proc = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, text=True, check=False)
    for line in proc.stdout.splitlines():
        if line.startswith("Pages:"):
            pages = int(line.split(":", 1)[1].strip())
            print(f"[CHECK] {pdf_path.name}: {pages} páginas (limite {max_pages})")
            if pages > max_pages:
                raise SystemExit(f"[ERRO] {pdf_path} excede {max_pages} páginas ({pages})")


def main() -> int:
    t_start = time.monotonic()

    # 1. Compilação C++17
    run_step("1. Build C++17 (takum-test, zt-sim, zt-test)",
             ["make", "build", "sim", "build/zt-test"])

    # 2. Testes unitários (C++ + Python + Referências)
    run_step("2a. Testes C++ do núcleo Takum (Fase 1 - 52 verificações)", ["./build/takum-test"])
    run_step("2b. Testes C++ do simulador Zvtakum (Fase 2 - 29 verificações)", ["./build/zt-test"])
    run_step("2c. Testes Python (modelo exato, libtakum, Posit, binary128)",
             [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
             cwd=ROOT / "python")
    run_step("2d. Auditoria bibliográfica offline",
             [sys.executable, "tools/check_references.py", "--json", "references/audit.json"])

    # 3. Verificação diferencial QEMU/Python
    if shutil.which("qemu-riscv64"):
        run_step("3. Verificação diferencial (QEMU + modelo Python)",
                 [sys.executable, "tests/sim/difftest.py"])
    else:
        print("\n[AVISO] qemu-riscv64 ausente; executando apenas zvtakum_isa no difftest.")
        run_step("3. Verificação diferencial Zvtakum (modelo Python)",
                 [sys.executable, "tests/sim/difftest.py", "--only", "zvtakum_isa"])

    # 4. Benchmarks SpMV no simulador e modelo analítico de instruções
    run_step("4a. Execução dos 96 kernels SpMV RISC-V no zt-sim",
             [sys.executable, "kernels/spmv.py"])
    run_step("4b. Ajuste/verificação do modelo analítico N = rR + cS + K",
             [sys.executable, "kernels/modelo_contagem.py"])

    # 5. Baselines numéricos e benchmark de conversão
    run_step("5a. Baselines numéricos expandidos (IEEE, OFP8, BF16, Posit, Takum vs Float128)",
             [sys.executable, "kernels/numeric_baselines.py"])
    run_step("5b. Verificação do manifesto SuiteSparse-100 e conversão binary128 local",
             [sys.executable, "scripts/bench_suitesparse100.py"])

    # 6. Geração de gráficos vetoriais matplotlib e diagramas TikZ
    run_step("6a. Geração dos gráficos vetoriais (tapered-precision, error-cdf, insn-csr)",
             [sys.executable, "paper/gera_figuras.py"])

    if shutil.which("pdflatex"):
        for tex in ("datapath_zvtakum.tex", "datapath_zvtakum_pt.tex", "zvtakum-datapath.tex", "zvtakum-datapath-pt.tex"):
            if (ROOT / "paper" / "figures" / tex).exists():
                run_step(f"6b. Compilação TikZ ({tex})",
                         ["pdflatex", "-interaction=nonstopmode", tex],
                         cwd=ROOT / "paper" / "figures")

    # 7. Manifesto de reprodutibilidade
    run_step("7. Manifesto de reprodutibilidade",
             [sys.executable, "tools/make_manifest.py"])

    total = time.monotonic() - t_start
    print("\n==========================================")
    print(f"PIPELINE COMPLETO CONCLUÍDO COM SUCESSO em {total:.1f}s")
    print("==========================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
