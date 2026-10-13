# Fase 1 — decodificação e aritmética Takum (T8/T16/T32)

Este documento descreve o que este repositório implementa, como o código
extrai os campos do formato, quais são os algoritmos de adição, subtração e
multiplicação, a regra de arredondamento adotada e como tudo é verificado.
Ele cobre os itens 1 e 2 da Fase 1 do enunciado.

## 1. Formato Takum linear

Um código Takum de `n` bits (`n = 8, 16` ou `32` nesta etapa) é lido como:

| Campo | Bits | Significado |
|---|---|---|
| **S** | 1 | sinal (0 positivo, 1 negativo) |
| **D** | 1 | direção (0 abaixo de 1, 1 acima de 1) |
| **R** | 3 | regime, como lido no código |
| **C** | `r` | característica |
| **F** | `p` | fração |

O regime efetivo é `r = R` quando `D = 1` e `r = 7 - R` quando `D = 0`;
a largura da fração é `p = n - 5 - r`. A característica é
`c = 2^r - 1 + C` (para `D = 1`) ou `c = -2^(r+1) + 1 + C` (para `D = 0`).
O valor representado é

```
v = (-1)^S * (1 - 3S + F/2^p) * 2^((-1)^S * (c + S))
```

que é a variante linear da Def. 8 de Hunhold (arXiv:2404.18603v2). Não há
infinito. O código todo em zero é o zero; o código `1000...0` (bit mais alto
em 1) é o **NaR** (*Not a Real*), o valor ausente. A negação é o complemento
de dois do código.

**Janela de 12 bits (`n < 12`).** Para T8, a leitura usa uma janela de 12 bits:
o código é deslocado à esquerda e recebe zeros fantasmas à direita
(`raw = code << (12 - 8)`), de modo que S, D, R, C e F caiam nas mesmas
posições relativas de T16/T32. É essa janela que fixa a faixa de T8 em
`[2^-239, 2^239]` (com `r = 7` e `p = 0`, a assimetria da característica
limita o expoente), bem menor que o domínio nominal do formato.

## 2. Extração dos campos (S, D, R, C, F)

No núcleo em C++ (`include/takum.hpp`, `src/takum.cpp`):

- `zt::decode_fields(n, code)` devolve S, D, R e o regime efetivo, C, a
  característica combinada `c`, os bits crus de F e a largura `p` (a fração é
  `F / 2^p`). Vale para qualquer código, inclusive zero e NaR: a função lê os
  bits como estão e não decide casos especiais.
- `zt::decode(n, code)` resolve os casos especiais (zero e NaR) e devolve o
  valor exato: `(-1)^neg * sig * 2^(e-63)`, com o bit 63 de `sig` igual a 1
  (significando normalizado). O valor é exato; `sig` e `e` são inteiros.
- As duas funções compartilham a mesma rotina interna de leitura
  (`parse_fields`), de modo que só existe uma interpretação dos campos no
  código-fonte.

No modelo Python (`python/takum/codec.py`):

- `Takum(bits).fields(raw)` devolve um `Fields` com `sign`, `direction`,
  `regime`, `characteristic_bits` (C), `characteristic` (c) e `fraction`
  (F como `Fraction`), além de `fraction_width` (p).
- `Takum(bits).decode(raw)` devolve o valor como `Fraction` exata, `Fraction(0)`
  para o zero e `None` para o NaR.

## 3. Codificação: RNE, saturação, NaR e zero

`zt::encode` (e `Takum.encode` no Python) recebe um valor exato e devolve o
código de `n` bits:

1. **Zero e NaR** têm códigos fixos (`0` e `1000...0`).
2. **Arredondamento para o par no código (RNE).** A codificação monta a
   "cadeia infinita" do código da magnitude: o cabeçalho (D, R e C) seguido
   dos bits de fração do significando. Toma o prefixo de `n + 1` bits — os
   `n` bits que serão o código (`L`) mais um bit de meio-ponto (`m`) — e
   marca com *sticky* qualquer bit não nulo descartado além do prefixo, além
   do *sticky* que as operações já vinham acumulando. O resultado é `L`; se
   `m = 1` e (sticky ativo ou `L` ímpar), sobe para `L + 1`. Esse é o
   arredondamento para o par **no código**, não no valor (ver a decisão 7.1).
3. **Saturação.** Depois do arredondamento, o resultado é limitado ao
   intervalo `[1, maxpos]`, com `maxpos = 2^(n-1) - 1` (o NaR menos um):
   valores acima do máximo viram `maxpos`; valores positivos menores que o
   mínimo viram o menor positivo; resultados exatamente zero viram o código do
   zero. Não há infinito.
4. **Negativos.** O código é o complemento de dois do código da magnitude.

## 4. Algoritmos de adição, subtração e multiplicação

Toda a aritmética é feita em inteiros (`uint64_t` e `unsigned __int128`), sem
`double`, para que o resultado não dependa do ambiente.

**Adição (`zt::add`).** Depois de tratar NaR (vence qualquer operação) e zero
(elemento neutro), os dois valores são alinhados pelo maior expoente: o menor
é deslocado para a direita e os bits descartados viram *sticky*. Os
significandos são somados (mesmo sinal) ou subtraídos com o *sticky* como
*borrow* (sinais opostos). O resultado é normalizado (deslocamento à esquerda,
ou à direita com acúmulo de *sticky*) e codificado uma única vez, já
arredondando e saturando.

**Subtração (`zt::sub`).** É a adição com o segundo operando negado pelo
complemento de dois do código, o que preserva a semântica dos casos especiais.

**Multiplicação (`zt::mul`).** Depois de NaR (vence) e zero (absorve), os
significandos são multiplicados em 128 bits; o produto é normalizado e o
*sticky* recebe os bits descartados. O expoente é a soma dos expoentes mais o
ajuste da normalização, e a codificação arredonda uma única vez, com esse
*sticky*.

## 5. Estratégia de verificação

O gabarito é o **modelo Python em racionais exatos**: ele é independente do
C++ e gera os vetores dourados commitados em `tests/golden/` (semente fixa
2026, alvo `make golden`). Os testes automáticos são:

- **T8 exaustivo:** as três operações para todos os 65 536 pares de códigos,
  contra tabelas de 256×256 bytes (`tests/golden/t8_{add,sub,mul}.bin`).
- **T16 e T32 amostrados:** 4 000 pares por operação e largura (24 000 casos
  no total, `tests/golden/takum_ops_sampled.txt`), misturando códigos
  aleatórios e valores de magnitude moderada, que exercitam as fronteiras de
  regime.
- **Ida e volta:** `decode` seguido de `encode` reproduz o código original para
  todo o T8 e todo o T16, e para 200 000 códigos T32 amostrados.
- **Casos dirigidos:** campos S/D/R/C/F de códigos conhecidos; empates para
  par (inclusive na fronteira em que a característica de T8 é truncada);
  saturação nos três tamanhos; zero e NaR nas operações.
- **Oráculo externo:** o modelo Python é conferido, em todo o T8
  (decodificação e as três operações), contra uma tabela gerada pela versão
  pinada da libtakum de Laslo Hunhold, e contra os limites de exatidão de
  inteiros publicados por Hunhold (arXiv:2412.20273v2, seção 5).

Tudo roda com `make test`, sem rede e sem nenhuma dependência além de `g++` e
`python3` (biblioteca padrão).

## 6. Arquivos e o que cada um cobre

- `include/takum.hpp` — interface do núcleo (item 1 e item 2);
- `src/takum.cpp` — implementação (decodificação, codificação e ALU);
- `tests/test_main.cpp` — testes do núcleo citados na seção 5;
- `tests/gen_golden.py` — regeneração dos vetores a partir do modelo Python;
- `python/takum/codec.py` — modelo de referência em racionais exatos;
- `python/tests/` — testes do modelo e a verificação contra a libtakum.

## 7. Decisões de projeto e alternativas

### 7.1 Arredondamento normativo: RNE no código

Adotado o arredondamento para o par **no código**, com prefixo de `n + 1` bits
e *sticky*, sem `double` (decisão D6 do registro de decisões do projeto
original). A alternativa considerada — arredondar no valor (vizinho mais
próximo) — foi descartada porque difere do comportamento do modelo de
referência e da libtakum nas regiões de característica truncada. Exemplo real
em T8: `2^-231` é o ponto médio (no domínio do código, isto é, geométrico)
entre `2^-239` (código 1) e `2^-223` (código 2); o RNE escolhe o código par 2
(`2^-223`), enquanto o vizinho mais próximo em valor seria `2^-239`. O
empate para par no código segue Hunhold, arXiv:2408.10594v4, seção 5.5.

### 7.2 Apenas T8, T16 e T32; variante linear

O escopo da Fase 1 são as larguras 8, 16 e 32 e a variante **linear** do
formato (decisão D5 do projeto original). A variante logarítmica exige a
implementação de `Δ±` para soma e subtração e fica fora desta etapa.

### 7.3 Modelo Python como gabarito bit a bit

O modelo em racionais exatos (decisão D3 do projeto original) é a referência
dos vetores dourados e a segunda implementação independente do núcleo em C++.
A comparação entre dois caminhos independentes (bits inteiros em C++ e
frações exatas em Python) é o principal argumento de correção desta etapa.

### 7.4 C++17 sem dependências, aritmética em inteiros

O núcleo é C++17 puro com `-Wall -Wextra -Werror` (decisão D2 do projeto
original). O uso de `__int128` evita o `double` do host, que é a causa
conhecida de divergências de dupla arredondagem registradas no projeto
original.

### 7.5 Remoção das funções de Fase 2 do núcleo

O núcleo original também continha `narrow` (T32/T16→T16/T8) e `dot_step` (um
passo do `vtdot`), usadas apenas pelo simulador de máquina, que pertence à
Fase 2 e não está neste repositório. Como nenhuma outra função dependia delas,
foram removidas junto com os vetores dourados correspondentes
(`t16_to_t8.bin` e `takum_dot_sampled.txt`), para não publicar uma interface
que não faz parte da Fase 1. No modelo Python, o método equivalente
`Takum.convert` também foi removido; o alargamento exato T8→T16 continua
verificado via `decode` (código deslocado).

### 7.6 Oráculo externo commitado

A tabela T8 da libtakum (21 KB comprimidos) é commitada em vez de depender da
biblioteca em tempo de teste: `make test` não precisa de rede, compilador C
externo nem instalação. A proveniência — revisão `776ac0ca...` (v2.0.0,
licença ISC), formato do arquivo e SHA-256 — está documentada no topo de
`python/tests/test_reference.py`. A tabela não é usada para gerar os vetores
dourados (isso é feito só pelo modelo Python); ela é evidência adicional de
que o gabarito concorda com uma implementação independente publicada.

## 8. Referências

- L. Hunhold, *Beating Posits at Their Own Game: Takum Arithmetic*, 2024.
  arXiv:2404.18603v2. (Definição 8, variante linear; usada no formato.)
- L. Hunhold, *Streamlining SIMD ISA extensions with Takum arithmetic: a case
  study on Intel AVX10.2*, MOCAST 2025. arXiv:2503.14067. (Motivação do
  projeto.)
