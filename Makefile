# Projeto Integrador: núcleo Takum da Fase 1 e simulador Zvtakum da Fase 2.
#
# Requisitos: C++17, Python 3.10+, e para sim-check/paper os toolchains
# correspondentes. Ver README.md e os READMEs dos diretórios.

CXX      ?= c++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra -Werror -ffp-contract=off
CPPFLAGS += -Iinclude
PYTHON   ?= python3
BUILD    := build
LIB_OBJ  := $(BUILD)/takum.o
SIM_OBJ  := $(BUILD)/machine.o

all: build

build: $(BUILD)/takum-test

$(BUILD)/takum.o: src/takum.cpp include/takum.hpp
	@mkdir -p $(@D)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c -o $@ $<

$(BUILD)/takum-test: tests/test_main.cpp $(LIB_OBJ) include/takum.hpp
	@mkdir -p $(@D)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -DZT_GOLDEN_DIR='"tests/golden"' -o $@ tests/test_main.cpp $(LIB_OBJ)

$(BUILD)/machine.o: src/machine.cpp include/zt/machine.hpp include/takum.hpp include/zt/takum.hpp
	@mkdir -p $(@D)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c -o $@ $<

$(BUILD)/zt-sim: src/main.cpp $(SIM_OBJ) $(LIB_OBJ)
	@mkdir -p $(@D)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -o $@ src/main.cpp $(SIM_OBJ) $(LIB_OBJ)

$(BUILD)/zt-test: tests/sim/test_main.cpp $(SIM_OBJ) $(LIB_OBJ)
	@mkdir -p $(@D)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -DZT_GOLDEN_DIR='"tests/sim/golden"' -o $@ tests/sim/test_main.cpp $(SIM_OBJ) $(LIB_OBJ)

test: build
	@echo "== testes C++ (vetores dourados) =="
	./$(BUILD)/takum-test
	@echo "== testes Python (modelo de referência) =="
	cd python && $(PYTHON) -B -m unittest discover -s tests -v

golden:
	$(PYTHON) -B tests/gen_golden.py

sim: $(BUILD)/zt-sim

sim-test: $(BUILD)/zt-test
	./$(BUILD)/zt-test

sim-check: sim
	$(PYTHON) tests/sim/gen_asm.py
	$(PYTHON) tests/sim/gen_zvt.py
	$(PYTHON) tests/sim/difftest.py

spmv: sim
	$(PYTHON) kernels/spmv.py
	$(PYTHON) kernels/numeric_baselines.py
	$(PYTHON) kernels/modelo_contagem.py

paper-data:
	$(PYTHON) paper/gera_tabelas.py
	$(PYTHON) paper/gera_figuras.py

paper:
	cd paper && latexmk -pdf -interaction=nonstopmode main.tex

slides:
	cd slides && latexmk -pdf -interaction=nonstopmode slides.tex

clean:
	rm -rf $(BUILD)

.PHONY: all build test golden sim sim-test sim-check spmv paper-data paper slides clean
