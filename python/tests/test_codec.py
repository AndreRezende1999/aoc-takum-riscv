"""Testes do codec Takum em racionais exatos (gabarito da Fase 1).

Os casos de arredondamento usam os mesmos valores esperados do teste C++
(tests/test_main.cpp); a verificação contra a tabela externa da libtakum está
em test_reference.py.  Ver docs/fase1.md.
"""

import unittest
from fractions import Fraction as F

from takum.codec import Takum


class CodecTests(unittest.TestCase):
    def setUp(self):
        self.t = Takum(8)

    def test_known_fields_and_values(self):
        """Valida os campos (S, D, R, C, F) e valores conhecidos de T8, além
        do NaR.  Gabarito: definição do formato em docs/fase1.md."""
        for raw, value in {0: F(0), 0x40: F(1), 0x41: F(9, 8),
                           0x44: F(3, 2), 0x48: F(2), 0x4a: F(3),
                           0x4c: F(4), 0x38: F(1, 2), 0xc0: F(-1),
                           1: F(1, 2**239), 0x7f: F(2**239)}.items():
            self.assertEqual(self.t.decode(raw), value, hex(raw))
            self.assertEqual(self.t.encode(value), raw)
        self.assertIsNone(self.t.decode(0x80))
        fields = self.t.fields(0x4a)
        self.assertEqual((fields.sign, fields.direction, fields.regime,
                          fields.characteristic, fields.fraction), (0, 1, 1, 1, F(1, 2)))

    def test_all_t8_codes_roundtrip_and_widen_exactly(self):
        """Valida a ida e volta dos 256 códigos T8 e o alargamento exato para
        T16 (código T8 deslocado de 8 bits decodifica ao mesmo valor).
        Gabarito: identidade do codec, cuja tabela T8 é conferida contra a
        libtakum em test_reference.py."""
        wide = Takum(16)
        for raw in range(256):
            value = self.t.decode(raw)
            self.assertEqual(self.t.encode(value), raw)
            self.assertEqual(wide.decode(raw << 8), value)

    def test_ties_even_and_truncated_characteristic_threshold(self):
        """Valida o empate para par no código, inclusive na fronteira em que
        a característica de T8 é truncada (p = 0).  Gabarito: Hunhold,
        arXiv:2408.10594v4 §5.5; os mesmos casos estão em test_main.cpp."""
        self.assertEqual(self.t.encode(F(17, 16)), 0x40)
        self.assertEqual(self.t.encode(F(19, 16)), 0x42)
        self.assertEqual(self.t.encode(F(-19, 16)), 0xbe)
        # Ponto médio no domínio do código (geométrico) entre 2^-239 e
        # 2^-223: 2^-231 (empate para par).
        self.assertEqual(self.t.encode(F(1, 2**231)), 2)
        self.assertEqual(self.t.encode(F(1, 2**232)), 1)
        self.assertEqual(self.t.encode(F(1, 2**1000)), 1)
        self.assertEqual(self.t.encode(F(2**1000)), 0x7f)

    def test_alu_specials_cancellation_and_exact_examples(self):
        """Valida NaR, zero e cancelamento na ALU (add/sub/mul).  Gabarito:
        definição do formato em docs/fase1.md."""
        self.assertEqual(self.t.add(0x40, 0x40), 0x48)
        self.assertEqual(self.t.sub(0x48, 0x40), 0x40)
        self.assertEqual(self.t.mul(0x44, 0x48), 0x4a)
        self.assertEqual(self.t.add(0x40, 0xc0), 0)
        self.assertEqual(self.t.mul(0, 0x80), 0x80)
        for raw in range(256):
            self.assertEqual(self.t.add(raw, 0), raw)
            self.assertEqual(self.t.sub(raw, raw), 0x80 if raw == 0x80 else 0)

    def test_invalid_inputs_and_widths_are_rejected(self):
        """Valida que códigos fora da largura e larguras não suportadas são
        rejeitados."""
        for raw in (-1, 256):
            with self.assertRaises(ValueError): self.t.decode(raw)
        with self.assertRaises(ValueError): Takum(12)

    def test_invalid_text_is_not_silently_converted_to_nar(self):
        """Valida que texto inválido e float do host não viram NaR em
        silêncio (só None gera NaR)."""
        with self.assertRaises(ValueError): self.t.encode('typing error')
        with self.assertRaises(TypeError): self.t.encode(0.1)

    def test_large_width_near_one_and_exact_product(self):
        """Valida 1 + 1/2^(n-5) e o produto exato em T16 e T32, os dois
        tamanhos além de T8 cobertos pela Fase 1."""
        for n in (16, 32):
            t = Takum(n)
            one = 1 << (n - 2)
            self.assertEqual(t.decode(one + 1), 1 + F(1, 2**(n - 5)))
            self.assertEqual(t.mul(one, one + 1), one + 1)


if __name__ == '__main__':
    unittest.main()
