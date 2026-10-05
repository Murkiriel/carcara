"""Monta tiles vetoriais (MVT) mínimos para os testes: só o que a validação lê, o nome da camada e as feições."""
import gzip
from typing import Dict


def varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        out.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(out)


def field(number: int, payload: bytes) -> bytes:
    """Um campo de tamanho declarado (tipo 2 do protobuf)."""
    return varint((number << 3) | 2) + varint(len(payload)) + payload


def layer(name: str, features: int) -> bytes:
    body = field(1, name.encode("utf-8"))
    for i in range(features):
        body += field(2, varint(8) + varint(i))  # feição com um id: basta para ser contada
    body += varint((15 << 3) | 0) + varint(2)     # versão, um campo varint: precisa ser pulado na leitura
    return field(3, body)


def tile(layers: Dict[str, int], compressed: bool = True) -> bytes:
    raw = b"".join(layer(name, count) for name, count in layers.items())
    return gzip.compress(raw, mtime=0) if compressed else raw
