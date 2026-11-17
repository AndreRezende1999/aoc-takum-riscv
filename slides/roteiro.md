# Roteiro Completo da Apresentação, Explicação de Conceitos e Storytelling (15 min)

Este documento guia a apresentação oral de **15 minutos** de [`slides/slides.pdf`](slides.pdf) (12 slides), estruturada **exatamente** sobre os requisitos do edital (`ProjectGuidelinesAOC.pdf` — Seções 2, 3, 4.1, 5.1, 5.2, 5.3 e 6.3).

---

## 1. O Arco de Storytelling (Fio Condutor da Apresentação)

Para prender a atenção da banca do início ao fim, a apresentação segue uma narrativa de engenharia em **5 atos**:

1. **O Conflito (Slides 1–2):** Aplicações modernas de IA e álgebra linear esparsa são limitadas por banda de memória, não por ULA. Para comprimir dados em 8 e 16 bits, a indústria criou uma colcha de retalhos de formatos IEEE (`FP16`, `bfloat16`, `OFP8 E4M3/E5M2`). Na extensão vetorial do RISC-V (`RVV 1.0`), isso gera **96 instruções** de ponto flutuante/conversão, exige tratamento de subnormais e prende o pipeline ao registrador `fcsr` (`frm`/`fflags`) — e o `FP8` sequer existe.
2. **A Ideia Matemática e o Hardware da Fase 1 (Slides 3–4):** A aritmética **Takum** resolve a causa raiz: concentra mais bits de mantissa perto de $1.0$ (*tapered precision*), garante faixa dinâmica imensa ($\approx 10^{\pm 72}$ a $10^{\pm 77}$) mesmo em 8 bits e, crucialmente, empacota todo o cabeçalho de escala $(S, D, R, C)$ nos **12 bits mais significativos (12 MSBs)** para *qualquer* largura (`T8`, `T16`, `T32`). Construímos uma ULA em **inteiros de 128 bits** com arredondamento **RNE no espaço de códigos**, evitando `double` do hospedeiro — e provamos por quê: encontramos **128 casos em 30.000** onde a `libtakum` oficial erra por 1 ULP em `T32` devido a duplo arredondamento via `double`.
3. **A Arquitetura `Zvtakum` e as Decisões de Projeto da Fase 2 (Slides 5–7):** Em vez de 96 instruções, bastam **5 instruções vetoriais** (`vtadd.vv`, `vtsub.vv`, `vtmul.vv`, `vtdot.vv`, `vncvt.t.t`) parametrizadas por `vtype.vsew` no espaço **`custom-0` (`0x0B`)**. Acoplamos o subsistema vetorial ao caminho de dados RISC-V sem nenhuma dependência de `fcsr`, e justificamos cada decisão arquitetural considerada (Slide 6/7 — exigência explícita da Seção 4.1 do edital).
4. **A Prova Experimental da Fase 3 (Slides 8–11):** Validamos o simulador `zt-sim` byte a byte contra o **QEMU 10.2.2** e contra um oráculo `Float128` (`libquadmath`). Na multiplicação matriz esparsa–vetor (**SpMV CSR**, $y = A \cdot x$):
   - Em **32 bits**, `Takum32` reduz o erro mediano em **$5.15\times$** frente ao `FP32` (isolando $2.01\times$ puro do formato e $2.56\times$ do acumulador `T64` do `vtdot.vv`).
   - Em **8 e 16 bits**, enquanto `E4M3`, `E5M2` e `FP16` sofrem *overflow* não finito em **3 a 4 das 8 matrizes**, `Takum8` e `Takum16` têm **0 falhas (100% finitos)**, superam `bfloat16` em $3.17\times$ a $7.61\times$ e evitam o colapso de cauda dos `Posits` em 100 matrizes SuiteSparse.
   - Na **contagem de instruções**, nosso modelo analítico $N_f = r_f R + c_f S + K$ crava as 96 execuções com **resíduo zero** e prova algebricamente ($N_{\text{Takum32}} - N_{\text{FP32}} = R - S \le 0$) que `Takum32` **nunca executa mais instruções que `FP32`**.
5. **O Fechamento com Demonstração ao Vivo (Slide 12):** Mostramos no terminal o simulador executando os testes e rodando `bcsstk01` em tempo real, onde a diferença de instruções entre `Takum32` (`1353`) e `FP32` (`1365`) é literalmente $R - S = 48 - 60 = -12$.

---

## 2. Divisão de Tempo Sugerida para 4 Integrantes (15 Minutos)

| Integrante | Slides | Tempo | Escopo Principal |
|---|---|---|---|
| **Apresentador 1 (André)** | Slides 1, 2 e 3 | `00:00 – 03:30` (3,5 min) | Abertura, problema da proliferação IEEE na RVV, objetivos do projeto e Fase 1A (codificação Takum Def. 8 e janela de 12 MSBs). |
| **Apresentador 2 (Gabriel)** | Slides 4, 5 e 6 | `03:30 – 07:00` (3,5 min) | Fase 1B (ULA inteira de 128 bits, RNE no código, achado na `libtakum`) e Fase 2 (as 5 instruções `Zvtakum` em `custom-0` e o Caminho de Dados RISC-V + `Zvtakum`). |
| **Apresentador 3 (João Pedro)** | Slides 7 e 8 | `07:00 – 09:45` (2,75 min) | Opções consideradas, decisões de projeto e justificativas (Seção 4.1 do edital); verificação em 4 camadas (`QEMU`/`Float128`) e estrutura do kernel SpMV CSR. |
| **Apresentador 4 (Isadora)** | Slides 9, 10, 11 e 12 + Demo | `09:45 – 15:00` (5,25 min: 3 min slides + 2,25 min demo) | Resultados em 32 bits (decomposição formato vs. acumulador), 8/16 bits (*overflows* e 100 matrizes SuiteSparse), modelo analítico $N_f = r_f R + c_f S + K$ e **Demo ao vivo no terminal**. |

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
  - Diferença crucial para o **Posit**: o Posit usa código unário para o regime (precisa de um detector de zeros líderes na palavra inteira de 32 bits, e nas escalas extremas a precisão do Posit cai a 1 bit). O Takum limita o cabeçalho a 12 bits, então em `T16` sobram sempre pelo menos 5 bits de precisão nas caudas e até 12 bits perto de $1$, cobrindo $\approx 10^{\pm 77}$!
- **Onde apontar:** Primeiro nas duas equações no topo ($L_{\max} = 12\text{ bits}$ e a fórmula da Definição 8 em complemento de dois) e depois nos 3 gráficos `(a) 8 bits`, `(b) 16 bits` e `(c) 32 bits` (apontar o "platô" verde do Takum vs. a queda laranja do Posit e a parede estreita azul do `FP16`).
- **Fala sugerida:**
  > *"Entrando na Fase 1: como funciona a codificação Takum Linear da Definição 8? Cada número tem 5 campos: sinal $S$, direção $D$, regime $R$ de 3 bits fixos, característica $C$ de $r$ bits e fração $F$. Como $R$ tem 3 bits, o tamanho $r$ varia de 0 a no máximo 7 bits. Isso significa que todo o prefixo de escala $(S, D, R, C)$ ocupa no máximo $1 + 1 + 3 + 7 = 12$ bits mais significativos, não importa se o número é `T8`, `T16` ou `T32`! Para o `T8`, completamos 4 zeros fantasmas à direita e usamos exatamente a mesma fiação de decodificação.*
  > *Além disso, só existem dois padrões especiais: tudo zero para o $0$ e `100...0` para o `NaR` (Not a Real). Não há infinito, não há subnormais e a negação é complemento de dois puro.*
  > *No gráfico abaixo vemos o efeito disso: no painel central (16 bits), o `FP16` (azul) tem precisão alta no centro mas morre em $10^{\pm 5}$; o `bfloat16` (vermelho) chega a $10^{\pm 38}$ mas fica preso em 8 bits; o `Posit16` (laranja) tem pico no centro mas colapsa a zero nas pontas; já o `Takum16` (verde) entrega 12 bits perto de $1$ e mantém um piso de 5 bits até $10^{\pm 77}$."*

---

### SLIDE 4 — 3. Fase 1: ULA Takum em Inteiros de 128 Bits e RNE no Código (`03:30 – 05:00`)
- **Conceito técnico chave (para dominar):**
  - Na Fase 1, poderíamos ter simplesmente chamado `double` do C++ para somar e multiplicar. Por que não fizemos isso? Porque `T32` (e o acumulador `T64`) têm casos de meio-ponto onde converter para `double` (53 bits) arredonda uma primeira vez, e converter para Takum arredonda uma segunda vez (**duplo arredondamento**)!
  - Nossa ULA em `src/takum.cpp` desempacota qualquer Takum na tupla exata $(-1)^{\mathrm{neg}} \cdot \mathrm{sig} \cdot 2^{e-63}$ usando inteiros de 64 e 128 bits (`unsigned __int128`).
  - O arredondamento Takum é **RNE no espaço de códigos** (e não no espaço de valores reais): montamos a cadeia infinita de bits $(D, R, C, F)$, olhamos o prefixo de $n$ bits ($L$), o bit $n+1$ ($m$, meio-ponto) e o *OR* de todos os bits seguintes ($st$, *sticky*). Somamos $1$ ao código $L$ se e só se $m=1$ e $(st=1 \text{ ou } L \text{ é ímpar})$.
- **Onde apontar:** Nos três blocos do slide: tupla em `__int128`, regra booleana $L \to L+1$, e o destaque das **128/30.000 divergências** contra a `libtakum`.
- **Fala sugerida:**
  > *"Para implementar as operações aritméticas fundamentais da Fase 1 — adição, subtração, multiplicação, passo de produto escalar e estreitamento — projetamos uma ULA em C++17 operando estritamente com inteiros de 64 e 128 bits (`__int128`), sem tocar em `double` do hospedeiro.*
  > *Cada operando vira uma tupla exata $(\mathrm{neg}, e, \mathrm{sig})$. Na soma e subtração, alinhamos os significandos em 128 bits preservando o bit *sticky*, que também atua como *borrow* na subtração efetiva; na multiplicação, calculamos o produto inteiro exato de 128 bits.*
  > *Na saída, implementamos o arredondamento RNE diretamente no espaço de códigos, como especifica o codec VHDL de Hunhold: extraímos o prefixo $L$ de $n$ bits, o bit $n+1$ de meio-ponto $m$ e o *sticky* $st$, incrementando $L$ quando $m=1$ e há resto ou $L$ é ímpar, saturando em $[\mathrm{minpos}, \mathrm{maxpos}]$.*
  > *Essa decisão se provou fundamental: ao testar nossa ULA contra a biblioteca oficial `libtakum` v2.0.0, batemos 100% nos 196.608 pares de `T8` e 50.000 de `T16`, mas encontramos 128 casos em 30.000 no `T32` em que a `libtakum` diverge por 1 ULP porque ela usa um `double` intermediário que sofre duplo arredondamento em cima da fronteira de empate. Nossa ULA de 128 bits preserva a direção exata."*

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

### SLIDE 7 — 6. Opções Consideradas, Decisões de Projeto e Justificativas (`07:00 – 08:25`)
- **Conceito técnico chave (para dominar):**
  - Este slide atende diretamente à **Seção 4.1 do Edital**, que pede explicitamente para expor *as opções de projeto consideradas, as decisões tomadas e a justificativa para cada uma*.
  - São 5 decisões estruturais:
    1. **Takum Linear (Def. 8) vs. Logarítmico (Def. 2):** Avaliamos ambos (inclusive medimos o fechamento multiplicativo no repositório). Embora o logarítmico transforme multiplicação em soma inteira, sua adição exige tabelas ROM não lineares ($\Delta_\pm$). O Linear mantém somadores e multiplicadores inteiros diretos no pipeline SIMD.
    2. **`custom-0` (`0x0B`) vs. `OP-V` (`0x57`):** Um rascunho inicial tentava usar `OP-V` dizendo que `funct6=111001` era o único livre. Auditamos o `riscv-opcodes` e vimos que há de 11 a 33 `funct6` livres por classe e alto risco de colisão futura. Migramos para `custom-0`, espaço oficial da Fundação RISC-V para extensões customizadas.
    3. **Inteiros de 128 bits vs. `double`:** Elimina o duplo arredondamento em `T32`.
    4. **Acúmulo escalar `vd[0]` em `2·SEW` (`EMUL=1`) vs. Vetores `T64`:** Permite que `vtdot.vv` acumule produtos `T32` em `T64` sem precisar implementar aritmética vetorial completa de 64 bits nem dobrar o `LMUL` dos operandos de entrada.
    5. **Sem `fcsr`:** RNE fixo no código + saturação em `maxpos`/`minpos` + `NaR` eliminam `frm` e a redução em árvore de `fflags`.
- **Fala sugerida:**
  > *"Conforme solicitado nas diretrizes do projeto, sintetizamos nesta tabela as cinco principais decisões arquiteturais onde avaliamos alternativas antes de fechar o design:*
  > *Primeiro, entre Takum Logarítmico e Linear, escolhemos o Linear da Definição 8 porque dispensa tabelas não lineares $\Delta_\pm$ na adição e se encaixa direto em ULAs inteiras SIMD.*
  > *Segundo, em vez de poluir o opcode padrão `OP-V`, nossa auditoria no `riscv-opcodes` motivou a alocação limpa em `custom-0` (`0x0B`), evitando conflito com futuras extensões oficiais.*
  > *Terceiro, trocamos o intermediário `double` por inteiros de 128 bits para eliminar o duplo arredondamento em `T32`.*
  > *Quarto, definimos o `vtdot.vv` acumulando no escalar `vd[0]` com largura dupla `2·SEW` (`EMUL=1`), o que nos dá acumulação `T64` para operandos `T32` sem exigir registradores vetoriais de 64 bits.*
  > *E quinto, eliminamos a dependência de `fcsr`, já que o arredondamento RNE é determinístico e não existem exceções de overflow para infinito."*

---

### SLIDE 8 — 7. Fase 3: Simulador `zt-sim`, Verificação e Kernel SpMV CSR (`08:25 – 09:45`)
- **Conceito técnico chave (para dominar):**
  - Como garantir que nosso simulador `zt-sim` (que executa binários ELF64 reais de RISC-V) não tem bugs? Criamos 4 barreiras de verificação:
    1. Tabelas exaustivas de `T8` ($3 \times 65.536$ pares + $65.536$ *narrowings*) contra modelo racional exato (`Fraction` em Python).
    2. Confronto com a `libtakum` v2.0.0.
    3. Validação do nosso oráculo `Float128` (`binary128`, 113 bits de mantissa) contra `__float128`/`libquadmath` do GCC em 6.017 testes.
    4. **Teste diferencial byte a byte contra o `QEMU 10.2.2`** em $\mathrm{VLEN} \in \{128, 256, 512\}$ para instruções escalares e RVV 1.0 padrão, e contra o modelo Python nas **96 execuções do kernel SpMV CSR**.
  - Na direita do slide: mostrar a diferença cirúrgica entre o laço interno `FP32` (usa `vfmul.vv` + `vfredusum.vs` = 12 instruções por faixa) e o laço `Takum32` (funde os dois num único `vtdot.vv` = 11 instruções por faixa, e faz 1 `vncvt.t.t` só ao terminar a linha inteira!).
- **Fala sugerida:**
  > *"Entrando na Fase 3, construímos o simulador funcional `zt-sim` em C++17 capaz de carregar binários ELF64 RISC-V reais, executar `RV64IM`, `Zicsr`, `RVV 1.0` e `Zvtakum`, e instrumentar contadores detalhados. Para garantir zero erros, validamos o sistema em quatro camadas: testes exaustivos em `T8` contra racionais exatos, confronto com a `libtakum`, validação do nosso oráculo `Float128` contra a `libquadmath` do GCC em 6.017 casos, e teste diferencial byte a byte contra o `QEMU 10.2.2` em três larguras de vetor (`VLEN` 128, 256 e 512).*
  > *Com o simulador validado, implementamos o kernel de multiplicação matriz esparsa por vetor (SpMV CSR, $y = A \cdot x$) sobre oito matrizes clássicas da coleção Harwell–Boeing. Reparem na coluna da direita a diferença no laço de *strip-mining*: enquanto o `FP32` precisa de `vfmul.vv` seguido de `vfredusum.vs` em toda faixa (12 instruções por faixa), o `Takum32` funde multiplicação e acumulação em um único `vtdot.vv` (11 instruções por faixa) e executa apenas um `vncvt.t.t` ao final da linha."*

---

### SLIDE 9 — 8. Resultado 1: Erro Relativo $\ell_2$ em 32 Bits vs. `Float128` (`09:45 – 10:50`)
- **Conceito técnico chave (para dominar):**
  - Quando comparamos o kernel simulado `FP32` (mediana $5.91 \times 10^{-8}$) com o kernel `Takum32` (mediana $1.15 \times 10^{-8}$), o `Takum32` é **$5.15\times$ mais preciso** e vence em **7 das 8 matrizes** (a única exceção é `pores_1`, cujos coeficientes cruzam regimes onde a precisão do Takum já caiu abaixo de 24 bits).
  - Mas um avaliador atento poderia perguntar: *"Esse ganho de $5.15\times$ veio do formato Takum32 ou veio porque o `vtdot.vv` acumula em 64 bits (`T64`) enquanto o `FP32` acumulou em 32 bits?"*
  - Nós isolamos as duas variáveis na tabela!
    - Forçando **acumulador de 32 bits nos dois** (`FP32 ac. 32b` vs. `Takum32 ac. 32b`), o `Takum32` cai para $2.94 \times 10^{-8}$ e continua vencendo em **7 das 8 matrizes**, um ganho puro de **$2.01\times$ só do formato** (graças aos até 28 bits de significando perto de $1$).
    - E dando **acumulador de 64 bits para os dois** (`FP32 ac. 64b` vs. `Takum32 ac. 64b`), o `Takum32` vence por **$3.15\times$**. Ou seja: $5.15\times = 2.01\times (\text{formato}) \times 2.56\times (\text{acumulador})$.
- **Onde apontar:** Na linha `Mediana` da tabela (comparando as colunas `5.91e-8`, `1.15e-8`, `2.94e-8` e `5.37e-9`).
- **Fala sugerida:**
  > *"Vamos ao primeiro grande resultado experimental: a acurácia da SpMV em 32 bits medida contra nosso oráculo de precisão quádrupla `Float128`. O kernel RVV `FP32` obtém erro relativo mediano de $5.91 \times 10^{-8}$, enquanto o kernel `Takum32` atinge $1.15 \times 10^{-8}$ — uma redução de $5.15\times$ no erro mediano, vencendo em 7 das 8 matrizes.*
  > *Para fazer uma análise científica rigorosa, separamos nas colunas de controle o que vem do formato e o que vem do acumulador de 64 bits do `vtdot.vv`: quando restringimos ambos a um acumulador de 32 bits (quarta coluna numérica), o `Takum32` ainda vence em 7 de 8 matrizes com erro $2.01\times$ menor que o `FP32`, e quando damos acumulador de 64 bits a ambos, o `Takum32` é $3.15\times$ mais preciso graças aos seus 28 bits de significando perto da unidade. Com pré-escalonamento `pow2-bound`, o erro cai para $5.37 \times 10^{-9}$, vencendo nas 8 matrizes."*

---

### SLIDE 10 — 9. Resultado 2: 8/16 Bits, Overflows e 100 Matrizes SuiteSparse (`10:50 – 11:55`)
- **Conceito técnico chave (para dominar):**
  - Em 8 e 16 bits sem pré-escalonamento (`none`), formatos com expoente curto colapsam: `OFP8 E4M3` produz linhas não finitas (`NaN`/`Inf`) em **4 das 8 matrizes** (`bcsstk01`, `bcsstk02`, `pores_1`, `west0132`), e `E5M2` e `FP16` estouram em **3 das 8**. No gráfico CDF `(a)` à esquerda, veja que as curvas pontilhadas de `FP16 (s/ esc.)`, `E4M3` e `E5M2` **batem num teto abaixo de 0.6** (não chegam a 1.0 porque mais de 40% das linhas estouraram!).
  - Já `Takum8`, `Takum16` e `bfloat16` chegam a **100% de linhas finitas (0/8 falhas)**!
  - E entre os que não estouram em 16 bits, `Takum16` ($7.43 \times 10^{-4}$) é **$3.17\times$ mais preciso que `bfloat16`** ($2.36 \times 10^{-3}$) sem escala e **$7.61\times$ mais preciso** com escala `pow2-bound` (vencendo 8/8).
  - No gráfico `(b)` à direita (100 matrizes SuiteSparse com `Posit` e `Takum Logarítmico`), vemos que embora o `Posit16` vá bem perto de $1$, na cauda ele chega a **99.9% de erro**, contra apenas **0.85%** no `Takum16`.
- **Onde apontar:** No platô truncado das curvas vermelhas/azuis no gráfico `(a)` vs. as curvas contínuas de `Takum16` e `Takum32` chegando a `1.0`, e na cauda direita do gráfico `(b)`.
- **Fala sugerida:**
  > *"Em 8 e 16 bits, o resultado mais marcante aparece no gráfico de distribuição acumulada (CDF) à esquerda, que reúne 74.074 avaliações de linhas: sem pré-escalonamento em software, o `E4M3` sofre *overflow* em 4 das 8 matrizes, e o `E5M2` e o `FP16` estouram em 3 das 8 — por isso as curvas deles param perto de 0.55 e nunca chegam a 1.0.*
  > *Em contrapartida, `Takum8` e `Takum16` têm zero falhas (100% finitos em todas as matrizes). Comparado ao `bfloat16`, que também não estoura, o `Takum16` reduz o erro mediano em $3.17\times$ sem escala e em $7.61\times$ com escala `pow2-bound`, pois entrega de 10 a 12 bits significativos perto de 1 contra 8 fixos do `bfloat16`. E no painel da direita, em 100 matrizes do SuiteSparse, mostramos que o `Takum` evita o colapso catastrófico de cauda do `Posit16`, cujo erro máximo chega a 99.9% contra 0.85% no `Takum16`."*

---

### SLIDE 11 — 10. Resultado 3: Contagem de Instruções, CSRs e Modelo Analítico (`11:55 – 12:50`)
- **Conceito técnico chave (para dominar):**
  - Ajustamos um modelo linear analítico exato para o número dinâmico de instruções do kernel SpMV:
    $$N_f = r_f \cdot R + c_f \cdot S + K$$
    onde $R$ é o número de linhas da matriz, $S$ é o número total de faixas (*strips*) não vazias e $K = 21$ é o prólogo/epílogo escalar.
  - Esse modelo reproduz todas as **96 execuções reais no simulador com resíduo máximo igual a ZERO**!
  - Olhe para os coeficientes medidos:
    - `FP32`: $r = 13$ instruções por linha, $c = 12$ instruções por faixa.
    - `Takum32`: $r = 14$ instruções por linha (+1 por causa do `vncvt.t.t` ao fim da linha), $c = 11$ instruções por faixa ($-1$ porque o `vtdot.vv` funde `vfmul.vv` e `vfredusum.vs`).
  - Subtraindo um do outro:
    $$N_{\text{Takum32}} - N_{\text{FP32}} = (14 - 13)R + (11 - 12)S = R - S \le 0$$
    Como toda linha não vazia tem pelo menos uma faixa ($S \ge R$ nas matrizes sem linhas vazias), provamos matematicamente que o **`Takum32` nunca executa mais instruções que o `FP32`** (nas 24 execuções, são 13 com estritamente menos instruções e 11 com o mesmo número), com **exatamente o mesmo número de escritas em CSR** (`1.07`/nnz em `VLEN=256`) e **15.6% menos elementos vetoriais ativos processados** (`4.50` vs. `5.33`/nnz)!
  - Em `T8` e `T16`, como os índices de coluna do CSR são de 32 bits (`vluxei32`), é preciso alternar `vtype` entre 32 bits (para o índice) e 8/16 bits (para o dado), o que custa +1 `vsetvli` por faixa; mesmo assim, em `VLEN=128`, cabem 2 a 4 vezes mais elementos por faixa, reduzindo o total de instruções em **$-19.3\%$ (`T16`)** e **$-26.6\%$ (`T8`)**.
- **Onde apontar:** Na equação $N_{\text{Takum32}} - N_{\text{FP32}} = R - S \le 0$ e nos 3 gráficos de barras `(a) Instruções`, `(b) Escritas CSR` e `(c) Elementos Ativos` (`5.33` caindo para `4.50`).
- **Fala sugerida:**
  > *"Por fim, avaliamos o impacto arquitetural na contagem de instruções e acessos a CSRs. Derivamos o modelo analítico $N_f = r_f R + c_f S + K$, que crava todas as 96 execuções do simulador com resíduo zero.*
  > *Para o `FP32`, cada linha custa $r=13$ instruções e cada faixa custa $c=12$. Para o `Takum32`, o `vncvt.t.t` adiciona 1 instrução por linha ($r=14$), mas o `vtdot.vv` economiza 1 instrução por faixa ($c=11$) ao fundir multiplicação e redução. Logo, a diferença exata é $N_{\text{Takum32}} - N_{\text{FP32}} = R - S \le 0$: o `Takum32` executa menos ou igual número de instruções nos 24 pares testados, realiza exatamente o mesmo número de escritas em CSR que o `FP32` e reduz em 15.6% os elementos vetoriais ativos processados pelas lanes, caindo de 5.33 para 4.50 por não nulo.*
  > *Em 8 e 16 bits, o gather de índices de 32 bits exige alternar o `vtype` uma vez por faixa, aumentando as escritas de CSR, mas em `VLEN=128` o maior empacotamento por registrador reduz o total de instruções em 19.3% no `Takum16` e 26.6% no `Takum8`."*

---

### SLIDE 12 — 11. Conclusão e Demonstração Funcional ao Vivo (`12:50 – 15:00`)
- **Fala sugerida (fechamento dos slides + transição para o terminal):**
  > *"Em conclusão, entregamos toda a cadeia proposta no edital: a especificação e o núcleo Takum de 128 bits, a extensão `Zvtakum` em `custom-0` com caminho de dados RISC-V completo sem dependências de `fcsr`, os artigos no padrão IEEE e um script único (`scripts/run_all.py`) que reproduz todos os testes e gráficos. Agora vou passar para o terminal para fazermos a demonstração funcional ao vivo do simulador."*

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
  - `Ran 18 tests in ~1.3s — OK` (`unittest` em Python: modelo exato `Fraction`, confronto exaustivo com `libtakum` v2.0.0 e formatos IEEE/OFP8/bfloat16).
  - `21 verificações, 0 falhas` (`zt-test`: instruções vetoriais `Zvtakum`, `narrow T16->T8` e `vtdot`).

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
- **O que apontar para a banca (momento "uau" da demo!):**
  1. **`insn_total`: `1353` (`Takum32`) vs. `1365` (`FP32`)** $\rightarrow$ A matriz `bcsstk01` tem $R = 48$ linhas e, em $\mathrm{VLEN}=256$, $S = 60$ faixas. Pelo nosso teorema $N_{\text{Takum32}} - N_{\text{FP32}} = R - S = 48 - 60 = -12$. E quanto é $1353 - 1365$? **Exatamente $-12$ instruções!**
  2. **`insn_zvtakum`: `108`** $\rightarrow$ São exatamente as $60$ instruções `vtdot.vv` (uma por faixa) mais as $48$ instruções `vncvt.t.t` (uma ao fim de cada linha): $60 + 48 = 108$!
  3. **`csr_writes`: `312` nos dois** $\rightarrow$ Zero sobrecarga de CSR em 32 bits!
  4. **`elem_active`: `1744` (`Takum32`) vs. `2096` (`FP32`)** $\rightarrow$ Redução de 352 elementos ativos processados pelas vias vetoriais porque o `vtdot.vv` funde multiplicação e redução em uma única passagem!

---

## 5. Guia Rápido de Respostas para Perguntas da Banca (Q&A)

1. **"Por que vocês escolheram o espaço `custom-0` (`0x0B`) em vez de colocar no `OP-V` (`0x57`) junto com a RVV padrão?"**
   - **Resposta:** Fizemos um levantamento automatizado no repositório oficial `riscv-opcodes` e verificamos que existen entre 11 e 33 códigos `funct6` livres em `OP-V` dependendo da classe de operando, que a RISC-V International reserva para futuras extensões padronizadas (como criptografia e matrizes). Usar `custom-0` (`0x0B`, `funct3=000`) segue a convenção oficial da arquitetura RISC-V para extensões não padronizadas sem risco de colisão de binários.

2. **"Por que o `Takum8` teve erro alto (0.64 a 1.21) em algumas matrizes como `bcsstk01` e `west0132` sem reescalamento?"**
   - **Resposta:** Porque essas matrizes têm entradas de rigidez na casa de $10^6$ a $10^9$ ($|e| \ge 15$). Em `T8` ($n=8$), como 5 bits vão para $(S, D, R)$ e o regime $r$ cresce para representar expoentes grandes, quando $|e| \ge 15$ temos $r \ge 3$ e restam $p = 8 - 5 - 3 = 0$ bits de fração (os 4 *ghost bits* truncam a característica). Ou seja, em `T8` extremo ele preserva a ordem de grandeza sem estourar para `NaN`/`Inf` (diferente do `E4M3` que falha totalmente), e quando aplicamos `pow2-bound` o erro mediano do `Takum8` cai para $8.39 \times 10^{-2}$, empatando em 4–4 com o `E5M2`.

3. **"Como funciona o arredondamento no espaço de códigos e por que ele difere do arredondamento no espaço de valores?"**
   - **Resposta:** No IEEE 754, dentro de um mesmo expoente, os números são igualmente espaçados (linear), então o ponto médio entre dois códigos consecutivos tem o mesmo valor aritmético. No Takum, quando $p=0$ (fronteira onde a característica $C$ é truncada no `T8`), dois códigos consecutivos representam potências de 2 distantes por um fator (ex.: código 1 é $2^{-239}$ e código 2 é $2^{-223}$). Olhando para os bits do código antes de truncar, o bit de meio-ponto $m=1$ corresponde à média geométrica $2^{-231}$ (e não à média aritmética). Arredondar pelo bit $m$ no espaço de códigos economiza um comparador aritmético completo em hardware e segue exatamente a especificação VHDL de Hunhold.

4. **"Por que em 8 e 16 bits o número de escritas em CSR aumenta em relação ao `FP32`?"**
   - **Resposta:** Porque no formato CSR as colunas (`col_idx`) são inteiros de 32 bits (`uint32_t`). Quando os valores da matriz estão em `T32` ou `FP32`, tanto o índice quanto o dado têm 32 bits (`SEW=32`), então basta um único `vsetvli` por faixa. Já quando os dados estão em `T8` ou `T16`, para carregar $vl$ índices de 32 bits sem truncar endereços de coluna acima de 65.535, o kernel faz um `vsetvli` para ajustar o `EMUL` do índice e outro para voltar ao `SEW` de 8 ou 16 bits. Ainda assim, em `VLEN=128`, cabem 2 a 4 vezes mais elementos por faixa, o que reduz o número total de instruções executadas em $-19.3\%$ (`T16`) e $-26.6\%$ (`T8`).
