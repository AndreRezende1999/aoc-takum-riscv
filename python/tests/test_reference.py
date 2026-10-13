"""Verificação do gabarito Python contra fontes externas.

1. Tabela T8 gerada pela libtakum de Laslo Hunhold, revisão pinada
   ``776ac0ca7855f640100731ed8bbb0c7cf83b2d94`` (v2.0.0, licença ISC),
   commitada em ``data/libtakum_t8.bin.gz``.  A tabela não é gerada pelo codec
   Python: são os 256 valores decodificados em binary64 little-endian,
   seguidos das tabelas 256x256 de soma, subtração e multiplicação (índice
   ``a*256+b``), com cabeçalho ASCII ``TK8REF1\\n``.  SHA-256 descompactado:
   ``88b3d655a792b66a074923550911e133fdd789340c9703fa2b81f7741696a9ab``.
   A proveniência e a decisão de commitar a tabela estão em docs/fase1.md,
   seção 7.6.

2. Limites de exatidão de inteiros publicados: Hunhold, arXiv:2412.20273v2,
   seção 5 (maiores inteiros consecutivos representáveis em cada largura).
"""

import gzip
import hashlib
import math
import struct
import unittest
from fractions import Fraction
from pathlib import Path

from takum.codec import Takum

DATA = Path(__file__).parent / 'data'
REFERENCE_SHA256 = '88b3d655a792b66a074923550911e133fdd789340c9703fa2b81f7741696a9ab'


def validate_libtakum(path):
    """Compara todos os 256 códigos e os 65536 pares por operação de T8 com a
    tabela externa e devolve um relatório com as contagens de divergências."""
    blob = path.read_bytes()
    data = gzip.decompress(blob) if path.suffix == '.gz' else blob
    if len(data) != 8 + 256 * 8 + 3 * 65536 or data[:8] != b'TK8REF1\n':
        raise ValueError('Invalid reference file (header or size)')
    t = Takum(8)
    report = {'upstream_commit': '776ac0ca7855f640100731ed8bbb0c7cf83b2d94',
              'reference_sha256': hashlib.sha256(data).hexdigest(),
              'variant': 'linear', 'checks': {}}
    mismatches = []
    for a in range(256):
        d = struct.unpack_from('<d', data, 8 + 8 * a)[0]
        want = None if math.isnan(d) else Fraction(d)
        if t.decode(a) != want:
            mismatches.append({'a': a, 'actual': str(t.decode(a)), 'expected': str(want)})
    report['checks']['decode'] = {'cases': 256, 'mismatches': len(mismatches),
                                  'first_mismatches': mismatches[:10]}
    offset = 8 + 256 * 8
    for op in ('add', 'sub', 'mul'):
        mismatches = []
        fn = getattr(t, op)
        for a in range(256):
            for b in range(256):
                want = data[offset + a * 256 + b]
                got = fn(a, b)
                if got != want:
                    mismatches.append({'a': a, 'b': b, 'actual': got, 'expected': want})
        report['checks'][op] = {'cases': 65536, 'mismatches': len(mismatches),
                                'first_mismatches': mismatches[:10]}
        offset += 65536
    report['matches_all'] = all(v['mismatches'] == 0 for v in report['checks'].values())
    return report


class ReferenceTests(unittest.TestCase):
    def test_all_t8_pairs_match_pinned_libtakum(self):
        """Valida decodificação e add/sub/mul de todo o T8 (256 códigos e
        65536 pares por operação) contra a tabela externa da libtakum."""
        report = validate_libtakum(DATA / 'libtakum_t8.bin.gz')
        self.assertEqual(report['reference_sha256'], REFERENCE_SHA256)
        self.assertTrue(report['matches_all'], report)

    def test_integer_exactness_limits_from_published_table(self):
        """Valida os maiores inteiros consecutivos representáveis em T8, T16
        e T32.  Gabarito: Hunhold, arXiv:2412.20273v2, seção 5."""
        for bits, last in ((8, 8), (16, 512), (32, 2**24)):
            t = Takum(bits)
            for sign in (1, -1):
                for value in (last - 1, last):
                    self.assertEqual(t.decode(t.encode(sign * value)), sign * value)
                self.assertNotEqual(t.decode(t.encode(sign * (last + 1))), sign * (last + 1))


if __name__ == '__main__':
    unittest.main()
