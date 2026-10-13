// =============================================================================
// Testes do núcleo Takum (Fase 1).
//
// Executado por `make test` a partir da raiz do repositório.  Os vetores
// dourados ficam em tests/golden/ e são gerados por tests/gen_golden.py a
// partir do modelo Python em racionais exatos (python/takum/codec.py).
//
// Cobre os dois itens do enunciado: extração de S, D, R, C e F; e adição,
// subtração e multiplicação em T8 (exaustivo) e T16/T32 (amostrado).
// =============================================================================

#include <cstdint>
#include <cstdio>
#include <fstream>
#include <functional>
#include <sstream>
#include <string>
#include <vector>

#include "takum.hpp"

namespace {

int g_checks = 0;
int g_failures = 0;

#define CHECK(cond, ...)                                                   \
    do {                                                                   \
        ++g_checks;                                                        \
        if (!(cond)) {                                                     \
            ++g_failures;                                                  \
            std::fprintf(stderr, "  falha %s:%d: ", __FILE__, __LINE__);   \
            std::fprintf(stderr, __VA_ARGS__);                             \
            std::fprintf(stderr, "\n");                                    \
        }                                                                  \
    } while (0)

std::vector<uint8_t> read_bytes(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    CHECK(in.good(), "não foi possível abrir %s", path.c_str());
    return std::vector<uint8_t>(std::istreambuf_iterator<char>(in), {});
}

std::vector<std::string> read_lines(const std::string& path) {
    std::ifstream in(path);
    CHECK(in.good(), "não foi possível abrir %s", path.c_str());
    std::vector<std::string> lines;
    for (std::string line; std::getline(in, line);) lines.push_back(line);
    return lines;
}

const std::string kGolden = ZT_GOLDEN_DIR "/";

// Monta um valor exato finito |v| = sig * 2^(e-63), com o bit 63 de sig em 1.
zt::Exact finite(uint64_t sig, int e, bool neg = false) {
    zt::Exact v;
    v.kind = zt::Exact::Kind::Finite;
    v.neg = neg;
    v.sig = sig;
    v.e = e;
    return v;
}

uint64_t hex(const std::string& s) { return std::stoull(s, nullptr, 16); }

// Valida a extração de S, D, R, C e F em códigos conhecidos.
// Gabarito: modelo Python (python/tests/test_codec.py) e a definição do
// formato em docs/fase1.md.
void test_fields() {
    // 0x4a em T8: S=0, D=1, R=1 (r=1), C=0 (c=1) e F=1/2 com p=6.
    const zt::Fields f = zt::decode_fields(8, 0x4a);
    CHECK(f.s == 0 && f.d == 1, "0x4a: S=%d D=%d", f.s, f.d);
    CHECK(f.regime_bits == 1 && f.regime == 1, "0x4a: R=%d r=%d", f.regime_bits, f.regime);
    CHECK(f.cbits == 0 && f.c == 1, "0x4a: C=%llu c=%lld", static_cast<unsigned long long>(f.cbits),
          static_cast<long long>(f.c));
    CHECK(f.frac == 32 && f.p == 6, "0x4a: F=%llu p=%d", static_cast<unsigned long long>(f.frac), f.p);

    // Os códigos de 1.0 nas três larguras: D=1, R=0 (c=0), C=0 e F=0, com o
    // valor exato sig=2^63 e e=0.
    for (int n : {8, 16, 32}) {
        const uint64_t one = uint64_t(1) << (n - 2);
        const zt::Fields g = zt::decode_fields(n, one);
        const zt::Exact v = zt::decode(n, one);
        CHECK(g.s == 0 && g.d == 1 && g.regime == 0 && g.c == 0 && g.frac == 0,
              "n=%d: campos de 1.0 (c=%lld)", n, static_cast<long long>(g.c));
        CHECK(v.kind == zt::Exact::Kind::Finite && !v.neg && v.sig == uint64_t(1) << 63 && v.e == 0,
              "n=%d: valor exato de 1.0", n);
    }

    // Extremos de T8: maxpos (0x7f) tem c=239 e p=0; minpos (1) tem c=-239.
    const zt::Fields maxp = zt::decode_fields(8, 0x7f);
    const zt::Fields minp = zt::decode_fields(8, 0x01);
    CHECK(maxp.c == 239 && maxp.frac == 0 && maxp.p == 0, "T8 maxpos: c=%lld",
          static_cast<long long>(maxp.c));
    CHECK(minp.c == -239 && minp.frac == 0 && minp.p == 0, "T8 minpos: c=%lld",
          static_cast<long long>(minp.c));

    // NaR (0x80 em T8) não tem campos de valor, mas decode_fields lê os bits
    // como estão (S=1); quem decide NaR é decode.
    CHECK(zt::decode_fields(8, 0x80).s == 1, "0x80: S deve ser 1 na leitura crua");
    CHECK(zt::decode(8, 0x80).kind == zt::Exact::Kind::Nar, "0x80 deve decodificar como NaR");
    CHECK(zt::decode(8, 0).kind == zt::Exact::Kind::Zero, "0 deve decodificar como zero");
}

// Valida codificação: zero, NaR, empates para par e saturação.
// Gabarito: casos dirigidos do modelo Python (test_codec.py,
// test_ties_even_and_truncated_characteristic_threshold).
void test_encode_rounding_and_saturation() {
    // Zero e NaR têm códigos fixos.
    CHECK(zt::encode(8, zt::Exact{}) == 0, "zero deve codificar em 0");
    zt::Exact nar;
    nar.kind = zt::Exact::Kind::Nar;
    CHECK(zt::encode(8, nar) == 0x80, "NaR deve codificar em 0x80 em T8");

    // Empate no código: 17/16 fica entre 0x40 e 0x41 -> par (0x40); 19/16
    // fica entre 0x41 e 0x42 -> par (0x42); o negativo é o complemento de
    // dois de 0x42.
    CHECK(zt::encode(8, finite(17ull << 59, 0)) == 0x40, "17/16 -> 0x40");
    CHECK(zt::encode(8, finite(19ull << 59, 0)) == 0x42, "19/16 -> 0x42");
    CHECK(zt::encode(8, finite(19ull << 59, 0, true)) == 0xbe, "-19/16 -> 0xbe");

    // Empate na fronteira da característica truncada (p=0 em T8): 2^-231 é o
    // ponto médio no domínio do código (geométrico) entre 2^-239 (código 1)
    // e 2^-223 (código 2) -> par (2).
    CHECK(zt::encode(8, finite(uint64_t(1) << 63, -231)) == 2, "2^-231 -> 2");
    CHECK(zt::encode(8, finite(uint64_t(1) << 63, -232)) == 1, "2^-232 -> 1");

    // Saturação: |v| acima de maxpos vira maxpos; abaixo de minpos vira
    // minpos (sem zero e sem infinito); o negativo é o complemento de dois.
    for (int n : {8, 16, 32}) {
        const uint64_t maxpos = zt::nar_code(n) - 1;
        CHECK(zt::encode(n, finite(uint64_t(1) << 63, 1000)) == maxpos, "n=%d: 2^1000 satura", n);
        CHECK(zt::encode(n, finite(uint64_t(1) << 63, -1000)) == 1, "n=%d: 2^-1000 satura", n);
        CHECK(zt::encode(n, finite(uint64_t(1) << 63, 1000, true)) ==
                  ((uint64_t(0) - maxpos) & zt::width_mask(n)),
              "n=%d: -2^1000 satura no negativo", n);
        CHECK(zt::decode(n, zt::encode(n, finite(uint64_t(1) << 63, 1000))).kind ==
                  zt::Exact::Kind::Finite,
              "n=%d: saturação não gera NaR", n);
    }
}

// Valida as tabelas T8 completas de add, sub e mul (256x256 códigos cada).
// Gabarito: vetores dourados gerados pelo modelo Python (tests/golden).
void test_t8_tables() {
    const char* names[] = {"add", "sub", "mul"};
    for (int op = 0; op < 3; ++op) {
        const std::vector<uint8_t> table = read_bytes(kGolden + "t8_" + names[op] + ".bin");
        CHECK(table.size() == 65536, "tabela t8_%s com tamanho %zu", names[op], table.size());
        int bad = 0;
        for (unsigned a = 0; a < 256; ++a) {
            for (unsigned b = 0; b < 256; ++b) {
                uint64_t got = op == 0   ? zt::add(8, a, b)
                               : op == 1 ? zt::sub(8, a, b)
                                         : zt::mul(8, a, b);
                if (got != table[a * 256 + b]) {
                    if (bad < 5)
                        std::fprintf(stderr, "    t8 %s a=%02x b=%02x got=%02llx want=%02x\n",
                                     names[op], a, b, static_cast<unsigned long long>(got),
                                     table[a * 256 + b]);
                    ++bad;
                }
            }
        }
        CHECK(bad == 0, "t8 %s: %d divergências em 65536 pares", names[op], bad);
    }
}

// Valida add/sub/mul amostrados em T16/T32 contra o gabarito Python.
// Gabarito: tests/golden/takum_ops_sampled.txt (gerado por gen_golden.py).
void test_sampled_ops() {
    int bad = 0;
    int total = 0;
    for (const std::string& line : read_lines(kGolden + "takum_ops_sampled.txt")) {
        std::istringstream in(line);
        std::string op, a_s, b_s, r_s;
        int bits = 0;
        in >> op >> bits >> a_s >> b_s >> r_s;
        const uint64_t a = hex(a_s);
        const uint64_t b = hex(b_s);
        const uint64_t want = hex(r_s);
        uint64_t got = op == "add" ? zt::add(bits, a, b)
                       : op == "sub" ? zt::sub(bits, a, b)
                                     : zt::mul(bits, a, b);
        ++total;
        if (got != want) {
            if (bad < 5)
                std::fprintf(stderr, "    %s%d a=%llx b=%llx got=%llx want=%llx\n", op.c_str(),
                             bits, static_cast<unsigned long long>(a),
                             static_cast<unsigned long long>(b),
                             static_cast<unsigned long long>(got),
                             static_cast<unsigned long long>(want));
            ++bad;
        }
    }
    CHECK(bad == 0, "operações amostradas: %d divergências em %d casos", bad, total);
}

// Valida a ida e volta codificar/decodificar: decode seguido de encode
// reproduz o código original (inclusive na revisão da codificação).
// Gabarito: identidade do par decode/encode (não há vetor externo).
void test_round_trip() {
    for (int n : {8, 16}) {
        int bad = 0;
        const uint64_t limit = uint64_t(1) << n;
        for (uint64_t code = 0; code < limit; ++code) {
            const zt::Exact v = zt::decode(n, code);
            if (v.kind == zt::Exact::Kind::Zero) {
                if (code != 0) ++bad;
                continue;
            }
            if (v.kind == zt::Exact::Kind::Nar) {
                if (code != zt::nar_code(n)) ++bad;
                continue;
            }
            if (zt::encode(n, v) != code) ++bad;
        }
        CHECK(bad == 0, "ida e volta T%d: %d códigos não reproduzidos", n, bad);
    }

    // T32: 2^32 códigos é inviável de enumerar; a amostra determinística
    // (gerador congruente linear) cobre a identidade nas três larguras.
    int bad = 0;
    uint64_t x = 0x0123456789abcdefULL;
    for (int i = 0; i < 200000; ++i) {
        x = x * 6364136223846793005ULL + 1442695040888963407ULL;
        const uint64_t code = (x >> 16) & 0xffffffffu;
        const zt::Exact v = zt::decode(32, code);
        if (v.kind == zt::Exact::Kind::Zero) {
            if (code != 0) ++bad;
            continue;
        }
        if (v.kind == zt::Exact::Kind::Nar) {
            if (code != zt::nar_code(32)) ++bad;
            continue;
        }
        if (zt::encode(32, v) != code) ++bad;
    }
    CHECK(bad == 0, "ida e volta T32 amostrada: %d códigos não reproduzidos em 200000", bad);
}

// Valida NaR e zero nas operações e cancelamento exato.
// Gabarito: definição do formato em docs/fase1.md.
void test_nar_propagation() {
    CHECK(zt::add(16, zt::nar_code(16), 0x4000) == zt::nar_code(16), "NaR em add");
    CHECK(zt::mul(8, 0x40, zt::nar_code(8)) == zt::nar_code(8), "NaR em mul");
    CHECK(zt::mul(8, 0, zt::nar_code(8)) == zt::nar_code(8), "NaR vence zero em mul");
    CHECK(zt::sub(32, 0x40000000, 0x40000000) == 0, "x - x = 0");
}

}  // namespace

int main() {
    const std::vector<std::pair<const char*, std::function<void()>>> tests = {
        {"campos S, D, R, C e F", test_fields},
        {"codificação: par, zero, NaR e saturação", test_encode_rounding_and_saturation},
        {"tabelas T8 (add, sub, mul)", test_t8_tables},
        {"operações amostradas T16/T32", test_sampled_ops},
        {"ida e volta do codificador", test_round_trip},
        {"propagação de NaR e zero", test_nar_propagation},
    };
    for (const auto& [name, fn] : tests) {
        const int before = g_failures;
        fn();
        // Alinha em 42 colunas contando caracteres (não bytes: os acentos
        // ocupam 2 bytes em UTF-8).
        int visible = 0;
        for (const unsigned char* p = reinterpret_cast<const unsigned char*>(name); *p != 0; ++p)
            if ((*p & 0xC0) != 0x80) ++visible;
        std::printf("%s", name);
        for (int i = visible; i < 42; ++i) std::putchar(' ');
        std::printf(" %s\n", g_failures == before ? "ok" : "FALHOU");
    }
    std::printf("\n%d verificações, %d falhas\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
