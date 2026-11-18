# Roteiro Completo da Apresentação, Explicação de Conceitos e Storytelling (15 min)

Este documento guia a apresentação oral de **15 minutos** de [`slides/slides.pdf`](slides.pdf) (14 slides: 1 capa + 13 slides numerados), estruturada sobre os requisitos do edital (`ProjectGuidelinesAOC.pdf`, Seções 2, 3, 4.1, 5.1, 5.2, 5.3 e 6.3).

---

## 1. O Arco de Storytelling (Fio Condutor da Apresentação)

Para conduzir a banca com clareza do problema à validação experimental, a apresentação segue uma narrativa de engenharia em **5 atos**:

1. **O Conflito (Slides 1 e 2):** Aplicações modernas de IA e álgebra linear esparsa são limitadas por banda de memória, exigindo formatos compactos de 8 e 16 bits. A indústria criou vários formatos IEEE parciais (`FP16`, `bfloat16`, `OFP8 E4M3/E5M2`). Na extensão vetorial do RISC-V (`RVV 1.0`), isso resulta em **96 instruções** de ponto flutuante e conversão, exige tratamento de subnormais e acopla o pipeline ao registrador `fcsr` (`frm`/`fflags`), enquanto o `FP8` sequer existe no padrão.
2. **A Ideia Matemática e o Hardware da Fase 1 (Slides 3 e 4):** A aritmética **Takum** concentra mais bits de mantissa perto de $1.0$ (*tapered precision*), alcança faixa dinâmica ampla ($\approx 10^{\pm 72}$ em `T8` e $10^{\pm 77}$ em `T16/T32`) e empacota o cabeçalho de escala $(S, D, R, C)$ nos **12 bits mais significativos (12 MSBs)** para *qualquer* largura (`T8`, `T16`, `T32`). Construímos uma ULA em **inteiros de 128 bits** com arredondamento **RNE no espaço de códigos**, evitando `double` do hospedeiro: em 30.000 amostras `T32` (10.000 por operação), encontramos **128/10.000 multiplicações** onde a `libtakum` oficial diverge por 1 ULP devido ao duplo arredondamento via `double`.
3. **A Arquitetura `Zvtakum` e as Decisões de Projeto da Fase 2 (Slides 5 a 7):** Em vez de 96 instruções, adotamos **5 instruções vetoriais** (`vtadd.vv`, `vtsub.vv`, `vtmul.vv`, `vtdot.vv`, `vncvt.t.t`) parametrizadas por `vtype.vsew` no espaço **`custom-0` (`0x0B`)**. Integramos o subsistema vetorial ao datapath RISC-V sem dependência de `fcsr` e registramos 6 eixos de alternativas e justificativas técnicas (Seção 4.1 do edital).
4. **Avaliação Experimental e Limitações da Fase 3 (Slides 8 a 12):** Validamos o simulador `zt-sim` com **81 checagens C++** (52 em `takum-test` + 29 em `zt-test`), **75 testes Python**, confronto com `libtakum` e `Float128` (`6.017` casos), e teste diferencial byte a byte contra o **QEMU 10.2.2**. Na multiplicação matriz esparsa-vetor (**SpMV CSR**, $y = A \cdot x$):
   - Em **32 bits**, `Takum32` reduz o erro mediano em **$5.15\times$** frente ao `FP32` ($2.01\times$ do formato e $2.56\times$ do acumulador `T64` do `vtdot.vv`), vencendo `FP32` em 7/8 matrizes e vencendo `Posit(32,2)` em `bcsstk01` e `pores_1` (enquanto `Posit32` vence em 6/8 matrizes moderadas).
   - Em **8 e 16 bits**, enquanto `E4M3` falha em **4/8** matrizes e `E5M2`/`FP16` falham em **3/8**, `Takum8`, `Takum16`, `Posit8/16` e `bfloat16` mantêm **0/8 falhas finitas**; `Takum16` supera `bfloat16` em $3.17\times$ a $7.61\times$, embora `Posit(8,2)` supere `Takum8` em 7/8 matrizes sem escala e 8/8 com escala por concentrar mais bits de mantissa perto de $1$. No SuiteSparse-100, `Takum16` evita a degradação de cauda do `Posit16`.
   - Na **contagem de instruções**, o modelo analítico $N_f = r_f R + c_f S + K$ fecha as 96 execuções com **resíduo máximo zero**, e a relação $N_{\text{Takum32}} - N_{\text{FP32}} = R - S \le 0$ mostra que `Takum32` nunca executa mais instruções que `FP32` no kernel analisado. No Slide 12 apresentamos explicitamente as limitações e ameaças à validade.
5. **Conclusão e Demonstração ao Vivo (Slides 13 e 14):** Fechamos com a síntese das entregas e rodamos no terminal a suíte completa, o teste diferencial e o kernel `bcsstk01` em tempo real ($1353 - 1365 = R - S = 48 - 60 = -12$).

---

## 2. Divisão de Tempo Sugerida para 4 Integrantes (15 Minutos)

| Integrante | Slides | Tempo | Escopo Principal |
|---|---|---|---|
| **Apresentador 1 (André)** | Slides 1, 2 e 3 | `00:00 - 03:15` (3,25 min) | Abertura, problema da proliferação IEEE na RVV, objetivos do projeto e Fase 1A (codificação Takum Def. 8 e janela de 12 MSBs). |
| **Apresentador 2 (Gabriel)** | Slides 4, 5 e 6 | `03:15 - 06:30` (3,25 min) | Fase 1B (ULA inteira de 128 bits, RNE no código, 128/10.000 divergências na `libtakum`) e Fase 2 (5 instruções `Zvtakum` em `custom-0` e datapath RISC-V + `Zvtakum`). |
| **Apresentador 3 (João Pedro)** | Slides 7, 8 e 9 | `06:30 - 09:45` (3,25 min) | 6 decisões de projeto e justificativas (Seção 4.1 do edital); verificação em 4 camadas (`QEMU`/`Float128`); kernel SpMV CSR e resultados em 32 bits (incluindo `Posit(32,2)`). |
| **Apresentador 4 (Isadora)** | Slides 10, 11, 12, 13 e 14 + Demo | `09:45 - 15:00` (5,25 min: 3 min slides + 2,25 min demo) | Resultados em 8/16 bits (`Posit`, *overflows*, SuiteSparse-100), modelo analítico $N_f = r_f R + c_f S + K$, limitações, conclusão e **Demo ao vivo no terminal**. |

---

## 3. Roteiro Detalhado Slide a Slide (Conceitos + Fala + Dicas Visuais)

---

### SLIDE 1 — Capa (`00:00 – 00:25`)
- **Fala sugerida:**
  > *"Bom dia/boa tarde professor e colegas. Nós somos o grupo formado por André, Gabriel, Isadora e João Pedro, e vamos apresentar o nosso Projeto Integrador de AOC: a implementação e avaliação do formato aritmético Takum na Extensão Vetorial RISC-V, que batizamos de subextensão `Zvtakum`."*

---

### SLIDE 2 — 1. Motivação, Problema e Objetivos do Projeto (`00:25 – 01:45`)
- **Conceito técnico chave (para dominar):**
  - Na norma IEEE 754, os bits de expoente e mantissa são fixos. Para caber em 16 ou 8 bits, ou você sacrifica alcance dinâmico (`FP16` só vai até $\approx 6.5 \times 10^4$ e estoura fácil), ou sacrifica precisão (`bfloat16` tem só 7 bits de fração). Em 8 bits foi ainda pior: a indústria precisou criar dois formatos incompatíveis (`OFP8 E4M3` para pesos/ativações e `E5M2` para gradientes).
  - Quando olhamos para o catálogo oficial de opcodes da extensão vetorial RISC-V (`riscv-opcodes`), já existem **92 instruções vetoriais de ponto flutuante** mais **4 de `bfloat16`** (`Zvfbfmin`/`Zvfbfwma`), sendo **25 apenas para converter um formato em outro** — e o `FP8` sequer existe no padrão RVV 1.0!
- **Onde apontar:** Coluna da esquerda (os números `10^±5`, `96 instruções`, `fcsr`) e depois coluna da direita (os 4 objetivos mapeados às Fases 1, 2 e 3 do edital).
- **Fala sugerida:**
  > *"Qual é a dor arquitetural que motiva este trabalho? Cargas modernas de IA e álgebra linear esparsa são limitadas por banda de memória. Para carregar mais elementos por registrador vetorial, surgiram vários formatos IEEE de 8 e 16 bits: `FP16`, `bfloat16`, `E4M3` e `E5M2`. Só que essa proliferação cobra um preço caro na ISA e no hardware: na RVV 1.0, o `FP8` nem existe, e somando `FP` padrão com `bfloat16` já são 96 instruções vetoriais — 25 delas só de conversão cruzada — além da lógica de subnormais e do gargalo de sincronizar o registrador `fcsr` a cada ciclo.*
  > *Seguindo a metodologia que Hunhold propôs para o Intel AVX10.2 em 2025, nosso objetivo foi responder: e se substituirmos essa fragmentação na RVV pelo formato Takum? Ao parametrizar a largura pelo CSR `vtype.vsew`, aquelas 96 instruções colapsam em apenas 8 primitivas aritméticas. Dividimos o projeto nas três fases do edital: Fase 1 (decodificador de 12 MSBs e ULA Takum), Fase 2 (extensão ISA `Zvtakum` e datapath RISC-V) e Fase 3 (simulador funcional e avaliação em SpMV contra `Float128`)."*

---

### SLIDE 3 — 2. Fase 1: Codificação Takum Linear (Def. 8) e Janela de 12 MSBs (`01:45 – 03:30`)
- **Conceito técnico chave (para dominar):**
  - Uma palavra Takum de $n$ bits tem 5 campos: Sinal $S$ (1 bit), Direção $D$ (1 bit), Regime $R$ (3 bits), Característica $C$ ($r$ bits) e Fração $F$ ($p = n - 5 - r$ bits).
  - Por que o decodificador olha **no máximo 12 bits**? Porque $R$ tem 3 bits, logo $r \in \{0, \dots, 7\}$. Somando $1 (S) + 1 (D) + 3 (R) + 7 (C_{\max}) = 12\text{ bits}$!
  - E se a palavra tiver menos de 12 bits, como o `T8` ($n=8$)? Basta deslocar 4 bits à esquerda preenchendo 4 *ghost bits* (zeros fantasmas) à direita: o mesmo circuito de 12 bits decodifica `T8`, `T16` e `T32`!
  - Diferença crucial para o **Posit**: o Posit usa código unário para o regime (precisa de um detector de zeros líderes na palavra inteira de 32 bits). Na região central focada pela escala `symlog` ($|\log_{10}|x||\le 5$), `Takum` e `Posit(n,2)` empatam com $n-4$ bits em $|x|\in[0{,}5,2)$, mas entre $0{,}3$ e $4{,}8$ décadas o prefixo unário curto do `Posit` preserva 1 a 2 bits extras (o que explica seu ganho em matrizes moderadas de 8 e 16 bits); fora dessa faixa, o Posit decai rapidamente enquanto o Takum limita o cabeçalho a 12 bits, mantendo pisos de 5 bits (`T16`) e 21 bits (`T32`) até $\approx 10^{\pm 77}$.
- **Onde apontar:** Primeiro na faixa central `[-5, 5]` (escala `symlog`) dos 3 gráficos `(a) 8 bits`, `(b) 16 bits` e `(c) 32 bits` (mostrando onde `E4M3`/`E5M2`/`FP16` terminam, os degraus do `Posit` acima do `Takum` entre $0{,}3$ e $4{,}8$, e depois o cruzamento nas caudas até $\pm 77$).
- **Fala sugerida:**
  > *"Entrando na Fase 1: como funciona a codificação Takum Linear da Definição 8? Cada número tem 5 campos: sinal $S$, direção $D$, regime $R$ de 3 bits fixos, característica $C$ de $r$ bits e fração $F$. Como $R$ tem 3 bits, $r$ varia de 0 a 7, limitando todo o prefixo de escala $(S, D, R, C)$ aos 12 bits mais significativos em qualquer largura. Para `T8`, completamos 4 zeros fantasmas à direita com a mesma fiação decodificadora.*
  > *Olhando para o gráfico em escala `symlog` focada no centro ($|\log_{10}|x||\le 5$), vemos o compromisso estrutural entre os formatos: perto da unidade ambos empatam em $n-4$ bits, mas entre $0{,}3$ e $4{,}8$ décadas de distância de 1 o `Posit(n,2)` preserva 1 a 2 bits extras de fração porque seu regime unário ainda é curto, enquanto o `Takum` já aloca bits para ampliar a característica `C`. Por outro lado, fora dessa banda central o `E4M3` e o `FP16` cessam em $\pm 2{,}6$ e $\pm 4{,}8$, e o `Posit` despenca, enquanto o `Takum16` e o `Takum32` mantêm pisos de 5 e 21 bits até $10^{\pm 77}$."*

---

### SLIDE 4 (Item 3): Fase 1 — ULA Takum em Inteiros de 128 Bits e RNE no Código (`03:15 - 04:20`)
- **Conceito técnico chave (para dominar):**
  - Na Fase 1, evitar `double` do C++ evita casos de duplo arredondamento em `T32` (e no acumulador `T64`): converter para `double` (53 bits) arredonda uma primeira vez, e codificar para Takum arredonda uma segunda vez.
  - Nossa ULA em `src/takum.cpp` desempacota qualquer Takum na tupla exata $(-1)^{\mathrm{neg}} \cdot \mathrm{sig} \cdot 2^{e-63}$ usando inteiros de 64 e 128 bits (`unsigned __int128`).
  - O arredondamento Takum é **RNE no espaço de códigos**: montamos a cadeia infinita de bits $(D, R, C, F)$, olhamos o prefixo de $n$ bits ($L$), o bit $n+1$ ($m$, meio-ponto) e o *OR* de todos os bits seguintes ($st$, *sticky*). Somamos $1$ ao código $L$ se e só se $m=1$ e $(st=1 \text{ ou } L \text{ é ímpar})$.
- **Onde apontar:** Nos três blocos do slide: tupla em `__int128`, regra booleana $L \to L+1$, e o destaque das **128/10.000 divergências em multiplicação `T32`** contra a `libtakum`.
- **Fala sugerida:**
  > *"Para implementar as operações aritméticas fundamentais da Fase 1 (adição, subtração, multiplicação, passo de produto escalar e estreitamento), projetamos uma ULA em C++17 operando com inteiros de 64 e 128 bits (`__int128`), sem utilizar `double` do hospedeiro.*
  > *Cada operando vira uma tupla exata $(\mathrm{neg}, e, \mathrm{sig})$. Na soma e subtração, alinhamos os significandos em 128 bits preservando o bit *sticky*, que também atua como *borrow* na subtração efetiva; na multiplicação, calculamos o produto inteiro exato de 128 bits.*
  > *Na saída, aplicamos RNE diretamente no espaço de códigos, como especifica o codec VHDL de Hunhold: extraímos o prefixo $L$ de $n$ bits, o bit $n+1$ de meio-ponto $m$ e o *sticky* $st$, incrementando $L$ quando $m=1$ e há resto ou $L$ é ímpar, saturando em $[\mathrm{minpos}, \mathrm{maxpos}]$.*
  > *Ao testar nossa ULA contra a biblioteca oficial `libtakum` v2.0.0, batemos 100% nos 196.608 pares de `T8` e em 50.000 operações de `T16`, mas encontramos 128 casos em 10.000 multiplicações de `T32` (sobre 30.000 amostras totais) onde a `libtakum` diverge por 1 ULP ao usar um intermediário em `double`. Nossa ULA de 128 bits preserva o arredondamento único."*

---

### SLIDE 5 — 4. Fase 2: Extensão do Conjunto de Instruções RISC-V (`Zvtakum`) (`05:00 – 06:00`)
- **Conceito técnico chave (para dominar):**
  - Reproduz exatamente a **Tabela 1 da Seção 5.2 do Edital**, adicionando os campos reais de codificação binária (`funct6 = 000000` a `000100`, `opcode = 0x0B = custom-0`, `funct3 = 000`).
  - Destaque para `vtdot.vv`: acumula o produto escalar dos elementos ativos no elemento `0` do registrador destino `vd` com o dobro da largura (`EEW = 2·SEW`, isto é, `T8` acumula em `T16`, `T16` em `T32`, e `T32` em `T64`), e ao final da linha da matriz esparsa, `vncvt.t.t` estreita de volta de `2·SEW` para `SEW`!
- **Onde apontar:** Tabela das 5 instruções (mostrando `vtdot.vv` e `vncvt.t.t`) e os três itens abaixo (`custom-0`, `vtype.vsew` e eliminação de `fcsr`).
- **Fala sugerida:**
  > *"Na Fase 2, mapeamos as cinco instruções vetoriais solicitadas no edital: `vtadd.vv`, `vtsub.vv` e `vtmul.vv` operam elemento a elemento na largura configurada pelo `SEW` (`T8`, `T16` ou `T32`). Já a dupla `vtdot.vv` e `vncvt.t.t` foi desenhada pensando em álgebra linear esparsa e redes neurais: o `vtdot.vv` multiplica as vias ativas e acumula sequencialmente no elemento zero de `vd` com o dobro da largura (`2·SEW` — portanto `T32` acumula internamente em `T64`), e o `vncvt.t.t` faz o estreitamento RNE de `2·SEW` de volta para `SEW`.*
  > *Todas as cinco instruções foram alocadas no espaço `custom-0` (`opcode 0x0B`), respeitando máscara `v0.t`, comprimento `vl` e políticas agnósticas da RVV 1.0, e eliminando por completo os campos `frm` e `fflags` do `fcsr`."*

---

### SLIDE 6 — 5. Fase 2: Caminho de Dados RISC-V + Subsistema Vetorial `Zvtakum` (`06:00 – 07:00`)
- **Conceito técnico chave (para dominar):**
  - Este é o nosso diagrama TikZ completo. Na metade superior (preto/cinza) está o datapath RISC-V escalar clássico de 5 estágios (Busca, Decodificação, Execução, Memória e Write-Back). Na metade inferior (em azul-petróleo / *teal*) está o subsistema vetorial `Zvtakum` acoplado.
  - Como o escalar e o vetorial conversam?
    1. Na instrução `vsetvli`, o valor escalar `Dado 1 (rs1)` e os bits `[31..20]` configuram os **CSRs Vetoriais (`vl`, `vtype`, `vstart`)**.
    2. Nas cargas e armazenamentos vetoriais (`vle`/`vse`) e no *gather* indexado (`vluxei32.v`), a ULA escalar calcula o endereço base e o **VReg** fornece os índices/dados pela linha vertical **`Store Vetorial / Índice Gather`** até a Memória de Dados.
    3. Nas instruções `Zvtakum`, `Vet 1 (vs1)` e `Vet 2 (vs2)` saem do `VReg`, passam pelo **Decodificador Takum de 12 MSBs** (que extrai `[S,D,R,C,F]` e aplica o *ghost-bit pad* no `T8`), entram na **ULA Vetorial SIMD**, passam pelo bloco **Acumulador `2·SEW`, Narrow & Codificador RNE** (com realimentação `vd[0]` para o `vtdot.vv`), e voltam ao `VReg` via `MuxVWB`.
- **Onde apontar:** Seguir da esquerda para a direita na caixa pontilhada *teal* na parte inferior do slide.
- **Fala sugerida:**
  > *"Este diagrama mostra como o subsistema `Zvtakum` (na faixa inferior, em azul-petróleo) se integra ao datapath RISC-V base. À esquerda, os CSRs vetoriais recebem `rs1` da instrução `vsetvli` e distribuem `SEW` e `vl` para todo o pipeline vetorial. Do Banco de Registradores Vetoriais `VReg` saem `vs1` e `vs2` rumo ao Decodificador Takum Unificado de 12 MSBs, que extrai os 5 campos `[S, D, R, C, F]` com um único circuito para 8, 16 e 32 bits.*
  > *Em seguida, as vias SIMD da ULA Vetorial executam a aritmética e alimentam o estágio pós-ULA de Acúmulo `2·SEW`, Estreitamento e Codificação RNE — notem o laço de realimentação de `vd[0]` voltando para o acumulador no `vtdot.vv`, e a linha vertical que leva os índices de `vluxei32` do `VReg` para a Memória de Dados antes do `MuxVWB`."*

---

### SLIDE 7 (Item 6): Opções Consideradas, Decisões de Projeto e Justificativas (`06:30 - 07:35`)
- **Conceito técnico chave (para dominar):**
  - Este slide atende diretamente à **Seção 4.1 do Edital**, expondo as opções consideradas, as decisões tomadas e suas justificativas em **6 eixos**:
    1. **Takum Linear (Def. 8) vs. Logarítmico (Def. 2):** Avaliamos ambos no repositório (`scripts/bench_closure.py`). Embora o logarítmico reduza multiplicação a soma inteira, sua adição exige tabelas ROM não lineares ($\Delta_\pm$). O Linear mantém somadores e multiplicadores inteiros compatíveis com ULAs SIMD da RVV.
    2. **`custom-0` (`0x0B`) vs. `OP-V` (`0x57`):** Auditoria automatizada no `riscv-opcodes` mostrou de 11 a 33 `funct6` livres por classe e risco de colisão com extensões padrão futuras. Adotamos `custom-0`, espaço oficial da RISC-V International para extensões experimentais.
    3. **Inteiros de 128 bits vs. `double`:** Elimina os 128/10.000 desvios de duplo arredondamento em multiplicação `T32`.
    4. **Largura do acumulador (`2·SEW` vs. `SEW`, `EMUL=1`):** Permite acumular produtos `T32` em `T64` dentro de `vd[0]`, reduzindo o erro mediano em $2.56\times$ frente ao acumulador `T32` sem exigir banco vetorial `SEW=64`.
    5. **Modelo `vtdot.vv` com dois arredondamentos vs. *quire* exato:** O `vtdot.vv` aplica arredondamento RNE por acumulação em $2\cdot\mathrm{SEW}$ e `vncvt.t.t` estreita ao fim da linha, mantendo o estado confinado a `vd[0]` ($2\cdot\mathrm{SEW}$ bits) em vez de exigir um registrador *quire* de centenas de bits.
    6. **Sem `fcsr`:** RNE fixo no código + saturação em `maxpos`/`minpos` + `NaR` eliminam `frm` e a árvore OR de exceções de `fflags`.
- **Fala sugerida:**
  > *"Conforme solicitado nas diretrizes do projeto, sintetizamos nesta tabela seis decisões arquiteturais nas quais avaliamos alternativas antes de fechar o projeto:*
  > *Primeiro, escolhemos Takum Linear (Definição 8) em vez do Logarítmico porque dispensa tabelas não lineares $\Delta_\pm$ na adição vetorial.*
  > *Segundo, alocamos `Zvtakum` em `custom-0` (`0x0B`), evitando sobrecarga de `OP-V` após auditoria no `riscv-opcodes`.*
  > *Terceiro, implementamos a ULA interna com inteiros de 128 bits para eliminar duplo arredondamento em `T32`.*
  > *Quarto e quinto, adotamos acumulador escalar `vd[0]` de largura `2·SEW` (`EMUL=1`) com dois arredondamentos (passo RNE em `vtdot.vv` mais estreitamento ao fim da linha em `vncvt.t.t`), obtendo $2.56\times$ de redução adicional no erro sem exigir registradores de 64 bits no banco nem um *quire* dedicado.*
  > *E sexto, eliminamos dependência de `fcsr`, removendo barreiras de estado entre vias."*

---

### SLIDE 8 (Item 7): Fase 3 — Simulador `zt-sim`, Verificação e Kernel SpMV CSR (`07:35 - 08:40`)
- **Conceito técnico chave (para dominar):**
  - Quatro barreiras de verificação garantem consistência funcional em `zt-sim`:
    1. **81 checagens C++** (52 em `takum-test` + 29 em `zt-test`) e **75 testes Python** em `unittest` contra modelos racionais (`Fraction`), cobrindo tabelas exaustivas de `T8` ($3 \times 65.536$ pares + $65.536$ *narrowings*) e testes de instruções ilegais.
    2. Confronto com `libtakum` v2.0.0: 0 desvios em `T8` (196.608 ops) e `T16` (50.000 ops), e 30.000 amostras `T32` (0 desvios em add/sub, 128/10.000 em mul por duplo arredondamento no host).
    3. Oráculo `Float128` (`binary128`) validado contra `__float128`/`libquadmath` do GCC em **6.017 casos** (com apenas 3 diferenças conhecidas de sinal de zero).
    4. **Teste diferencial contra o `QEMU 10.2.2`** em $\mathrm{VLEN} \in \{128, 256, 512\}$ (9 execuções sem divergências; removemos a leitura pré-`vsetvli` de `csrr vtype` porque a especificação RVV 1.0 §3.11 define reset com `vill=1`, mantido no `zt-sim` e testado no `zt-test`, enquanto o QEMU 8.2.2 em modo usuário inicializava `vtype=0`) e conferência das **96 execuções SpMV**.
- **Fala sugerida:**
  > *"Entrando na Fase 3, construímos o simulador funcional `zt-sim` em C++17 para binários ELF64 RISC-V (`RV64IM`, `Zicsr`, `RVV 1.0` e `Zvtakum`). Nossa verificação reúne quatro camadas: 81 checagens C++ (52 do núcleo mais 29 do simulador) e 75 testes Python; confronto com `libtakum` v2.0.0; validação do oráculo `Float128` contra `libquadmath` em 6.017 casos; e teste diferencial byte a byte contra o `QEMU 10.2.2` em `VLEN` 128, 256 e 512 (9 execuções com zero divergências).*
  > *Para a SpMV CSR sobre 8 matrizes Harwell-Boeing, observem à direita que o `FP32` usa `vfmul.vv` mais `vfredusum.vs` (12 instruções por faixa), ao passo que o `Takum32` combina produto e soma em `vtdot.vv` (11 instruções por faixa) e executa um `vncvt.t.t` ao fim da linha."*

---

### SLIDE 9 (Item 8): Resultado 1 — Erro Relativo $\ell_2$ em 32 Bits vs. `Float128` (`08:40 - 09:45`)
- **Conceito técnico chave (para dominar):**
  - `FP32` (mediana $5.91 \times 10^{-8}$) vs. `Takum32` ($1.15 \times 10^{-8}$): `Takum32` reduz o erro mediano em **$5.15\times$** e vence em **7 de 8 matrizes** (`pores_1` fica para `FP32`).
  - Decomposição controlada: forçando acumulador de 32 bits em ambos (`2.94e-8` vs. `5.91e-8`), o ganho do formato `Takum32` é **$2.01\times$** (7/8 vitórias); o acumulador `T64` do `vtdot.vv` acrescenta **$2.56\times$** ($5.15 = 2.01 \times 2.56$).
  - **Comparação com `Posit(32,2)`:** sem escala, `Posit32` atinge mediana **$9.98 \times 10^{-9}$** e supera `Takum32` em **6 das 8 matrizes** de faixa dinâmica moderada, enquanto `Takum32` leva vantagem em `bcsstk01` ($5.06 \times 10^{-8}$ vs. $3.65 \times 10^{-7}$) e `pores_1` ($7.87 \times 10^{-8}$ vs. $9.45 \times 10^{-8}$).
- **Fala sugerida:**
  > *"Na SpMV em 32 bits medida contra o oráculo `Float128`, o kernel RVV `FP32` obtém erro mediano de $5.91 \times 10^{-8}$, e o kernel `Takum32` atinge $1.15 \times 10^{-8}$: redução de $5.15\times$, vencendo em 7 das 8 matrizes.*
  > *Isolando formato e acumulador nas colunas de controle, vemos $2.01\times$ vindos do formato `Takum32` (com acumulador 32 bits) e $2.56\times$ do acumulador `T64` do `vtdot.vv`. Incluímos também o controle `Posit(32,2)`: nas matrizes bem comportadas perto da unidade, o `Posit32` atinge mediana $9.98 \times 10^{-9}$ e vence em 6 de 8 matrizes, enquanto o `Takum32` sustenta erro menor nas matrizes de maior dispersão de magnitude como `bcsstk01` e `pores_1`."*

---

### SLIDE 10 (Item 9): Resultado 2 — 8/16 Bits, Posit, Overflows e SuiteSparse-100 (`09:45 - 10:50`)
- **Conceito técnico chave (para dominar):**
  - Sem escala (`none`): `E4M3` sofre *overflow* em **4/8** matrizes e `E5M2`/`FP16` em **3/8**. `Takum8`, `Takum16`, `Posit8/16` e `bfloat16` têm **0/8 falhas finitas**.
  - Em 16 bits, `Takum16` ($7.43 \times 10^{-4}$) supera `bfloat16` ($2.36 \times 10^{-3}$) por **$3.17\times$** (7/8) sem escala e **$7.61\times$** (8/8) com `pow2-bound`. O controle `Posit(16,2)` marca $6.54 \times 10^{-4}$ e vence `Takum16` em **6/8 matrizes**.
  - Em 8 bits, **`Posit(8,2)` supera `Takum8` em 7 de 8 matrizes sem escala** ($1.24 \times 10^{-1}$ vs. $1.52 \times 10^{-1}$) **e em 8 de 8 com `pow2-bound`** ($3.83 \times 10^{-2}$ vs. $8.39 \times 10^{-2}$), porque dedica mais bits à fração perto de $1$.
  - No SuiteSparse-100 (gerado originalmente com oráculo `long double` de 80 bits, com script Python `binary128` e validação local nas 8 matrizes HB no repositório), o `Takum16` limita o erro máximo de conversão em **$0.85\%$**, contra **$99.9\%$** do `Posit16` quando magnitudes ultrapassam a região central do regime.
- **Fala sugerida:**
  > *"Em 8 e 16 bits, o gráfico de CDF à esquerda reúne 94.276 avaliações de linhas (incluindo os controles em `Posit`): sem escala, `E4M3` estoura em 4 matrizes e `E5M2` e `FP16` estouram em 3, enquanto `Takum8/16`, `Posit8/16` e `bfloat16` permanecem 100% finitos. O `Takum16` supera o `bfloat16` por $3.17\times$ sem escala e $7.61\times$ com `pow2-bound`.*
  > *Também registramos o contraste com o `Posit`: nessa amostra de matrizes com entradas próximas de $1$, o `Posit(8,2)` supera o `Takum8` em 7 das 8 matrizes sem escala e 8/8 escalado, porque o `Takum8` reserva 5 bits fixos para `(S,D,R)`. Em contrapartida, nas 100 matrizes SuiteSparse à direita, o `Takum16/32` evita o colapso de cauda do `Posit` ($0.85\%$ vs. $99.9\%$ no `Posit16`)."*

---

### SLIDE 11 (Item 10): Resultado 3 — Contagem de Instruções, CSRs e Modelo Analítico (`10:50 - 11:45`)
- **Conceito técnico chave (para dominar):**
  - Modelo linear exato: $N_f = r_f R + c_f S + K$ ($K = 21$), com **resíduo máximo = 0** nas 96 execuções reais e 12/12 matrizes sintéticas (`FP32`: $r=13, c=12$; `Takum32`: $r=14, c=11$).
  - Subtraindo ambos: $N_{\text{Takum32}} - N_{\text{FP32}} = R - S \le 0$ para todo CSR sem linha vazia ($S \ge R$): `Takum32` executa menos instruções em 13 pares e igual número em 11 (24/24 pares), mesmas escritas CSR (`1.07`/nnz em `VLEN=256`) e **$-15.6\%$ elementos vetoriais ativos** (`4.50` vs. `5.33`/nnz).
  - Em 8 e 16 bits, alternar `vtype` para índices CSR de 32 bits custa 1 `vsetvli` adicional por faixa, mas em `VLEN=128` o maior empacotamento reduz o total de instruções em **$-19.3\%$ (`T16`)** e **$-26.6\%$ (`T8`)**.
- **Fala sugerida:**
  > *"Na avaliação estrutural, ajustamos o modelo analítico $N_f = r_f R + c_f S + K$, que reproduz todas as 96 execuções do simulador e 12 matrizes sintéticas com resíduo máximo zero.*
  > *No corte em 32 bits, $N_{\text{Takum32}} - N_{\text{FP32}} = R - S \le 0$: nos 24 pares avaliados, `Takum32` executa menos ou o mesmo número de instruções que `FP32`, mantém o mesmo número de escritas em CSR e reduz os elementos ativos em 15.6% (`4.50` vs. `5.33` por não nulo). Em 8 e 16 bits, alternar o `vtype` entre o índice de 32 bits e os valores aumenta as escritas CSR, porém em `VLEN=128` a densidade vetorial reduz as instruções totais em 19.3% (`T16`) e 26.6% (`T8`)."*

---

### SLIDE 12 (Item 11): Limitações e Ameaças à Validade (`11:45 - 12:30`)
- **Conceito técnico chave (para dominar):**
  - Apresentar com transparência científica os limites do estudo:
    1. Amostra SpMV restrita a 8 matrizes Harwell-Boeing ($30$ a $1033$ linhas) com entradas majoritariamente em faixa moderada, favorecendo `Posit(8,2)`/`Posit(16,2)` em acurácia mediana.
    2. CSVs do benchmark SuiteSparse-100 foram gerados originalmente na rodada C11 com `long double` de 80 bits; o repositório agora traz o gerador em Python `binary128` e o manifesto auditável, mas o servidor `sparse.tamu.edu` bloqueou o download automatizado (`HTTP 403`), mantendo a validação de `binary128` restrita às 8 matrizes locais.
    3. `zt-sim` é funcional (instruções e CSRs), sem estimativa de ciclos, área ou potência pós-síntese; baselines `FP8`, `FP16`, `bfloat16` e `Posit` foram simulados em Python preservando a mesma ordem de redução dos ELFs RISC-V; e o `vtdot.vv` sequencial (dois arredondamentos) é dependente de `VLEN`.
- **Fala sugerida:**
  > *"Antes de concluir, destacamos objetivamente cinco limitações deste estudo: primeiro, a avaliação SpMV ponta a ponta utiliza 8 matrizes pequenas a médias da coleção Harwell-Boeing, faixa na qual `Posit(8,2)` e `Posit(16,2)` ainda superam `Takum` por terem mais bits de mantissa próximos a 1; segundo, os CSVs agregados do SuiteSparse-100 vêm de rodada em `long double` de 80 bits, enquanto nosso novo gerador Python em `binary128` pôde ser verificado localmente nas 8 matrizes porque o servidor remoto retornou HTTP 403; terceiro, `zt-sim` é um simulador funcional sem modelo de ciclos, área ou energia; quarto, os demais baselines numéricos rodaram em referência funcional Python com a mesma ordem de redução por faixas; e quinto, a redução `vtdot.vv` com dois arredondamentos depende de `VLEN`."*

---

### SLIDE 13 (Item 12): Conclusão e Síntese das Entregas (`12:30 - 13:05`)
- **Fala sugerida:**
  > *"Sintetizando as entregas: implementamos a janela unificada de 12 MSBs e a ULA inteira de 128 bits, a extensão vetorial `Zvtakum` em `custom-0` sem dependência de `fcsr`, a redução de $5.15\times$ em erro mediano frente ao `FP32` em 32 bits sem exceder o total de instruções, tolerância a overflow em 8 e 16 bits, além dos artigos IEEE de 6 páginas em Inglês e Português, auditoria de 25 referências em `references/audit.csv` e o fluxo `run_all.sh --strict`. Passamos agora ao terminal para a demonstração ao vivo."*

---

### SLIDE 14 (Item 13): Demonstração Funcional ao Vivo (Comandos Reais) (`13:05 - 15:00`)
- **Onde apontar:** Mostrar no projetor os 4 blocos de comandos reais enquanto executa ao vivo no terminal.
- **Fala sugerida:**
  > *"Neste último slide estão os comandos exatos que vamos executar agora ao vivo no terminal: a suíte C++ e Python (`make test && make sim-test`), o teste diferencial contra `QEMU 10.2.2` (`make sim-check`), a execução direta do kernel SpMV em `bcsstk01` no `zt-sim` comparando `Takum32` com `FP32`, e a demonstração interativa `./run_all.sh demo`."*

---

## 4. Passo a Passo da Demonstração Funcional ao Vivo no Terminal (`2 min`)

Deixe um terminal aberto na raiz do repositório (`/var/home/andrerezende/Projects/aoc-takum-riscv`) e execute os **3 passos abaixo**:

### Passo 1 — Validar a ULA Takum (Fase 1) e os Vetores Dourados do Simulador (Fase 2) (`~30 s`)
Execute:
```sh
make test && make sim-test
```
- **O que aparece na tela:**
  - `52 verificações, 0 falhas` (C++ `takum-test`: campos $S,D,R,C,F$, tabelas exaustivas `T8`, `T16/T32`, `NaR` e RNE).
  - `Ran 75 tests` ... `OK` (`unittest` em Python: modelo exato `Fraction`, `LogTakum`, `Posit`, confronto com `libtakum` e `binary128`).
  - `29 verificações, 0 falhas` (`zt-test`: instruções vetoriais `Zvtakum`, `narrow T16->T8`, `T32` amostrado, reset `vtype.vill=1` segundo RVV 1.0 §3.11 e instrução `custom-0` ilegal).

### Passo 2 — Verificação Diferencial Byte a Byte contra o QEMU 10.2.2 (`~20 s`)
Execute:
```sh
make sim-check
```
- **O que aparece na tela:**
  - `rvv_std`, `scalar_ops` e `zvtakum_isa` rodando em `VLEN=128`, `VLEN=256` e `VLEN=512` $\rightarrow$ **`9 execuções, 0 divergências`**.
  - **O que comentar:** *"Aqui nosso simulador `zt-sim` acabou de rodar os mesmos binários ELF64 que o `qemu-riscv64` 10.2.2 nas três larguras de vetor e comparou a saída byte a byte: zero divergências."*

### Passo 3 — Executar um Kernel SpMV Real (`bcsstk01`) em `Takum32` vs. `FP32` e Comparar Contadores (`~60 s`)
Execute:
```sh
./build/zt-sim build/spmv/bcsstk01.takum32.v256.elf --vlen 256 --stdout /tmp/y_t32.bin --counters /tmp/c_t32.json
./build/zt-sim build/spmv/bcsstk01.fp32.v256.elf --vlen 256 --stdout /tmp/y_fp32.bin --counters /tmp/c_fp32.json
cat /tmp/c_t32.json
cat /tmp/c_fp32.json
```
- **O que vai aparecer na tela (exatamente estes números):**
  - Para **`Takum32`** (`c_t32.json`):
    ```json
    {
      "vlen_bits": 256,
      "exit_code": 0,
      "insn_total": 1353,
      "insn_scalar": 813,
      "insn_vsetvl": 156,
      "insn_vector": 276,
      "insn_zvtakum": 108,
      "csr_reads": 0,
      "csr_writes": 312,
      "elem_active": 1744,
      "bytes_loaded": 4800,
      "bytes_stored": 192,
      "index_bytes_loaded": 1600
    }
    ```
  - Para **`FP32`** (`c_fp32.json`):
    ```json
    {
      "vlen_bits": 256,
      "exit_code": 0,
      "insn_total": 1365,
      "insn_scalar": 813,
      "insn_vsetvl": 156,
      "insn_vector": 396,
      "insn_zvtakum": 0,
      "csr_reads": 0,
      "csr_writes": 312,
      "elem_active": 2096,
      "bytes_loaded": 4800,
      "bytes_stored": 192,
      "index_bytes_loaded": 1600
    }
    ```
- **O que apontar para a banca:**
  1. **`insn_total`: `1353` (`Takum32`) vs. `1365` (`FP32`)** $\rightarrow$ A matriz `bcsstk01` tem $R = 48$ linhas e, em $\mathrm{VLEN}=256$, $S = 60$ faixas. Pela identidade no kernel testado, $N_{\text{Takum32}} - N_{\text{FP32}} = R - S = 48 - 60 = -12$, e $1353 - 1365 = -12$ instruções.
  2. **`insn_zvtakum`: `108`** $\rightarrow$ São exatamente as $60$ instruções `vtdot.vv` (uma por faixa) mais as $48$ instruções `vncvt.t.t` (uma ao fim de cada linha): $60 + 48 = 108$!
  3. **`csr_writes`: `312` nos dois** $\rightarrow$ Zero sobrecarga de CSR em 32 bits!
  4. **`elem_active`: `1744` (`Takum32`) vs. `2096` (`FP32`)** $\rightarrow$ Redução de 352 elementos ativos processados pelas vias vetoriais porque o `vtdot.vv` funde multiplicação e redução em uma única passagem!

### Passo 4 — Demonstração Interativa e Validação Estrita da Entrega (`./run_all.sh`)
Execute:
```sh
./run_all.sh demo
./run_all.sh --strict
```
- **O que aparece na tela:** `./run_all.sh demo` roda `takum-test` (52), `zt-test` (29) e a demonstração de faixa dinâmica (`T8` vs `FP16`/`E4M3`); `./run_all.sh --strict` verifica o limite de 6 páginas dos artigos PDF, audita as 25 chaves BibTeX em `references/audit.csv` e gera `artifacts/manifest.json`.

---

## 5. Guia Rápido de Respostas para Perguntas da Banca (Q&A)

1. **"Por que vocês escolheram o espaço `custom-0` (`0x0B`) em vez de colocar no `OP-V` (`0x57`) junto com a RVV padrão?"**
   - **Resposta:** Fizemos um levantamento automatizado no repositório oficial `riscv-opcodes` e verificamos que existem entre 11 e 33 códigos `funct6` livres em `OP-V` dependendo da classe de operando, que a RISC-V International reserva para futuras extensões padronizadas (como criptografia e matrizes). Usar `custom-0` (`0x0B`, `funct3=000`) segue a convenção oficial da arquitetura RISC-V para extensões não padronizadas sem risco de colisão de binários.

2. **"Por que o `Posit(8,2)` superou o `Takum8` em 7 de 8 matrizes sem escala no SpMV?"**
   - **Resposta:** Porque em 8 bits o cabeçalho fixo $(S, D, R)$ do Takum consome 5 bits, deixando no máximo 3 bits de fração perto de $1$, enquanto o `Posit(8,2)` (sem bit separado de direção) aloca até 4 bits perto de $1$. Na amostra Harwell-Boeing escalada ou moderada isso favorece o `Posit(8,2)`, mas o Takum mantém piso dinâmico amplo nas caudas extremas do SuiteSparse-100 onde o regime unário do Posit entra em colapso de precisão.

3. **"Por que o `Takum8` teve erro alto (0.64 a 1.21) em algumas matrizes como `bcsstk01` e `west0132` sem reescalamento?"**
   - **Resposta:** Porque essas matrizes têm entradas de rigidez na casa de $10^6$ a $10^9$ ($|e| \ge 15$). Em `T8` ($n=8$), como 5 bits vão para $(S, D, R)$ e o regime $r$ cresce para representar expoentes grandes, quando $|e| \ge 15$ temos $r \ge 3$ e restam $p = 8 - 5 - 3 = 0$ bits de fração (os 4 *ghost bits* truncam a característica). Ou seja, em `T8` extremo ele preserva a ordem de grandeza sem estourar para `NaN`/`Inf` (diferente do `E4M3` que falha totalmente), e quando aplicamos `pow2-bound` o erro mediano do `Takum8` cai para $8.39 \times 10^{-2}$, empatando em 4–4 com o `E5M2`.

4. **"Como funciona o arredondamento no espaço de códigos e por que ele difere do arredondamento no espaço de valores?"**
   - **Resposta:** No IEEE 754, dentro de um mesmo expoente, os números são igualmente espaçados (linear), então o ponto médio entre dois códigos consecutivos tem o mesmo valor aritmético. No Takum, quando $p=0$ (fronteira onde a característica $C$ é truncada no `T8`), dois códigos consecutivos representam potências de 2 distantes por um fator (ex.: código 1 é $2^{-239}$ e código 2 é $2^{-223}$). Olhando para os bits do código antes de truncar, o bit de meio-ponto $m=1$ corresponde à média geométrica $2^{-231}$ (e não à média aritmética). Arredondar pelo bit $m$ no espaço de códigos economiza um comparador aritmético completo em hardware e segue exatamente a especificação VHDL de Hunhold.

5. **"Por que em 8 e 16 bits o número de escritas em CSR aumenta em relação ao `FP32`?"**
   - **Resposta:** Porque no formato CSR as colunas (`col_idx`) são inteiros de 32 bits (`uint32_t`). Quando os valores da matriz estão em `T32` ou `FP32`, tanto o índice quanto o dado têm 32 bits (`SEW=32`), então basta um único `vsetvli` por faixa. Já quando os dados estão em `T8` ou `T16`, para carregar $vl$ índices de 32 bits sem truncar endereços de coluna acima de 65.535, o kernel faz um `vsetvli` para ajustar o `EMUL` do índice e outro para voltar ao `SEW` de 8 ou 16 bits. Ainda assim, em `VLEN=128`, cabem 2 a 4 vezes mais elementos por faixa, o que reduz o número total de instruções executadas em $-19.3\%$ (`T16`) e $-26.6\%$ (`T8`).
