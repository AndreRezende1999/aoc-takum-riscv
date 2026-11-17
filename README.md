# Projeto Integrador AOC — Takum na Extensão Vetorial RISC-V (`Zvtakum`)

Este repositório implementa e avalia a aritmética **Takum** (variante linear, Definição 8 de Hunhold, 2024) acoplada à Extensão Vetorial RISC-V (**RVV 1.0**) por meio da subextensão experimental **`Zvtakum`**.

## Estrutura de Branches (Entregas)

- **`main` (Fase 1):** Núcleo aritmético Takum em inteiros de 128 bits (`T8`, `T16`, `T32` e acumulação `T64`), modelo de referência em racionais exatos (`Fraction`) e validação contra a `libtakum` v2.0.0.
- **`fase2` (Fase 2):** Simulador funcional `zt-sim` (`RV64IM + Zicsr + RVV 1.0 + Zvtakum`), verificação diferencial contra o `QEMU 10.2.2`, kernels SpMV CSR e modelo analítico inicial.
- **`entrega-final` (Entrega Final Completa):** Diagramas de caminho de dados RISC-V + `Zvtakum` em TikZ sem colisões (EN/PT), comparação estendida com `IEEE FP16/FP32`, `bfloat16`, `OFP8 E4M3/E5M2` (padrão e saturante), pré-escalonamento `pow2-bound`, benchmark de 100 matrizes SuiteSparse com `Posit (es=2)` e `Takum Logarítmico`, script único de execução e plotagem (`scripts/run_all.py`), apresentações em Beamer (`slides/slides.pdf`) e relatórios técnicos finais no formato IEEE Conference de 6 páginas em **Inglês** (`paper/main.pdf`) e **Português** (`paper/main_pt.pdf`).

## Equipe e Contribuições

| Nome | Matrícula | Contribuições principais |
|---|---|---|
| André Luís Alves Rezende | 2018104050 | Especificação da ISA `Zvtakum` (`custom-0`), núcleo Takum C++17 em 128 bits (`src/takum.cpp`), integração no simulador `zt-sim` (`src/machine.cpp`) e pipeline de automação (`scripts/run_all.py`). |
| Gabriel Ramos Fontes | 2022055939 | Oráculo de racionais exatos e formatos binários IEEE/OFP8/bfloat16 (`python/takum_rvv/`), validação contra `libtakum`/`libquadmath` e verificação diferencial com QEMU 10.2.2 (`tests/sim/difftest.py`). |
| Isadora Maria Carvalho Lopes | 2022421544 | Kernels CSR SpMV em assembly RVV/`Zvtakum` (`kernels/spmv.py`), modelo analítico de contagem $N_f = r_f R + c_f S + K$ (`kernels/modelo_contagem.py`) e baselines numéricos (`kernels/numeric_baselines.py`). |
| João Pedro Santos de Brito | 2023038302 | Projeto do caminho de dados RISC-V + `Zvtakum` em TikZ (`paper/figures/datapath_zvtakum*.tex`), geração de gráficos e tabelas (`paper/gera_figuras.py`, `paper/gera_tabelas.py`), artigos IEEE (`paper/main*.tex`) e slides (`slides/slides.tex`). |

## Execução Unificada (Pipeline Completo)

Para executar todos os testes (C++17, Python, QEMU difftest), rodar as 96 simulações SpMV e o modelo analítico, regerar os CSVs numéricos, gráficos vetoriais e tabelas, e recompilar os diagramas TikZ, os dois artigos IEEE (EN e PT) e os slides:

```sh
python3 scripts/run_all.py
# ou via Makefile:
make all-pipeline
```

Comandos individuais por etapa:

```sh
make test        # Núcleo Takum C++ (52 checks) e testes unitários Python (18 testes)
make sim-test    # Simulador Zvtakum contra vetores dourados (21 checks)
make sim-check   # Verificação diferencial byte a byte com QEMU 10.2.2 (9 execuções)
make spmv        # 96 kernels SpMV no zt-sim + modelo analítico + baselines IEEE/OFP8/BF16
make paper-data  # Gera tabelas LaTeX (EN/PT), macros (paper/numeros.tex) e figuras PDF/SVG
make paper       # Compila diagramas TikZ, paper/main.pdf (EN) e paper/main_pt.pdf (PT)
make slides      # Compila slides/slides.pdf (Beamer, 16:9)
```

## Mapa dos Entregáveis

| Entregável | Caminho |
|---|---|
| Núcleo Takum C++17 e testes Fase 1 | `include/takum/`, `src/takum.cpp`, `tests/test_main.cpp` |
| Modelo racional exato e formatos IEEE/OFP8/BF16 | `python/takum_rvv/`, `python/tests/` |
| Simulador `zt-sim` (RV64IM + Zicsr + RVV 1.0 + `Zvtakum`) | `include/zt/`, `src/machine.cpp`, `src/main.cpp`, `tests/sim/` |
| Kernels SpMV, modelo analítico e baselines | `kernels/spmv.py`, `kernels/modelo_contagem.py`, `kernels/numeric_baselines.py` |
| Resultados experimentais e datasets SuiteSparse/fechamento | `results/spmv_hb.csv`, `results/spmv_numerico_hb.csv`, `results/spmv_numerico_scaled_hb.csv`, `results/spmv_row_errors_hb.csv`, `results/suitesparse100_conversion.csv`, `results/closure_takum_linear_log.csv` |
| Diagramas TikZ do Datapath RISC-V + `Zvtakum` (EN e PT) | `paper/figures/datapath_zvtakum.tex` (`.pdf`), `paper/figures/datapath_zvtakum_pt.tex` (`.pdf`) |
| Gráficos vetoriais (EN e PT) | `paper/figures/tapered-precision*.pdf`, `paper/figures/error-cdf*.pdf`, `paper/figures/insn-csr-comparison*.pdf` |
| Artigo IEEE Conference — Inglês (6 páginas) | `paper/main.tex` $\rightarrow$ `paper/main.pdf` |
| Artigo IEEE Conference — Português (6 páginas) | `paper/main_pt.tex` $\rightarrow$ `paper/main_pt.pdf` |
| Bibliografia verificada (23 referências) | `paper/refs.bib` |
| Apresentação Beamer (Português) | `slides/slides.tex` $\rightarrow$ `slides/slides.pdf` |
| Script mestre de execução e geração | `scripts/run_all.py` |
| Documentação técnica e especificação da ISA | `docs/fase1.md`, `docs/arquitetura.md`, `docs/decisoes.md`, `docs/rvv-restructuring.md`, `docs/spec/zvtakum.adoc`, `docs/opcodes/zvtakum.opcodes` |
