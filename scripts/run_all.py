#!/usr/bin/env python3
"""Script único de verificação completa, execução dos benchmarks e geração de gráficos/artigos.

Executa de ponta a ponta (sem apagar ELFs pré-montados caso llvm-mc não esteja no PATH):
  1. Compilação C++17 (núcleo Takum, testes e simulador RV64IM/RVV/Zvtakum);
  2. Testes unitários da Fase 1 (C++ vetores dourados + Python racionais exatos + libtakum T8);
  3. Testes do simulador da Fase 2 (zt-test + difftest contra QEMU 10.2.2 e modelo Python);
  4. Kernels SpMV RISC-V (96 execuções bit-exatas no zt-sim) e modelo analítico de contagem;
  5. Baselines numéricos expandidos (IEEE FP16/FP32, bfloat16, OCP E4M3/E5M2 c/ e s/ saturação,
     Takum8/16/32, nos cenários sem escala e pow2-bound, mais erros por linha vs Float128);
  6. Geração de todas as tabelas LaTeX (EN/PT), macros e figuras vetoriais (matplotlib PDF/SVG);
  7. Compilação dos diagramas TikZ, dos artigos IEEE (EN/PT) e dos slides.

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


def main() -> int:
    t_start = time.monotonic()

    # 1. Compilação C++17
    run_step("1. Build C++17 (takum-test, zt-sim, zt-test)",
             ["make", "build", "sim", "build/zt-test"])

    # 2. Testes unitários Fase 1 (C++ + Python)
    run_step("2a. Testes C++ do núcleo Takum (Fase 1)", ["./build/takum-test"])
    run_step("2b. Testes Python (modelo exato, libtakum T8, binários IEEE/OFP8/BF16)",
             [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
             cwd=ROOT / "python")

    # 3. Testes do simulador Fase 2 (C++ + difftest QEMU/Python)
    run_step("3a. Testes C++ do simulador Zvtakum (zt-test)", ["./build/zt-test"])
    if shutil.which("qemu-riscv64"):
        run_step("3b. Verificação diferencial (QEMU 10.2.2 + modelo Python)",
                 [sys.executable, "tests/sim/difftest.py"])
    else:
        print("\n[AVISO] qemu-riscv64 ausente; executando apenas zvtakum_isa no difftest.")
        run_step("3b. Verificação diferencial Zvtakum (modelo Python)",
                 [sys.executable, "tests/sim/difftest.py", "--only", "zvtakum_isa"])

    # 4. Benchmarks SpMV no simulador e modelo analítico de instruções
    run_step("4a. Execução dos 96 kernels SpMV RISC-V no zt-sim",
             [sys.executable, "kernels/spmv.py"])
    run_step("4b. Ajuste/verificação do modelo analítico N = rR + cS + K",
             [sys.executable, "kernels/modelo_contagem.py"])

    # 5. Baselines numéricos expandidos (com/sem escala + distribuição por linha vs Float128)
    run_step("5. Baselines numéricos expandidos (IEEE, OFP8, BF16, Takum vs Float128)",
             [sys.executable, "kernels/numeric_baselines.py"])

    # 6. Geração de tabelas LaTeX e gráficos vetoriais matplotlib
    run_step("6a. Geração das tabelas e macros LaTeX (EN/PT)",
             [sys.executable, "paper/gera_tabelas.py"])
    run_step("6b. Geração dos gráficos vetoriais (tapered-precision, error-cdf, insn-csr)",
             [sys.executable, "paper/gera_figuras.py"])

    # 7. Compilação LaTeX (TikZ standalone + Artigos EN/PT + Slides)
    if shutil.which("pdflatex"):
        run_step("7a. Compilação dos diagramas TikZ standalone",
                 ["pdflatex", "-interaction=nonstopmode", "datapath_zvtakum.tex"],
                 cwd=ROOT / "paper" / "figures")
        run_step("7b. Compilação do diagrama TikZ PT standalone",
                 ["pdflatex", "-interaction=nonstopmode", "datapath_zvtakum_pt.tex"],
                 cwd=ROOT / "paper" / "figures")

        def compile_ieee_doc(step_label: str, stem: str, cwd: Path) -> None:
            run_step(f"{step_label} (pass 1)",
                     ["pdflatex", "-interaction=nonstopmode", f"{stem}.tex"], cwd=cwd)
            if shutil.which("bibtex"):
                run_step(f"{step_label} (bibtex)", ["bibtex", stem], cwd=cwd)
            run_step(f"{step_label} (pass 2)",
                     ["pdflatex", "-interaction=nonstopmode", f"{stem}.tex"], cwd=cwd)
            run_step(f"{step_label} (pass 3)",
                     ["pdflatex", "-interaction=nonstopmode", f"{stem}.tex"], cwd=cwd)

        compile_ieee_doc("7c. Compilação do Artigo IEEE em Inglês (paper/main.pdf)",
                         "main", ROOT / "paper")
        if (ROOT / "paper" / "main_pt.tex").exists():
            compile_ieee_doc("7d. Compilação do Artigo IEEE em Português (paper/main_pt.pdf)",
                             "main_pt", ROOT / "paper")
        if (ROOT / "slides" / "slides.tex").exists():
            run_step("7e. Compilação dos slides Beamer (pass 1)",
                     ["pdflatex", "-interaction=nonstopmode", "slides.tex"],
                     cwd=ROOT / "slides")
            run_step("7f. Compilação dos slides Beamer (pass 2)",
                     ["pdflatex", "-interaction=nonstopmode", "slides.tex"],
                     cwd=ROOT / "slides")

    total = time.monotonic() - t_start
    print(f"\n==========================================")
    print(f"PIPELINE COMPLETO CONCLUÍDO COM SUCESSO em {total:.1f}s")
    print(f"==========================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
