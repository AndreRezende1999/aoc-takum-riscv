# Projeto Integrador AOC: Takum na Extensão Vetorial RISC-V (`Zvtakum`)

Este repositório implementa e avalia a aritmética **Takum** (variante linear, Definição 8 de Hunhold, 2024) acoplada à Extensão Vetorial RISC-V (**RVV 1.0**) por meio da subextensão experimental **`Zvtakum`**.

## Estrutura de Branches

- **`main` (Código, Testes, Benchmarks e Geração de Figuras):** Núcleo aritmético Takum em inteiros de 128 bits (`T8`, `T16`, `T32` e acumulação `T64`), modelo de referência em racionais exatos (`Fraction`), simulador funcional `zt-sim` (`RV64IM + Zicsr + RVV 1.0 + Zvtakum`), verificação diferencial contra `QEMU 10.2.2`, kernels SpMV CSR, baselines numéricos (`IEEE FP16/FP32`, `bfloat16`, `OFP8 E4M3/E5M2`, `Posit (es=2)`, `Takum Logarítmico`), benchmark SuiteSparse-100 e scripts de geração de gráficos e diagramas (`paper/gera_figuras.py` e `paper/figures/`).
- **`docs` (Artigos IEEE e Slides Beamer):** Contém adicionalmente os relatórios técnicos finais no formato IEEE Conference de 6 páginas em **Inglês** (`paper/main.pdf`) e **Português** (`paper/main_pt.pdf`), a apresentação em Beamer (`slides/slides.pdf`) e o roteiro de apresentação (`slides/roteiro.md`).

## Equipe

| Nome | Matrícula |
|---|---|
| André Luís Alves Rezende | 2018104050 |
| Gabriel Ramos Fontes | 2022055939 |
| Isadora Maria Carvalho Lopes | 2022421544 |
| João Pedro Santos de Brito | 2023038302 |

## Execução Unificada e Comandos Principais

Para validar testes, reproduzir benchmarks e gerar as figuras da entrega em um único fluxo:

```sh
./run_all.sh              # Compila C++, executa testes C++/Python/QEMU, baselines e gera figuras
./run_all.sh --strict     # Falha se alguma dependência/teste falhar ou houver etapas ignoradas
./run_all.sh demo         # Execução rápida para demonstração ao vivo (81 C++ checks + exemplo T8 vs IEEE)
python3 scripts/run_all.py
```

Comandos individuais por etapa:

```sh
make test        # Núcleo Takum C++ (takum-test: 52 checagens) + testes unitários Python (75 testes)
make sim-test    # Simulador Zvtakum contra vetores dourados e testes ISA/CSR (zt-test: 29 checagens; total 81 C++)
make sim-check   # Verificação diferencial byte a byte com QEMU 10.2.2 (9 execuções; registra versões QEMU/LLVM)
make spmv        # 96 kernels SpMV no zt-sim + modelo analítico + baselines IEEE/OFP8/BF16/Posit
make figures     # Gera gráficos vetoriais PDF/SVG (paper/gera_figuras.py) e compila diagramas TikZ
python3 tools/check_references.py   # Audita as 25 entradas bibliográficas em references/audit.csv
python3 tools/make_manifest.py      # Emite artifacts/manifest.json e artifacts/skipped.txt
```

> **Explicação da contagem de testes C++ (`52 + 29 = 81`):** `takum-test` executa `52` checagens do núcleo escalar/codec (`tests/test_main.cpp`), enquanto `zt-test` executa `29` checagens do simulador vetorial (`tests/sim/test_main.cpp`, incluindo amostragem `T32`, ida-e-volta `T32`, propriedades algébricas `T8/T16`, instrução `custom-0` ilegal e verificação arquitetural de reset `vtype.vill=1`). Total: `81` checagens C++ + `75` testes Python em `python/tests/`.

## Mapa dos Entregáveis

| Entregável | Caminho |
|---|---|
| Núcleo Takum C++17 e testes Fase 1 | `include/takum/`, `src/takum.cpp`, `tests/test_main.cpp` |
| Modelo racional exato e formatos IEEE/OFP8/BF16/Posit | `python/takum_rvv/`, `python/tests/` |
| Simulador `zt-sim` (RV64IM + Zicsr + RVV 1.0 + `Zvtakum`) | `include/zt/`, `src/machine.cpp`, `src/main.cpp`, `tests/sim/` |
| Kernels SpMV, modelo analítico e baselines | `kernels/spmv.py`, `kernels/modelo_contagem.py`, `kernels/numeric_baselines.py` |
| Resultados experimentais e datasets SuiteSparse/fechamento | `results/spmv_hb.csv`, `results/spmv_numerico_hb.csv`, `results/spmv_numerico_scaled_hb.csv`, `results/spmv_row_errors_hb.csv`, `results/suitesparse100_conversion.csv`, `results/suitesparse100_manifest.json`, `results/closure_takum_linear_log.csv` |
| Geração de figuras e diagramas TikZ (EN e PT) | `paper/gera_figuras.py`, `paper/figures/` |
| Script mestre, evidências e auditoria | `run_all.sh`, `scripts/run_all.py`, `scripts/bench_closure.py`, `scripts/bench_suitesparse100.py`, `tools/check_references.py`, `tools/make_manifest.py`, `references/audit.csv`, `docs/evidencias/` |
| Documentação técnica e especificação da ISA | `docs/fase1.md`, `docs/arquitetura.md`, `docs/decisoes.md`, `docs/design.md`, `docs/rvv-restructuring.md`, `docs/spec/zvtakum.adoc`, `docs/opcodes/zvtakum.opcodes` |
| Artigos IEEE (EN/PT) e Apresentação Beamer | Branch `docs` (`https://github.com/AndreRezende1999/aoc-takum-riscv/tree/docs`) |
