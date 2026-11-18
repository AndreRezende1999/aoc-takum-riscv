# Projeto Integrador AOC: Takum na Extensão Vetorial RISC-V (`Zvtakum`)

Este repositório implementa e avalia a aritmética **Takum** (variante linear, Definição 8 de Hunhold, 2024) acoplada à Extensão Vetorial RISC-V (**RVV 1.0**) por meio da subextensão experimental **`Zvtakum`**.

## Estrutura de Branches (Entregas)

- **`main` (Fase 1):** Núcleo aritmético Takum em inteiros de 128 bits (`T8`, `T16`, `T32` e acumulação `T64`), modelo de referência em racionais exatos (`Fraction`) e validação contra a `libtakum` v2.0.0.
- **`fase2` (Fase 2):** Simulador funcional `zt-sim` (`RV64IM + Zicsr + RVV 1.0 + Zvtakum`), verificação diferencial contra o `QEMU 10.2.2`, kernels SpMV CSR e modelo analítico inicial.
- **`entrega-final` (Entrega Final Completa):** Diagramas de caminho de dados RISC-V + `Zvtakum` em TikZ sem colisões (EN/PT), comparação estendida com `IEEE FP16/FP32`, `bfloat16`, `OFP8 E4M3/E5M2` (padrão e saturante), pré-escalonamento `pow2-bound`, benchmark de 100 matrizes SuiteSparse com `Posit (es=2)` e `Takum Logarítmico`, script único de execução e plotagem (`scripts/run_all.py`), apresentações em Beamer (`slides/slides.pdf`) e relatórios técnicos finais no formato IEEE Conference de 6 páginas em **Inglês** (`paper/main.pdf`) e **Português** (`paper/main_pt.pdf`).

- **`revisao-final` (Versão Auditada e Reprodutível):** Integra geração reprodutível em Python do fechamento linear vs.\ logarítmico (`scripts/bench_closure.py`, `LogTakum`), benchmark SuiteSparse-100 em `binary128` com manifesto SHA-256 (`scripts/bench_suitesparse100.py`, `results/suitesparse100_manifest.json`), baselines em `Posit(es=2)` no SpMV (`python/takum_rvv/posit.py`), evidências da `libtakum`/`libquadmath` (`docs/evidencias/`), checagem de limite de páginas e auditoria bibliográfica (`tools/check_references.py`, `references/audit.csv`), e script unificado `./run_all.sh [--strict] [--full]`.

## Equipe e Registro de Contribuições

| Nome | Matrícula | Registro no projeto |
|---|---|---|
| André Luís Alves Rezende | 2018104050 | Integrante da equipe (autor do único usuário com commits registrados no histórico Git) |
| Gabriel Ramos Fontes | 2022055939 | Integrante da equipe |
| Isadora Maria Carvalho Lopes | 2022421544 | Integrante da equipe |
| João Pedro Santos de Brito | 2023038302 | Integrante da equipe |

> **Nota sobre rastreabilidade no Git:** o histórico de commits do repositório encontra-se registrado sob um único usuário (`AndreRezende1999`), não permitindo corroborar a divisão individual de autoria pelo `git log`. Recomenda-se que cada integrante registre suas contribuições em commits próprios para documentar a participação individual no desenvolvimento.

## Execução Unificada e Comandos Principais

Para validar testes, reproduzir artefatos e verificar invariantes da entrega em um único fluxo:

```sh
./run_all.sh              # Compila C++, executa testes C++/Python/QEMU, paper-data, PDFs e slides
./run_all.sh --strict     # Falha se PDF > 6 páginas, refs/audit.csv divergir ou houver testes ignorados
./run_all.sh demo         # Execução rápida para demonstração ao vivo (81 C++ checks + exemplo T8 vs IEEE)
python3 scripts/run_all.py
```

Comandos individuais por etapa:

```sh
make test        # Núcleo Takum C++ (takum-test: 52 checagens) + testes unitários Python (75 testes)
make sim-test    # Simulador Zvtakum contra vetores dourados e testes ISA/CSR (zt-test: 29 checagens; total 81 C++)
make sim-check   # Verificação diferencial byte a byte com QEMU 10.2.2 (9 execuções; registra versões QEMU/LLVM)
make spmv        # 96 kernels SpMV no zt-sim + modelo analítico + baselines IEEE/OFP8/BF16/Posit
make paper-data  # Gera tabelas LaTeX (EN/PT), macros (paper/numeros.tex) e figuras PDF/SVG
make paper       # Compila diagramas TikZ, paper/main.pdf (EN, <=6 pág.) e paper/main_pt.pdf (PT, <=6 pág.)
make slides      # Compila slides/slides.pdf (Beamer, 16:9, 14 slides) e ver slides/roteiro.md
python3 tools/check_references.py   # Audita todas as 25 chaves de paper/refs.bib contra references/audit.csv
python3 tools/make_manifest.py      # Emite artifacts/manifest.json e artifacts/skipped.txt
```

> **Explicação da contagem de testes C++ (`52 + 29 = 81`):** `takum-test` executa `52` checagens do núcleo escalar/codec (`tests/test_main.cpp`), enquanto `zt-test` executa `29` checagens do simulador vetorial (`tests/sim/test_main.cpp`, expandidas de 21 para 29 ao incluir amostragem `T32`, ida-e-volta `T32`, propriedades algébricas `T8/T16`, instrução `custom-0` ilegal e verificação arquitetural de reset `vtype.vill=1`). Total: `81` checagens C++ + `75` testes Python em `python/tests/`.

## Mapa dos Entregáveis

| Entregável | Caminho |
|---|---|
| Núcleo Takum C++17 e testes Fase 1 | `include/takum/`, `src/takum.cpp`, `tests/test_main.cpp` |
| Modelo racional exato e formatos IEEE/OFP8/BF16 | `python/takum_rvv/`, `python/tests/` |
| Simulador `zt-sim` (RV64IM + Zicsr + RVV 1.0 + `Zvtakum`) | `include/zt/`, `src/machine.cpp`, `src/main.cpp`, `tests/sim/` |
| Kernels SpMV, modelo analítico e baselines | `kernels/spmv.py`, `kernels/modelo_contagem.py`, `kernels/numeric_baselines.py` |
| Resultados experimentais e datasets SuiteSparse/fechamento | `results/spmv_hb.csv`, `results/spmv_numerico_hb.csv`, `results/spmv_numerico_scaled_hb.csv`, `results/spmv_row_errors_hb.csv`, `results/suitesparse100_conversion.csv`, `results/suitesparse100_manifest.json`, `results/closure_takum_linear_log.csv` |
| Diagramas TikZ do Datapath RISC-V + `Zvtakum` (EN e PT) | `paper/figures/zvtakum-datapath*.tex` (`.pdf`), `paper/figures/datapath_zvtakum*.tex` (`.pdf`) |
| Gráficos vetoriais (EN e PT) | `paper/figures/tapered-precision*.pdf`, `paper/figures/error-cdf*.pdf`, `paper/figures/insn-csr-comparison*.pdf` |
| Artigo IEEE Conference em Inglês (6 páginas) | `paper/main.tex` $\rightarrow$ `paper/main.pdf` |
| Artigo IEEE Conference em Português (6 páginas) | `paper/main_pt.tex` $\rightarrow$ `paper/main_pt.pdf` |
| Bibliografia verificada (25 referências) | `paper/refs.bib`, `references/audit.csv` |
| Apresentação Beamer (Português) | `slides/slides.tex` $\rightarrow$ `slides/slides.pdf` |
| Script mestre, evidências e auditoria | `run_all.sh`, `scripts/run_all.py`, `scripts/bench_closure.py`, `scripts/bench_suitesparse100.py`, `tools/check_references.py`, `tools/make_manifest.py`, `references/audit.csv`, `docs/evidencias/` |
| Documentação técnica e especificação da ISA | `docs/fase1.md`, `docs/arquitetura.md`, `docs/decisoes.md`, `docs/design.md`, `docs/rvv-restructuring.md`, `docs/spec/zvtakum.adoc`, `docs/opcodes/zvtakum.opcodes` |
