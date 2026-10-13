# Fase 1: decodificação e aritmética Takum (T8/T16/T32)

Projeto Integrador de Arquitetura de Computadores (AOC) — UFMG — 2026/02.

Implementação da lógica de conversão (codificação/decodificação) e das
operações aritméticas fundamentais do formato Takum linear, nas larguras
T8, T16 e T32.

## Integrantes

| Nome | Matrícula |
|---|---|
| André Luís Alves Rezende | 2018104050 |
| Gabriel Ramos Fontes | 2022055939 |
| Isadora Maria Carvalho Lopes | 2022421544 |
| João Pedro Gonçalves de Noronha Dutra | `<MATRÍCULA>` |

## Como compilar e testar

Requisitos: `g++` com suporte a C++17 e `python3` 3.10+ (somente a biblioteca
padrão). Não é preciso instalar nada mais.

```sh
make        # compila o binário de testes (build/takum-test)
make test   # roda os testes C++ e os testes Python
make golden # regenera tests/golden/ a partir do modelo Python
make clean  # remove build/
```

`make test` imprime uma linha por grupo de testes C++ e o resumo
(`52 verificações, 0 falhas`, hoje); em seguida roda os 9 testes Python do
modelo de referência e imprime `OK`. Qualquer divergência é mostrada com o
caso que falhou e as contagens, e o comando termina com código de erro.

## O que está implementado

**Item 1 — extração de S, D, R, C e F.** O núcleo em C++
(`include/takum.hpp`, `src/takum.cpp`) tem `zt::decode`, que decodifica o
código no valor exato, e `zt::decode_fields`, que expõe separadamente o bit de
sinal (S), o bit de direção (D), os bits de regime (R), os bits de
característica (C) e os bits de fração (F), inclusive com a janela de 12 bits
e os zeros fantasmas de T8. O modelo Python (`python/takum/codec.py`) oferece
os mesmos campos por `Takum.fields` e o valor exato por `Takum.decode`.

**Item 2 — adição, subtração e multiplicação em T8, T16 e T32.** `zt::add`,
`zt::sub` e `zt::mul` (e `Takum.add/sub/mul` no Python) operam sobre códigos
de 8, 16 ou 32 bits, com arredondamento para o par no código, saturação,
propagação de NaR e tratamento de zero. A verificação C++ é exaustiva em T8
(256×256 pares por operação) e amostrada em T16/T32 contra os vetores
dourados gerados pelo modelo Python em racionais exatos; o modelo, por sua
vez, é conferido contra uma tabela externa da libtakum. Os detalhes do
formato, dos algoritmos e da estratégia de verificação estão em
[`docs/fase1.md`](docs/fase1.md).

## Limitações conhecidas

- Apenas a variante linear do formato está implementada; a variante
  logarítmica não faz parte desta etapa.
- O único modo de arredondamento é para o par no código (RNE), sem modos
  alternativos como truncamento ou arredondamento no valor.
- Não há infinito nem exceções/flags IEEE: o NaR representa os resultados
  inválidos.
- A verificação é exaustiva em T8 e por amostragem em T16/T32, pois o espaço
  completo de pares dessas larguras é inviável de enumerar.

## Onde está cada coisa

| Caminho | Conteúdo |
|---|---|
| `include/` | interface pública do núcleo em C++ (`takum.hpp`) |
| `src/` | implementação do núcleo em C++17 (`takum.cpp`) |
| `tests/` | testes C++, gerador dos vetores e vetores dourados |
| `python/takum/` | modelo de referência em racionais exatos (gabarito) |
| `python/tests/` | testes do modelo e verificação contra a libtakum |
| `docs/` | documentação da Fase 1 (`fase1.md`) |

A Fase 2 (extensão de ISA RISC-V) será entregue na etapa seguinte.

## Licença

Código deste repositório: ISC (ver [`LICENSE`](LICENSE)). A tabela T8 usada
como oráculo externo foi gerada pela libtakum de Laslo Hunhold (ISC); a
proveniência está em `python/tests/test_reference.py` e em `docs/fase1.md`.
