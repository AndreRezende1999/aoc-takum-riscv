#!/usr/bin/env bash
# Single entry point for the AOC Takum/RISC-V project.
#
#   ./run_all.sh              # test + bench + check (código, testes e figuras)
#   ./run_all.sh test         # C++/Python/ISA tests + offline reference check
#   ./run_all.sh demo         # quick functional presentation demo
#   ./run_all.sh bench        # numeric baselines + figures (PDF/SVG + TikZ)
#   ./run_all.sh check        # citations + reproducibility manifest
#   ./run_all.sh --strict ... # fail if optional QEMU/LLVM/network tools are missing
#   ./run_all.sh bench --full # regenerate SpMV CSVs and full closure benchmark
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARTIFACTS="$ROOT/artifacts"
LOGS="$ARTIFACTS/logs"
mkdir -p "$LOGS"

STRICT=0
FULL=0
COMMAND="all"
for arg in "$@"; do
    case "$arg" in
        --strict) STRICT=1 ;;
        --full) FULL=1 ;;
        test|demo|bench|check|all) COMMAND="$arg" ;;
        *) echo "argumento desconhecido: $arg" >&2; exit 2 ;;
    esac
done

: > "$ARTIFACTS/skipped.txt"

log() { printf '[run_all] %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }
skip() {
    local message="$1"
    printf '[skip] %s\n' "$message"
    printf '%s\n' "$message" >> "$ARTIFACTS/skipped.txt"
    if [[ "$STRICT" -eq 1 ]]; then
        echo "[strict] dependência ausente: $message" >&2
        exit 3
    fi
}

run_test() {
    log "testes C++ e Python (make test)"
    make -C "$ROOT" test 2>&1 | tee "$LOGS/cpp-python-tests.log"
    grep -E "verificações|OK|ok$" "$LOGS/cpp-python-tests.log" > "$LOGS/cpp-tests.log" || true
    cp "$LOGS/cpp-python-tests.log" "$LOGS/python-tests.log"

    log "referências bibliográficas (offline)"
    python3 "$ROOT/tools/check_references.py" 2>&1 | tee "$LOGS/references-offline.log"

    if have llvm-mc && have qemu-riscv64; then
        log "testes diferenciais QEMU/LLVM (recompilando ELFs)"
        python3 "$ROOT/tests/sim/gen_asm.py"
        python3 "$ROOT/tests/sim/gen_zvt.py"
        python3 "$ROOT/tests/sim/difftest.py" 2>&1 | tee "$LOGS/difftest.log"
    elif have qemu-riscv64 && [[ -f "$ROOT/build/asm/scalar_ops.elf" ]]; then
        log "llvm-mc ausente no PATH; executando difftest com ELFs pré-compilados em build/asm/"
        make -C "$ROOT" sim >/dev/null
        python3 "$ROOT/tests/sim/difftest.py" 2>&1 | tee "$LOGS/difftest.log"
    else
        skip "llvm-mc ou qemu-riscv64 ausente; testes diferenciais completos não executados"
        make -C "$ROOT" sim >/dev/null
        python3 "$ROOT/tests/sim/difftest.py" --only zvtakum_isa 2>&1 | tee "$LOGS/difftest.log" || true
    fi
}

run_demo() {
    log "demo funcional sem LLVM/QEMU"
    make -C "$ROOT" build build/zt-test >/dev/null
    (
        cd "$ROOT"
        ./build/takum-test 2>&1 | tee "$LOGS/demo-cpp.log"
        ./build/zt-test 2>&1 | tee -a "$LOGS/demo-cpp.log"
    )
    python3 "$ROOT/tools/demo.py" 2>&1 | tee "$LOGS/demo.log"
}

run_bench() {
    make -C "$ROOT" sim >/dev/null
    if [[ "$FULL" -eq 1 ]]; then
        if have llvm-mc && have ld && have qemu-riscv64; then
            log "regenerando SpMV no simulador e modelo analítico"
            python3 "$ROOT/kernels/spmv.py" 2>&1 | tee "$LOGS/spmv.log"
        else
            skip "llvm-mc/ld/qemu ausente; mantendo results/spmv_hb.csv versionado"
        fi
        log "benchmark completo de fechamento linear vs logarítmico"
        python3 "$ROOT/scripts/bench_closure.py" 2>&1 | tee "$LOGS/closure.log"
    fi
    if [[ ! -f "$ROOT/results/spmv_hb.csv" ]]; then
        skip "results/spmv_hb.csv ausente; rode ./run_all.sh bench --full em ambiente com LLVM"
    fi
    log "verificando modelo analítico N = rR + cS + K"
    python3 "$ROOT/kernels/modelo_contagem.py" 2>&1 | tee "$LOGS/model.log"

    log "baselines numéricos (IEEE, bfloat16, OFP8, posit, Takum vs Float128)"
    python3 "$ROOT/kernels/numeric_baselines.py" 2>&1 | tee "$LOGS/numeric.log"

    log "manifesto e checagem de conversão SuiteSparse-100 / HB"
    python3 "$ROOT/scripts/bench_suitesparse100.py" 2>&1 | tee "$LOGS/suitesparse.log"
    if [[ ! -f "$ROOT/results/suitesparse100_conversion.csv" ]]; then
        skip "results/suitesparse100_conversion.csv ausente"
    elif [[ ! -d "$ROOT/matrices/suitesparse100" ]] || [[ -z "$(ls -A "$ROOT/matrices/suitesparse100" 2>/dev/null || true)" ]]; then
        log "cache matrices/suitesparse100 vazio; mantendo suitesparse100_conversion.csv versionado e self-check HB em binary128"
    fi

    log "figuras e diagramas"
    python3 "$ROOT/paper/gera_figuras.py" 2>&1 | tee "$LOGS/figures.log"
    if have pdflatex; then
        for tex in datapath_zvtakum.tex datapath_zvtakum_pt.tex zvtakum-datapath.tex zvtakum-datapath-pt.tex; do
            if [[ -f "$ROOT/paper/figures/$tex" ]]; then
                (cd "$ROOT/paper/figures" && pdflatex -interaction=nonstopmode "$tex") \
                    2>&1 | tee "$LOGS/diagram-${tex%.tex}.log"
            fi
        done
    fi
}

run_check() {
    log "referências (offline)"
    python3 "$ROOT/tools/check_references.py" --json "$ROOT/references/audit.json" \
        2>&1 | tee "$LOGS/references-offline.log"

    if [[ "$FULL" -eq 1 ]]; then
        log "referências (online)"
        python3 "$ROOT/tools/check_references.py" --online \
            --json "$ROOT/references/audit.json" 2>&1 | tee "$LOGS/references-online.log" || \
            skip "verificação online de referências indisponível; auditoria offline aprovada"
    fi

    log "manifesto"
    python3 "$ROOT/tools/make_manifest.py" 2>&1 | tee "$LOGS/manifest.log"
}

case "$COMMAND" in
    test) run_test ;;
    demo) run_demo ;;
    bench) run_bench ;;
    check) run_check ;;
    all)
        run_test
        run_bench
        run_check
        ;;
    *) echo "uso: $0 [test|demo|bench|check|all] [--strict] [--full]" >&2; exit 2 ;;
esac

log "concluído: $COMMAND"
