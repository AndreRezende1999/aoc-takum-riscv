# Projeto Integrador AOC — Takum/RISC-V

Este repositório contém a implementação da Fase 1 na `main` e o projeto
completo na branch `fase2`. A `main` permanece deliberadamente limitada ao
núcleo Takum; a `fase2` adiciona o simulador Zvtakum, kernels, resultados,
artigo e slides.

## Equipe e contribuições

| Nome | Matrícula | Contribuições principais |
|---|---|---|
| André Luís Alves Rezende | 2018104050 | `<CONTRIBUIÇÕES>` |
| Gabriel Ramos Fontes | 2022055939 | `<CONTRIBUIÇÕES>` |
| Isadora Maria Carvalho Lopes | 2022421544 | `<CONTRIBUIÇÕES>` |
| João Pedro Gonçalves de Noronha Dutra | `<MATRÍCULA>` | `<CONTRIBUIÇÕES>` |

## Como reproduzir a Fase 2

```sh
make test        # núcleo C++ e modelo Python
make sim-test    # simulador e vetores dourados
make sim-check   # diferencial com QEMU, se as ferramentas existirem
make spmv        # kernels e CSVs de resultados
make paper-data && make paper
make slides
```

## Mapa dos entregáveis

| Entregável | Local |
|---|---|
| Núcleo Takum e testes da Fase 1 | `include/`, `src/`, `tests/`, `python/takum/` |
| Simulador RV64IM/RVV/Zvtakum | `include/zt/`, `src/machine.cpp`, `src/main.cpp` |
| Kernels e resultados | `kernels/`, `results/` |
| Especificação e design | `docs/` |
| Artigo IEEE | `paper/` |
| Slides e roteiro da demo | `slides/` |

Os PDFs são regeneráveis pelos alvos `paper` e `slides`. Dados numéricos não
são alterados pelos geradores.
