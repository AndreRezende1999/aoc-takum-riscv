"""Known-value, round-trip, and ALU tests for Linear Takum and Logarithmic Takum."""

import unittest
from decimal import Decimal
from fractions import Fraction as F

try:
    from takum_rvv.codec import Takum, LogTakum, LOG_TAKUM8, LOG_TAKUM16, LOG_TAKUM32
except ImportError:
    Takum = LogTakum = None


class CodecTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(Takum, "O codec independente ainda precisa ser implementado")
        self.t = Takum(8)

    def test_known_fields_and_values(self):
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
        wide = Takum(16)
        for raw in range(256):
            value = self.t.decode(raw)
            self.assertEqual(self.t.encode(value), raw)
            self.assertEqual(wide.decode(raw << 8), value)
            self.assertEqual(self.t.convert(raw, wide), raw << 8)

    def test_ties_even_and_truncated_characteristic_threshold(self):
        self.assertEqual(self.t.encode(F(17, 16)), 0x40)
        self.assertEqual(self.t.encode(F(19, 16)), 0x42)
        self.assertEqual(self.t.encode(F(-19, 16)), 0xbe)
        # Halfway in the encoding between 2^-239 and 2^-223 is 2^-231.
        self.assertEqual(self.t.encode(F(1, 2**231)), 2)
        self.assertEqual(self.t.encode(F(1, 2**232)), 1)
        self.assertEqual(self.t.encode(F(1, 2**1000)), 1)
        self.assertEqual(self.t.encode(F(2**1000)), 0x7f)

    def test_alu_specials_cancellation_and_exact_examples(self):
        self.assertEqual(self.t.add(0x40, 0x40), 0x48)
        self.assertEqual(self.t.sub(0x48, 0x40), 0x40)
        self.assertEqual(self.t.mul(0x44, 0x48), 0x4a)
        self.assertEqual(self.t.add(0x40, 0xc0), 0)
        self.assertEqual(self.t.mul(0, 0x80), 0x80)
        for raw in range(256):
            self.assertEqual(self.t.add(raw, 0), raw)
            self.assertEqual(self.t.sub(raw, raw), 0x80 if raw == 0x80 else 0)

    def test_invalid_inputs_and_widths_are_rejected(self):
        for raw in (-1, 256):
            with self.assertRaises(ValueError):
                self.t.decode(raw)
        with self.assertRaises(ValueError):
            Takum(12)

    def test_invalid_text_is_not_silently_converted_to_nar(self):
        with self.assertRaises(ValueError):
            self.t.encode('typing error')
        with self.assertRaises(TypeError):
            self.t.encode(0.1)

    def test_large_width_near_one_and_exact_product(self):
        for n in (16, 32, 64):
            t = Takum(n)
            one = 1 << (n - 2)
            self.assertEqual(t.decode(one + 1), 1 + F(1, 2**(n - 5)))
            self.assertEqual(t.mul(one, one + 1), one + 1)

    def test_logarithmic_takum_known_values_roundtrip_and_alu(self):
        lt8 = LOG_TAKUM8
        self.assertEqual(lt8.decode(0), 0)
        self.assertEqual(lt8.decode(0x40), 1)
        self.assertEqual(lt8.decode(0xc0), -1)
        self.assertIsNone(lt8.decode(0x80))
        self.assertEqual(lt8.encode(1), 0x40)
        self.assertEqual(lt8.encode(-1), 0xc0)
        self.assertEqual(lt8.encode(None), 0x80)
        # Signed symmetry and exhaustive round-trip in T8
        for raw in range(256):
            val = lt8.decode(raw)
            self.assertEqual(lt8.encode(val), raw)
            if raw not in (0, 0x80):
                neg = (-raw) & 0xFF
                self.assertLess(abs(lt8.decode(neg) + val), Decimal("1e-70") * abs(val))
        # Exact log-domain multiplicative closure and identity
        self.assertEqual(lt8.mul(0x41, 0x3f), 0x40)
        self.assertEqual(lt8.mul(0xc1, 0x40), 0xc1)
        self.assertEqual(lt8.div(0x48, 0x48), 0x40)
        self.assertEqual(lt8.mul(0, 0x80), 0x80)
        # T16 and T32 sampled round-trip
        for lt in (LOG_TAKUM16, LOG_TAKUM32):
            one = 1 << (lt.bits - 2)
            self.assertEqual(lt.encode(lt.decode(one + 1)), one + 1)
            self.assertEqual(lt.encode(lt.decode(one - 1)), one - 1)


if __name__ == '__main__':
    unittest.main()
