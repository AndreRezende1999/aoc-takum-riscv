# Roteiro de Apresentação e Guia de Storytelling — Zvtakum (AOC 2026/02)

**Tempo total estipulado pelo Edital (`ProjectGuidelinesAOC.pdf`):** 15 minutos (12m45s de exposição + 2m15s de demonstração funcional ao vivo), seguido de arguição.
**Estrutura dos Slides (`slides/slides.tex`):** 15 slides enxutos, sem prefixos numéricos redundantes nos títulos e alinhados com os critérios da Seção 6.3 do edital:
1. Capa
2. Motivação, Problema e Objetivos do Projeto
3. Fase 1: Codificação Takum Linear (Def. 8) e Janela de 12 MSBs
4. Fase 1: ULA Takum em Inteiros de 128 Bits e RNE no Código
5. Fase 2: Extensão do Conjunto de Instruções RISC-V (`Zvtakum`)
6. Fase 2: As Cinco Instruções, Uma a Uma
7. Fase 2: Caminho de Dados RISC-V + Subsistema Vetorial `Zvtakum`
8. Fase 2: Onde Cada Instrução Passa Dentro da Arquitetura
9. Alternativas Consideradas, Decisões de Projeto e Justificativas
10. Fase 3: Simulador `zt-sim`, Verificação e Kernels SpMV e ML
11. Fase 3: Erro Relativo $\ell_2$ em 32 Bits vs. `Float128`
12. Fase 3: Baixa Precisão (8 e 16 Bits), Posits e Reescalonamento
13. Resultados: 15 Formatos em 100 Matrizes SuiteSparse e Custo RVV
14. Conclusão, Limitações e Síntese das Entregas
15. Demonstração Funcional ao Vivo (Live Demo)

---

## 1. O Arco Narrativo (Storytelling)

A apresentação segue uma estrutura de **Problema $\rightarrow$ Causa Raiz $\rightarrow$ Solução Arquitetural $\rightarrow$ Decisões de Engenharia $\rightarrow$ Prova Experimental e Demonstração**:

1. **O Gancho (Slides 1–2):** Em Álgebra Linear Esparsa (SpMV, $y = A \cdot x$) e inferência de redes neurais esparsas/quantizadas, matrizes reais de engenharia (como `bcsstk01`, com entradas de $3{,}3 \times 10^3$ a $2{,}9 \times 10^9$) quebram formatos estreitos tradicionais (`FP16`, `FP8 E4M3`) com *overflow* (`NaN`/`Inf`). Mesmo o `FP8 E5M2` e o `bfloat16` só sobrevivem às custas de um **reescalonamento prévio por software** (`pow2-bound`), que exige varrer a matriz inteira antes de calcular.
2. **A Ideia Central (Slide 3):** O formato **Takum Linear** (Hunhold, 2024) resolve a raiz do problema: sua faixa dinâmica de $\approx 10^{\pm 72}$ a $10^{\pm 77}$ é praticamente **invariante à largura de bits** ($n \in \{8, 16, 32, 64\}$). E o crucial para Arquitetura de Computadores: os campos de direção ($D$), regime ($R$) e característica ($C$) cabem sempre nos **12 MSBs**, permitindo um **único decodificador de hardware compartilhado** para qualquer largura.
3. **A Construção Incremental (Slides 4–9):**
   - *Fase 1 (Slide 4):* Soma, subtração e multiplicação exatas em `T8`, `T16`, `T32` e `T64` em aritmética inteira pura de 128 bits (`__uint128_t`), sem tocar na FPU IEEE 754 do hospedeiro, com arredondamento RNE determinístico no espaço de códigos.
   - *Fase 2 (Slides 5–8):* Alocamos a extensão **Zvtakum** em `custom-0` (`0x0B`), detalhamos o funcionamento algorítmico das 5 instruções (`vtadd.vv`, `vtsub.vv`, `vtmul.vv`, `vtdot.vv`, `vncvt.t.t`), apresentamos o diagrama de caminho de dados e explicamos exatamente o que cada instrução lê, por onde passa e o que escreve (sem tocar em `fcsr` nem acessar memória).
   - *Decisões de Projeto (Slide 9):* Mostramos explicitamente o que consideramos, o que descartamos e o porquê (`custom-0` vs `OP-V`; Takum Linear vs Logarítmico; acumulador de $2\cdot\mathrm{SEW}$ em `vd[0]` vs *quire*; `vtype.vill=1` estrito da especificação RVV 1.0 §3.11 validado contra `QEMU 10.2.2`).
4. **O Clímax Experimental (Slides 10–14):**
   - O par `vtdot.vv` + `vncvt.t.t` atua simultaneamente como núcleo do SpMV CSR e como primitiva fundamental de **kernels de aprendizado de máquina quantizados** (camadas lineares `GEMV`/`GEMM`, projeções de atenção e redes neurais podadas em 8 e 16 bits).
   - Em 32 bits (`Takum32` vs `FP32`), o acúmulo alargado em `T64` via `vtdot.vv` reduz a mediana do erro relativo em **1,54×** frente ao `FP32` (e **55,9×** na matriz `bcsstk01` com `T64`).
   - Em 8 e 16 bits sem reescalonamento, `FP16`, `E4M3` e `E5M2` falham com `NaN`, enquanto `Takum8` e `Takum16` convergem em **100% das matrizes** sem pré-processamento.
   - Na varredura de **100 matrizes SuiteSparse × 15 formatos**, `Takum16` e `Takum32` evitam o colapso de precisão nas caudas observado em `Posit16`/`Posit32`.
   - No custo de instruções RVV, provamos com o modelo analítico fechado $N = rR + cS + K$ (**resíduo zero nas 24 configurações**) que o par `vtdot.vv` + `vncvt.t.t` nunca excede o `FP32` e reduz em até **15,6% os elementos ativos por não nulo**.
5. **A Prova ao Vivo (Slide 15):** Rodamos os testes unitários e diferenciais (`make test && make sim-test` e `make sim-check`) e executamos o simulador `zt-sim` ao vivo na matriz `bcsstk01`.

---

## 2. Divisão de Tempo e Papéis (Equilibrada para 4 Integrantes)

| Integrante | Escopo | Slides | Tempo contínuo |
| :--- | :--- | :---: | :---: |
| **Apresentador 1** | Contexto, Problema do *Overflow*, Formato Takum (12 MSBs) e ULA 128-bit | Slides 1 a 4 | `00:00 - 03:30` (3m30s) |
| **Apresentador 2** | Fase 2: ISA `custom-0`, As 5 Instruções, Datapath e Fluxo Arquitetural | Slides 5 a 8 | `03:30 - 07:00` (3m30s) |
| **Apresentador 3** | Decisões de Projeto, Fase 3 (SpMV + Kernels ML) e Precisão em 32 Bits | Slides 9 a 11 | `07:00 - 10:15` (3m15s) |
| **Apresentador 4** | Baixa Precisão (8/16b), SuiteSparse-100, Conclusão e Live Demo | Slides 12 a 15 | `10:15 - 15:00` (4m45s) |

---

## 3. Roteiro Slide a Slide (O que falar e onde apontar)

### SLIDE 1: Capa (`00:00 - 00:25`)
* **Quem fala:** Apresentador 1
* **Fala sugerida:**
  > "Olá a todos, professor e colegas. Nós somos o grupo formado por André, Gabriel, Isadora e João Pedro. Neste projeto integrador de AOC, nós projetamos, implementamos em um simulador RISC-V de 64 bits e avaliamos a **Zvtakum**: uma extensão vetorial experimental para aritmética **Takum Linear** aplicada à multiplicação matriz-vetor esparsa (SpMV) e a kernels de aprendizado de máquina quantizados."

---

### SLIDE 2: Motivação, Problema e Objetivos do Projeto (`00:25 - 01:30`)
* **Quem fala:** Apresentador 1
* **Onde apontar:** Aponte primeiro para o bloco da esquerda (fragmentação do IEEE 754 em matrizes esparsas e inferência ML) e depois para os 4 objetivos à direita.
* **Fala sugerida:**
  > "Por que buscar uma alternativa ao IEEE 754 em arquiteturas vetoriais? Quando executamos o kernel SpMV ($y = A \cdot x$) ou inferência de redes neurais esparsas em 8 e 16 bits, enfrentamos uma fragmentação severa: o `FP16` satura em $6{,}55 \times 10^4$ e o `FP8 E4M3` em $448$, gerando `Inf` e `NaN` sem reescalonamento prévio por software (`pow2-bound`). Além disso, na especificação RVV 1.0, o suporte a `FP16` e `bfloat16` exige múltiplas extensões, 96 instruções e 25 conversões cruzadas acopladas ao registrador `fcsr`.
  > À direita estão nossos 4 objetivos alinhados às 3 fases do projeto: unificar a aritmética com o codec de **12 MSBs** e ULA inteira de 128 bits, projetar a extensão vetorial **Zvtakum** em `custom-0`, e avaliar o SpMV e kernels de aprendizado de máquina frente ao IEEE 754 e Posit contra uma referência `Float128` e o `QEMU 10.2.2`."

---

### SLIDE 3: Fase 1 — Codificação Takum Linear (Def. 8) e Janela de 12 MSBs (`01:30 - 02:35`)
* **Quem fala:** Apresentador 1
* **Onde apontar:** Aponte para a fórmula de $L_{\max}=12$ bits no topo e depois para os três painéis do gráfico $\log_{10}|x| \in [-50, 50]$ embaixo.
* **Fala sugerida:**
  > "Como o Takum mantém alcance de $\approx 10^{\pm 72}$ a $10^{\pm 77}$ em qualquer largura? Após o sinal $S$ (1 bit) e direção $D$ (1 bit), o regime $R$ de 3 bits determina a largura $r \in [0, 7]$ da característica $C$. Logo, **o cabeçalho inteiro ocupa no máximo $1 + 1 + 3 + 7 = 12$ bits (`12 MSBs`)!** Diferente do Posit, cujo regime unário pode varrer toda a palavra de 32 ou 64 bits, o Takum usa um único decodificador fixo de 12 bits para `T8`, `T16` e `T32`.
  > No gráfico abaixo, no intervalo $\log_{10}|x| \in [-50, 50]$, vemos o compromisso estrutural: no centro ($|x| \in [0{,}5, 2)$), `Takum` e `Posit` empatam em $n-4$ bits (acima do `FP16`, `bfloat16` e `FP32`); entre $0{,}3$ e $4{,}8$ décadas o `Posit` retém 1 a 2 bits extras, mas despenca nas caudas enquanto o `FP16`/`OFP8` sofrem *overflow* e o `Takum16/32` sustenta pisos estáveis de 5 e 21 bits."

---

### SLIDE 4: Fase 1 — ULA Takum em Inteiros de 128 Bits e RNE no Código (`02:35 - 03:30`)
* **Quem fala:** Apresentador 1
* **Onde apontar:** Aponte para os três blocos: representação interna em 128 bits, arredondamento RNE no espaço de códigos e comparação com a `libtakum`.
* **Fala sugerida:**
  > "Na Fase 1, implementamos o codec e a ULA Takum em C++20 usando apenas inteiros de 64 e 128 bits (`__uint128_t`), sem tocar em ponto flutuante da máquina hospedeira.
  > O arredondamento **Round-to-Nearest-Ties-to-Even (RNE)** opera diretamente no espaço de códigos usando o bit de meio-ponto $m$ e o *sticky bit* $st$, saturando em $[1, 2^{n-1}-1]$ sem gerar infinito.
  > Essa escolha arquitetural é decisiva: em 30.000 amostras `T32`, verificamos que implementar `T32` via `double` do hospedeiro (como faz a `libtakum`) sofre duplo arredondamento em 128 de 10.000 multiplicações de 1 ULP, o que a nossa ULA inteira de 128 bits evita completamente."

---

### SLIDE 5: Fase 2 — Extensão do Conjunto de Instruções RISC-V (`Zvtakum`) (`03:30 - 04:15`)
* **Quem fala:** Apresentador 2
* **Onde apontar:** Aponte para a tabela das 5 instruções no topo e para os três pontos de integração RVV embaixo.
* **Fala sugerida:**
  > "Entrando na **Fase 2**, projetamos as 5 instruções da extensão **Zvtakum** no espaço proprietário **`custom-0` (`0x0B`)**: `vtadd.vv`, `vtsub.vv` e `vtmul.vv` para aritmética vetorial em largura `SEW`; `vtdot.vv` para produto interno acumulando em $2\cdot\mathrm{SEW}$; e `vncvt.t.t` para estreitamento RNE.
  > Alocar em `custom-0` evita qualquer colisão com os 11 a 33 *slots* `funct6` livres de `OP-V` reservados para extensões futuras, ao mesmo tempo em que reutiliza `vtype.vsew`, `vl`, `vstart` e a máscara `v0.t` e elimina toda dependência de `fcsr`."

---

### SLIDE 6: Fase 2 — As Cinco Instruções, Uma a Uma (`04:15 - 05:15`)
* **Quem fala:** Apresentador 2
* **Onde apontar:** Aponte para a coluna da esquerda (`vtadd.vv`/`vtsub.vv` e `vtmul.vv`) e depois para a coluna da direita (`vtdot.vv` com destaque em vermelho e `vncvt.t.t`).
* **Fala sugerida:**
  > "Neste slide detalhamos o que cada uma das cinco instruções faz internamente:
  > - À esquerda, em `vtadd.vv` e `vtsub.vv`, decodificamos `vs2[i]` e `vs1[i]`, alinhamos os expoentes deslocando o menor, somamos exato em 128 bits e codificamos em `SEW`. Como o Takum é simétrico em complemento de dois, o `vtsub.vv` usa exatamente o mesmo caminho somador apenas negando `b` em complemento de dois.
  > - Embaixo à esquerda, `vtmul.vv` soma os expoentes e multiplica os significandos de 64 bits gerando 128 bits exatos antes de arredondar.
  > - À direita, temos o coração do SpMV e dos kernels de ML: o **`vtdot.vv`**. Ele lê o acumulador largo em `vd[0]` (de largura $2\cdot\mathrm{SEW}$) e, para cada elemento ativo $i$ em ordem crescente, multiplica `a * b` codificando em $2\cdot\mathrm{SEW}$ (primeiro arredondamento) e soma ao acumulador `acc` em $2\cdot\mathrm{SEW}$ (segundo arredondamento). Destacamos que são **dois arredondamentos por termo — portanto não é um FMA** — mas em compensação todo o estado cabe no próprio registrador `vd[0]` de $2\cdot\mathrm{SEW}$, sem exigir um registrador *quire* gigante dedicado!
  > - Por fim, o **`vncvt.t.t`** decodifica $2\cdot\mathrm{SEW}$ e recodifica em `SEW`, rodando uma única vez no fim de cada linha da matriz."

---

### SLIDE 7: Fase 2 — Caminho de Dados RISC-V + Subsistema Vetorial `Zvtakum` (`05:15 - 06:05`)
* **Quem fala:** Apresentador 2
* **Onde apontar:** Siga o fluxo no diagrama: `Instruction Fetch/Decode` $\rightarrow$ `Vector Register File v0-v31` $\rightarrow$ `Decodificador Takum 12 MSBs` $\rightarrow$ `ULA Vetorial Takum + Acumulador 2*SEW` $\rightarrow$ `Mux VWB`.
* **Fala sugerida:**
  > "Este diagrama mostra como a unidade funcional Zvtakum se acopla ao processador RISC-V: o banco de registradores vetoriais `v0`–`v31` alimenta o **Frontend Compartilhado de 12 MSBs**, que entrega sinal, característica e fração para a **ULA Vetorial de 128 bits** e para o **Acumulador de $2\cdot\mathrm{SEW}$** com realimentação de `vd[0]`, retornando pelo empacotador RNE e pelo bloco `Narrow` ao barramento de escrita vetorial (`Mux VWB`)."

---

### SLIDE 8: Fase 2 — Onde Cada Instrução Passa Dentro da Arquitetura (`06:05 - 07:00`)
* **Quem fala:** Apresentador 2
* **Onde apontar:** Aponte para as 3 linhas da tabela no topo e depois para os dois blocos inferiores (`O que as cinco têm em comum` e `O que elas não fazem`).
* **Fala sugerida:**
  > "Para fechar a arquitetura da Fase 2, esta tabela resume o caminho exato de cada instrução no hardware:
  > - `vtadd.vv`, `vtsub.vv` e `vtmul.vv` leem `vs1` e `vs2` filtrados por `v0`, passam pelo decodificador de 12 MSBs, pela ULA vetorial e pelo codificador RNE, e escrevem `vd[i]` elemento a elemento pelo `Mux VWB`.
  > - O `vtdot.vv` lê `vs1`, `vs2` e **o próprio `vd[0]` em realimentação**, passa pelo acumulador de $2\cdot\mathrm{SEW}$ e escreve **apenas em `vd[0]`**, sem tocar nos demais elementos de `vd`.
  > - Já o `vncvt.t.t` lê `vs2` com o dobro da largura ($\mathrm{EMUL} = 2\,\mathrm{LMUL}$), passa pelo bloco `Narrow` e escreve `vd[i]` na largura `SEW`.
  > E observem os dois pontos embaixo: todas as cinco consultam `vtype`, `vl` e `vstart`, mas **nenhuma toca no `fcsr`**, **nenhuma acessa memória** (o que segue com `vle` e `vluxei32`) e **nenhuma calcula endereço** (que permanece no caminho escalar). É exatamente por isso que o subsistema Zvtakum entra como um bloco *ao lado* do processador, de forma modular e limpa."

---

### SLIDE 9: Alternativas Consideradas, Decisões de Projeto e Justificativas (`07:00 - 08:00`)
* **Quem fala:** Apresentador 3
* **Onde apontar:** Percorra as 6 linhas da tabela comparativa.
* **Fala sugerida:**
  > "Atendendo à Seção 4.1 do edital, sintetizamos aqui as 6 decisões centrais de projeto e as alternativas descartadas:
  > 1. **Takum Linear (Def. 8)** em vez do Logarítmico, para usar somadores inteiros SIMD sem ROMs não-lineares $\Delta_\pm$.
  > 2. **Espaço `custom-0` (`0x0B`)** em vez de `OP-V` (`0x57`), preservando os *slots* padrões livres e evitando colisões futuras.
  > 3. **ULA inteira de 128 bits (`__int128`)** em vez de `double` do hospedeiro, eliminando o duplo arredondamento em `T32`.
  > 4. **Acumulador em $2\cdot\mathrm{SEW}$ dentro de `vd[0]`**, que reduz o erro em 32 bits em $\RazaoAcumuladorTakum\times$ sem exigir banco `SEW=64`.
  > 5. **Modelo de 2 arredondamentos no `vtdot.vv` + `vncvt.t.t`** em vez de um registrador *quire* dedicado.
  > 6. **Independência total de `fcsr`**, substituindo exceções IEEE por saturação RNE e propagação determinística de `NaR`."

---

### SLIDE 10: Fase 3 — Simulador `zt-sim`, Verificação e Kernels SpMV e ML (`08:00 - 09:05`)
* **Quem fala:** Apresentador 3
* **Onde apontar:** Aponte para as 4 camadas de verificação à esquerda e para o mapeamento de Kernels SpMV e ML à direita.
* **Fala sugerida:**
  > "Na **Fase 3**, validamos o simulador `zt-sim` em quatro camadas rigorosas:
  > 1. Testes exaustivos em `T8` ($3\times 65.536$ pares) e estreitamento `T16->T8` contra aritmética racional exata (`Fraction`), somando **81 checagens C++** e **75 testes Python**.
  > 2. Validação cruzada contra a `libtakum` v2.0.0 em `T8`, `T16` (50.000 casos) e `T32` (30.000 casos).
  > 3. Oráculo de referência `Float128` (`binary128` de 113 bits de mantissa via `libquadmath`) auditado em 6.017 casos.
  > 4. Teste diferencial byte-a-byte contra o **`QEMU 10.2.2`** com `vtype.vill=1` conforme a RVV 1.0 §3.11: **zero divergências nas 9 execuções** e nas **96 execuções de SpMV**.
  > À direita, mostramos como o par `vtdot.vv` + `vncvt.t.t` mapeia diretamente tanto o SpMV CSR quanto **kernels de aprendizado de máquina quantizados** (`GEMV`/`GEMM`, projeções de atenção e redes neurais podadas em 8 e 16 bits), reduzindo o laço por faixa de 12 instruções no `FP32` para 11 instruções no `Takum32`."

---

### SLIDE 11: Fase 3 — Erro Relativo $\ell_2$ em 32 Bits vs. `Float128` (`09:05 - 10:15`)
* **Quem fala:** Apresentador 3
* **Onde apontar:** Aponte para a tabela com as 4 matrizes representativas e a linha `Mediana (8)` e os dois destaques embaixo.
* **Fala sugerida:**
  > "Aqui estão os resultados de precisão em 32 bits frente ao `Float128` nas matrizes Harwell-Boeing.
  > Com o acumulador `T64` do `vtdot.vv`, o `Takum32` atinge erro relativo mediano de $2{,}51 \times 10^{-8}$ contra $3{,}87 \times 10^{-8}$ do `FP32` — uma redução de **1,54×** na mediana geral, vencendo em 6 das 8 matrizes sem escala e em **8 de 8 matrizes sob `pow2-bound`**.
  > Mesmo quando isolamos apenas o formato com acumulador de 32 bits (`Takum32 (32b)`), o Takum reduz o erro em **1,42×** sobre o `FP32` graças aos 28 bits de precisão perto da unidade. E frente ao `Posit32,2`, embora o Posit vença em matrizes de faixa moderada, o `Takum32` é ordens de grandeza mais preciso em matrizes de faixa ampla como `bcsstk01` ($5{,}06 \times 10^{-8}$ vs. $3{,}65 \times 10^{-7}$) e `pores_1`."

---

### SLIDE 12: Fase 3 — Baixa Precisão (8 e 16 Bits), Posits e Reescalonamento (`10:15 - 11:15`)
* **Quem fala:** Apresentador 4
* **Onde apontar:** Aponte para os três pontos à esquerda e para as curvas CDF à direita (painel (a) SpMV HB e painel (b) SuiteSparse-100).
* **Fala sugerida:**
  > "Quando descemos para 8 e 16 bits — o regime crítico de inferência de ML e aceleradores esparsos — vemos a diferença entre sobreviver ou quebrar:
  > - Sem reescalonamento (`none`), o `OFP8 E4M3` estoura com `NaN` em **4 de 8 matrizes**, e o `E5M2` e o `FP16` estouram em **3 de 8 matrizes** (por isso as curvas deles no painel (a) da CDF estagnam abaixo de $1{,}0$).
  > - Já o **`Takum8` e o `Takum16` têm zero falhas não-finitas (0/8)** sem nenhum pré-escalonamento!
  > - Em 16 bits sem escala, o `Takum16` reduz o erro mediano em **2,26× sobre o `bfloat16`** (vencendo em 7 de 8 matrizes). Em 8 bits, o `Posit8,2` tem menor erro em matrizes próximas da unidade (7/8), enquanto o `Takum8` sacrifica fração local em troca de jamais sofrer *overflow* até $\pm 10^{72}$."

---

### SLIDE 13: Resultados — 15 Formatos em 100 Matrizes SuiteSparse e Custo RVV (`11:15 - 12:10`)
* **Quem fala:** Apresentador 4
* **Onde apontar:** Aponte para a coluna da esquerda (100 matrizes SuiteSparse + modelo analítico $N = rR + cS + K$) e depois para o gráfico de barras à direita.
* **Fala sugerida:**
  > "Ampliando para **100 matrizes da SuiteSparse** avaliadas em 15 formatos contra referência de 80 bits (`long double`), vemos que a queda exponencial de precisão do Posit nas caudas leva o erro máximo do `Posit16` a **99,9%** (contra apenas **0,85%** no `Takum16`) e do `Posit32` a $1{,}59 \times 10^{-4}$ (contra $5{,}42 \times 10^{-8}$ no `Takum32`).
  > No custo arquitetural RVV à direita, nosso modelo analítico fechado $N_f = r_f R + c_f S + K$ fecha com **resíduo zero nas 24 execuções reais** do simulador:
  > - Como $N_{\text{Takum32}} - N_{\text{FP32}} = R - S \le 0$, o `Takum32` **nunca executa mais instruções que o `FP32`** (é menor em 20 de 24 pares e igual em 4), mantém exatamente as mesmas escritas em CSR (`0,309/nnz`) e **reduz em 15,6% os elementos vetoriais ativos por não nulo**!
  > - Em `T8` e `T16`, o maior empacotamento por registrador vetorial reduz as instruções totais em **6,0% a 7,0%** em `VLEN=128`, com o *trade-off* documentado de $+1$ `vsetvli` por faixa para alternar entre índices de 32 bits e dados estreitos."

---

### SLIDE 14: Conclusão, Limitações e Síntese das Entregas (`12:10 - 12:45`)
* **Quem fala:** Apresentador 4
* **Onde apontar:** Aponte para a síntese das 3 fases, o item de transparência sobre limitações e o link clicável da branch `main`.
* **Fala sugerida:**
  > "Concluindo antes da nossa demonstração ao vivo: entregamos as Fases 1, 2 e 3 completas, com codec de 12 MSBs e ULA de 128 bits, ISA Zvtakum em `custom-0` validada com zero divergências contra o `QEMU 10.2.2`, e avaliação completa de SpMV e kernels de ML contra `Float128` e SuiteSparse-100.
  > Como transparência metodológica, destacamos que o `zt-sim` é um simulador funcional sem modelo de ciclos/RTL e que os baselines de `FP8`/`FP16`/`bfloat16`/`Posit` são avaliados em software sob a mesma ordem de redução. Todo o código e artefatos estão públicos na branch `main` do nosso repositório GitHub. Vamos agora para a demonstração ao vivo no terminal."

---

### SLIDE 15: Demonstração Funcional ao Vivo (Live Demo) (`12:45 - 15:00`)
* **Quem fala:** Apresentador 4 (operando o terminal aberto na raiz do repositório `/var/home/andrerezende/Projects/aoc-takum-riscv`)
* **Roteiro prático no terminal (3 passos rápidos em ~2 minutos):**

#### Passo 1: Testes Unitários C++ (81 checagens) + Python (75 testes) (~40s)
* **Comando no terminal:**
  ```bash
  make test && make sim-test
  ```
* **O que narrar enquanto roda:**
  > "Primeiro, executamos `make test && make sim-test`. Vocês veem passando as **81 verificações em C++20** (`takum-test` com 52 checagens exaustivas `T8` e amostradas `T16`/`T32`, e `zt-test` com 29 checagens das 5 instruções `Zvtakum`, `vtype.vill=1` e *trap* em `custom-0`), seguidas pelos **75 testes unitários em Python** cobrindo codec, Posit, `Float128` e SpMV."

#### Passo 2: Validação Diferencial `zt-sim` vs `QEMU 10.2.2` (~40s)
* **Comando no terminal:**
  ```bash
  make sim-check
  ```
* **O que narrar enquanto roda:**
  > "Segundo, rodamos `make sim-check` (ou `python3 tests/sim/difftest.py`), que executa os binários ELF RISC-V nas três larguras `VLEN` (128, 256 e 512 bits) no `zt-sim` e no **`QEMU 10.2.2`** e compara os *dumps* de saída: **9 de 9 execuções com zero divergências**."

#### Passo 3: Demonstração Funcional SpMV (`bcsstk01`: `Takum32` vs `FP32`) (~45s)
* **Comando no terminal:**
  ```bash
  ./run_all.sh demo
  ```
* **O que narrar ao mostrar o resultado:**
  > "Por fim, rodamos `./run_all.sh demo`, que executa a demonstração funcional ponta-a-ponta da Fase 1 à Fase 3 na matriz `bcsstk01`, mostrando a decodificação dos 12 MSBs, as instruções vetoriais da Zvtakum e a redução do erro relativo e das instruções frente ao `FP32`. E para auditoria completa de reprodutibilidade e limite de 6 páginas do artigo IEEE, o repositório conta com `./run_all.sh --strict`. Muito obrigado! Estamos abertos às perguntas da banca."

---

## 4. Comandos Prontos para Copiar e Colar na Demo

Deixe um terminal aberto na pasta `/var/home/andrerezende/Projects/aoc-takum-riscv` com fonte grande (`Ctrl + +`) e rode na ordem:

```bash
# 1. Testes unitários C++ (81 checks) + Python (75 testes)
make test && make sim-test

# 2. Validação diferencial byte-a-byte zt-sim vs QEMU 10.2.2 (9/9 casos)
make sim-check

# 3. Demo funcional ponta-a-ponta (Fases 1, 2 e 3: bcsstk01 Takum32 vs FP32)
./run_all.sh demo
```

*(Nota de backup para arguição: caso a banca peça para verificar a auditoria completa de artefatos, hashes SHA-256 e limite estrito de 6 páginas dos artigos EN/PT, basta exibir `cat artifacts/manifest.json` ou rodar `./run_all.sh --strict`).*

---

## 5. Guia de Respostas Rápidas para a Arguição (Q&A da Banca)

1. **"Por que vocês escolheram o Takum Linear (Def. 8) em vez do Takum Logarítmico original?"**
   * **Resposta:** O artigo de Hunhold (2024) define ambas as variantes com o mesmo cabeçalho $(S, D, R, C)$. No entanto, em uma arquitetura vetorial SIMD com múltiplas *lanes* paralelas, o Takum Logarítmico exige tabelas de consulta não-lineares (interpolação das curvas Gaussianas $\Delta_+$ e $\Delta_-$) para realizar adições e subtrações no domínio logarítmico. Já o Takum Linear decodifica diretamente para um significando inteiro e reutiliza somadores e multiplicadores inteiros convencionais em cada *lane*. Mesmo assim, incluímos na Seção IV do artigo e no Slide 13 a comparação experimental entre Takum Linear e Logarítmico nas 100 matrizes da SuiteSparse.

2. **"Como funciona exatamente a janela de 12 MSBs no hardware?"**
   * **Resposta:** Em qualquer precisão Takum (`T8` a `T64`), $S$ usa 1 bit, $D$ usa 1 bit, $R$ usa 3 bits e a característica $C$ tem comprimento variável $r \in [0, 7]$ bits. Logo, o deslocamento máximo do cabeçalho é $1 + 1 + 3 + 7 = 12$ bits. Em hardware, isso significa que o circuito decodificador de escala olha **apenas para os 12 bits mais significativos** do elemento (fazendo *zero-padding* de 4 *ghost bits* à direita no caso de `T8`), extraindo $c$ e $p$ em tempo constante $O(1)$ com portas lógicas rasas, diferente do Posit cujo regime unário pode ocupar todos os 32 ou 64 bits da palavra.

3. **"Como vocês garantiram que o simulador `zt-sim` implementa corretamente a ISA RISC-V e a especificação RVV 1.0?"**
   * **Resposta:** Usamos validação diferencial automatizada (`tests/sim/difftest.py`) contra o **`QEMU 10.2.2`** (`qemu-riscv64 -cpu rv64,v=true,vlen=128/256/512`). Inclusive, durante a auditoria identificamos uma sutileza arquitetural importante (Decisão D12): a especificação RVV 1.0 (Seção 3.11) determina que no reset, antes de qualquer `vsetvli`, o CSR `vtype` deve ter `vill=1` (`0x8000000000000000`). Versões antigas do QEMU (como a 8.2.2) inicializavam `vtype=0` em modo usuário, mas o `QEMU 10.2.2` segue a especificação e concorda 100% byte-a-byte com o nosso simulador nas 9 combinações de programas e `VLEN`.

4. **"Qual é a referência exata (*ground truth*) para o cálculo do erro relativo no SpMV?"**
   * **Resposta:** Todas as 96 configurações de SpMV são comparadas contra um oráculo em **precisão quádrupla IEEE 754 `binary128` (`Float128`)**, gerado via `libquadmath` do GCC (`__float128`, com 113 bits de mantissa explícita, cerca de 34 dígitos decimais significativos) e auditado em `tests/data/binary128_cases.jsonl` com 6.017 casos de referência. Já no experimento complementar de conversão estática de 100 matrizes SuiteSparse, o erro de representação elemento-a-elemento é medido contra precisão estendida de 80 bits (`long double`).

5. **"Por que em 8 e 16 bits o número de escritas em CSR aumenta em relação ao FP32?"**
   * **Resposta:** Porque no kernel CSR em 8 e 16 bits (`T8` e `T16`), os índices de coluna da matriz CSR (`col_idx`) têm 32 bits (para suportar matrizes com mais de 65 mil colunas), enquanto os valores têm 8 ou 16 bits. Isso requer alternar o `vtype` via `vsetvli` em cada faixa vetorial entre `SEW=32` (para o índice do *gather*) e `SEW=8/16` (para os dados Takum), adicionando 1 escrita em CSR por faixa. Mesmo assim, em `VLEN=128` o maior empacotamento reduz o número **total de instruções dinâmicas em 6,0% a 7,0%**.

6. **"O Objetivo 4 do edital menciona 'operações de álgebra linear esparsa e kernels de aprendizado de máquina'. Como o projeto atende à parte de aprendizado de máquina?"**
   * **Resposta:** A operação fundamental de inferência em aprendizado de máquina moderno — tanto em camadas densas/lineares (`GEMV`/`GEMM`) e projeções de atenção em *Transformers* quanto em redes neurais esparsas/podadas (*pruned neural networks*) — é o **produto interno quantizado em 8 ou 16 bits com acumulação alargada e requantização**. O par arquitetural que projetamos na Zvtakum (`vtdot.vv` acumulando em $2 \cdot \mathrm{SEW}$: `T8 -> T16`, `T16 -> T32`, seguido de `vncvt.t.t` estreitando com arredondamento RNE para `SEW`) implementa diretamente essa primitiva em hardware. Mais importante: enquanto a quantização `FP8 E4M3` ou `FP16` exige manter e atualizar fatores de escala por tensor ou por canal (`pow2-bound`) para evitar *overflow*/`NaN`, o `Takum8` e o `Takum16` operam diretamente sobre pesos e ativações não reescalonados com 100% de convergência.

7. **"Por que os formatos de comparação (`FP8`, `FP16`, `bfloat16`, `Posit`) foram avaliados no modelo aritmético de referência em Python em vez de instruções nativas no simulador C++?"**
   * **Resposta:** Porque a especificação padrão RVV 1.0 ratificada não inclui instruções nativas para `FP8` (`E4M3`/`E5M2`) nem para `Posit`, e o baseline de contagem de instruções e escritas em CSR depende apenas da estrutura do laço vetorial (`vle`, `vluxei32.v`, `vfmul.vv`, `vfredusum.vs`), que é idêntica para qualquer formato IEEE 754 sem alargamento fundido. Ao avaliar a precisão numérica de todos os formatos sob exatamente a mesma ordem de redução em faixa (`strip-mining` em blocos de `VLEN/SEW` elementos com arredondamento RNE a cada passo), isolamos de forma justa e matematicamente exata a qualidade numérica de cada codificação frente à referência `Float128`.
