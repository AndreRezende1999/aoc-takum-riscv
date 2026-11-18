"""Known-value and round-trip tests for the exact posit comparator."""

import unittest
from fractions import Fraction as F

try:
    from takum_rvv.posit import Posit, POSIT8, POSIT8_2, POSIT16, POSIT32
except ImportError:
    Posit = None


class PositTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(Posit, "The posit comparator is not implemented")

    def test_known_posit8_0_values(self):
        fixtures = {
            0x00: F(0),
            0x01: F(1, 64),
            0x3F: F(63, 64),
            0x40: F(1),
            0x41: F(1) + F(1, 32),
            0x48: F(5, 4),
            0x60: F(2),
            0x7F: F(64),
            0xC0: F(-1),
        }
        for raw, value in fixtures.items():
            with self.subTest(raw=hex(raw)):
                self.assertEqual(POSIT8.decode(raw), value)
                self.assertEqual(POSIT8.encode(value), raw)
        self.assertIsNone(POSIT8.decode(0x80))
        self.assertEqual(POSIT8.encode(None), 0x80)

    def test_known_posit8_2_and_wide_values(self):
        self.assertEqual(POSIT8_2.decode(0x40), 1)
        self.assertEqual(POSIT8_2.decode(0x41), F(9, 8))
        self.assertEqual(POSIT8_2.decode(0x7F), F(2**24))
        self.assertEqual(POSIT8_2.decode(0x01), F(1, 2**24))
        self.assertEqual(POSIT16.decode(0x4000), 1)
        self.assertEqual(POSIT16.decode(0x7FFF), F(2**28))
        self.assertEqual(POSIT32.decode(0x40000000), 1)
        self.assertEqual(POSIT32.decode(0x7FFFFFFF), F(2**120))

    def test_all_posit8_codes_roundtrip(self):
        for fmt in (POSIT8, POSIT8_2):
            for raw in range(256):
                value = fmt.decode(raw)
                with self.subTest(format=fmt.name, raw=hex(raw)):
                    if raw == fmt.nar:
                        self.assertIsNone(value)
                        self.assertEqual(fmt.encode(None), raw)
                    else:
                        self.assertEqual(fmt.encode(value), raw)

    def test_sampled_posit16_codes_roundtrip(self):
        for raw in range(0, 1 << 16, 13):
            value = POSIT16.decode(raw)
            if raw == POSIT16.nar:
                self.assertIsNone(value)
            else:
                self.assertEqual(POSIT16.encode(value), raw, hex(raw))

    def test_arithmetic_and_saturation(self):
        self.assertEqual(POSIT8.add(0x40, 0x40), 0x60)
        self.assertEqual(POSIT8.sub(0x60, 0x40), 0x40)
        self.assertEqual(POSIT8.mul(0x60, 0x60), POSIT8.encode(4))
        self.assertEqual(POSIT8.mul(0x7F, 0x7F), 0x7F)
        self.assertEqual(POSIT8.add(0x7F, 0x40), 0x7F)
        self.assertEqual(POSIT8.add(0x80, 0x40), 0x80)
        self.assertEqual(POSIT8.mul(0x00, 0x80), 0x80)
        self.assertEqual(POSIT8.sub(0x40, 0x40), 0)
        self.assertEqual(POSIT8.add(0x40, POSIT8.encode(-1)), 0)
        self.assertEqual(POSIT8.encode(F(-1, 2**1000)), 0)
        self.assertEqual(POSIT8.encode(F(1, 2**1000)), 0)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            Posit(8, 6)
        with self.assertRaises(ValueError):
            POSIT8.decode(256)
        with self.assertRaises(TypeError):
            POSIT8.decode(F(1, 2))
        with self.assertRaises(TypeError):
            POSIT8.encode(0.1)


if __name__ == "__main__":
    unittest.main()
