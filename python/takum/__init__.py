"""Modelo de referência Takum linear da Fase 1 (racionais exatos).

O codec em codec.py é o gabarito dos vetores dourados e dos testes do núcleo
em C++ (src/takum.cpp); a especificação está em docs/fase1.md.
"""

from .codec import Fields, Takum

__all__ = ["Takum", "Fields"]
