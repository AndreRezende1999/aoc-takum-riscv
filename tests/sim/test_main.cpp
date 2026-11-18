// Testes do simulador. Executado por `make sim-test` ou `make test` a partir da raiz do repositório.
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <functional>
#include <sstream>
#include <string>
#include <vector>

#include "zt/takum.hpp"
#include "zt/machine.hpp"

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

void test_narrow_table() {
    const std::vector<uint8_t> table = read_bytes(kGolden + "t16_to_t8.bin");
    int bad = 0;
    for (unsigned code = 0; code < 65536; ++code) {
        if (zt::narrow(16, 8, code) != table[code]) ++bad;
    }
    CHECK(bad == 0, "narrow T16->T8: %d divergências em 65536 códigos", bad);
}

uint64_t hex(const std::string& s) { return std::stoull(s, nullptr, 16); }

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

void test_sampled_dot() {
    int bad = 0;
    int total = 0;
    for (const std::string& line : read_lines(kGolden + "takum_dot_sampled.txt")) {
        std::istringstream in(line);
        std::string op, acc_s, a_s, b_s, r_s;
        int bits = 0;
        in >> op >> bits >> acc_s >> a_s >> b_s >> r_s;
        const uint64_t got = zt::dot_step(bits, hex(acc_s), hex(a_s), hex(b_s));
        ++total;
        if (got != hex(r_s)) ++bad;
    }
    CHECK(bad == 0, "dot amostrado: %d divergências em %d casos", bad, total);
}

void test_sampled_narrow() {
    int bad = 0;
    int total = 0;
    for (const std::string& line : read_lines(kGolden + "takum_narrow_sampled.txt")) {
        std::istringstream in(line);
        std::string kind;
        int from = 0, to = 0;
        std::string code_s, result_s;
        in >> kind >> from >> to >> code_s >> result_s;
        const uint64_t code = hex(code_s);
        const uint64_t got = kind == "compose"
                                 ? zt::narrow(16, to, zt::narrow(from, 16, code))
                                 : zt::narrow(from, to, code);
        ++total;
        if (got != hex(result_s)) ++bad;
    }
    CHECK(bad == 0, "narrow amostrado: %d divergências em %d casos", bad, total);
}

void test_t32_round_trip() {
    int bad = 0;
    uint64_t x = 0x9e3779b97f4a7c15ULL;
    for (int i = 0; i < 200000; ++i) {
        x = x * 6364136223846793005ULL + 1442695040888963407ULL;
        const uint64_t code = (x >> 16) & 0xffffffffu;
        const zt::Exact value = zt::decode(32, code);
        if (value.kind == zt::Exact::Kind::Zero) {
            if (code != 0) ++bad;
        } else if (value.kind == zt::Exact::Kind::Nar) {
            if (code != zt::nar_code(32)) ++bad;
        } else if (zt::encode(32, value) != code) {
            ++bad;
        }
    }
    CHECK(bad == 0, "ida e volta T32 amostrada: %d divergências em 200000", bad);
}

void test_algebraic_properties() {
    for (int n : {8, 16}) {
        const uint64_t limit = n == 8 ? 256 : 65536;
        const uint64_t step = n == 8 ? 1 : 17;
        const uint64_t one = uint64_t(1) << (n - 2);
        int bad = 0;
        for (uint64_t a = 0; a < limit; a += step) {
            if (zt::add(n, a, 0) != a) ++bad;
            if (zt::add(n, 0, a) != a) ++bad;
            if (a != zt::nar_code(n) && zt::sub(n, a, a) != 0) ++bad;
            if (a != zt::nar_code(n) && zt::mul(n, a, one) != a) ++bad;
            if (zt::mul(n, a, zt::nar_code(n)) != zt::nar_code(n)) ++bad;
            for (uint64_t b = 0; b < limit; b += step * 3 + 1) {
                if (zt::add(n, a, b) != zt::add(n, b, a)) ++bad;
                if (zt::mul(n, a, b) != zt::mul(n, b, a)) ++bad;
            }
        }
        CHECK(bad == 0, "propriedades T%d: %d violações", n, bad);
    }
}

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
}

void test_illegal_custom0() {
    zt::Machine machine(128, 4096);
    auto &memory = machine.memory();
    auto put = [&](uint32_t word, size_t offset) {
        memory[offset + 0] = static_cast<uint8_t>(word & 0xff);
        memory[offset + 1] = static_cast<uint8_t>((word >> 8) & 0xff);
        memory[offset + 2] = static_cast<uint8_t>((word >> 16) & 0xff);
        memory[offset + 3] = static_cast<uint8_t>((word >> 24) & 0xff);
    };
    // csrr a0, vtype (before vsetvli -> vill=1 -> 0x8000000000000000 per RVV 1.0 s3.11)
    put(0xc2102573u, 0);
    // vsetvli x0, x0, e8, m1, tu, mu
    put(0x00007057u, 4);
    // csrr a1, vtype (after vsetvli -> vill=0)
    put(0xc21025f3u, 8);
    // custom-0 with funct3=1 must be rejected.
    put(0x0000100Bu, 12);
    machine.set_pc(0);
    bool threw = false;
    try {
        machine.run(16);
    } catch (const zt::SimError &) {
        threw = true;
    }
    CHECK(machine.reg(10) == (uint64_t(1) << 63),
          "CSR vtype inicial deve ter vill=1 (RVV 1.0 §3.11)");
    CHECK((machine.reg(11) & (uint64_t(1) << 63)) == 0,
          "CSR vtype após vsetvli deve limpar vill");
    CHECK(threw, "custom-0 com funct3!=0 deve ser ilegal");
}

void test_nar_propagation() {
    CHECK(zt::add(16, zt::nar_code(16), 0x4000) == zt::nar_code(16), "NaR em add");
    CHECK(zt::mul(8, 0x40, zt::nar_code(8)) == zt::nar_code(8), "NaR em mul");
    CHECK(zt::mul(8, 0, zt::nar_code(8)) == zt::nar_code(8), "NaR vence zero em mul");
    CHECK(zt::sub(32, 0x40000000, 0x40000000) == 0, "x - x = 0");
}

}  // namespace

int main() {
    const std::vector<std::pair<const char*, std::function<void()>>> tests = {
        {"tabelas T8 (add, sub, mul)", test_t8_tables},
        {"narrow T16 -> T8", test_narrow_table},
        {"operações amostradas T16/T32/T64", test_sampled_ops},
        {"vtdot amostrado", test_sampled_dot},
        {"narrow T32 amostrado", test_sampled_narrow},
        {"ida e volta T32 amostrada", test_t32_round_trip},
        {"propriedades algébricas T8/T16", test_algebraic_properties},
        {"ida e volta do codificador", test_round_trip},
        {"propagação de NaR e zero", test_nar_propagation},
        {"instrução custom-0 ilegal", test_illegal_custom0},
    };
    for (const auto& [name, fn] : tests) {
        const int before = g_failures;
        fn();
        std::printf("%-38s %s\n", name, g_failures == before ? "ok" : "FALHOU");
    }
    std::printf("\n%d verificações, %d falhas\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
