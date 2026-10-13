# Núcleo Takum da Fase 1 (T8/T16/T32): compilação, testes e vetores dourados.
#
#   make ou make build   compila build/takum-test
#   make test            compila e roda os testes C++ e os testes Python
#   make golden          regenera tests/golden/ a partir do modelo Python
#   make clean           remove build/
#
# Requisitos: g++ (C++17) e python3 (3.10+); apenas biblioteca padrão.

CXX      ?= c++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra -Werror -ffp-contract=off
CPPFLAGS += -Iinclude

PYTHON ?= python3
BUILD  := build
LIB_SRC := src/takum.cpp
LIB_OBJ := $(LIB_SRC:src/%.cpp=$(BUILD)/%.o)

all: build

build: $(BUILD)/takum-test

$(BUILD)/%.o: src/%.cpp include/*.hpp
	@mkdir -p $(@D)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c -o $@ $<

$(BUILD)/takum-test: tests/test_main.cpp $(LIB_OBJ) include/takum.hpp
	@mkdir -p $(@D)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -DZT_GOLDEN_DIR='"tests/golden"' -o $@ tests/test_main.cpp $(LIB_OBJ)

test: build
	@echo "== testes C++ (vetores dourados) =="
	./$(BUILD)/takum-test
	@echo "== testes Python (modelo de referência) =="
	cd python && $(PYTHON) -B -m unittest discover -s tests -v

golden:
	$(PYTHON) -B tests/gen_golden.py

clean:
	rm -rf $(BUILD)

.PHONY: all build test golden clean
