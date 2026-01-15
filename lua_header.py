from __future__ import annotations

from lua_io import Reader


class Header:
    signature: bytes
    version: int
    format: int
    endianness: int
    int_len: int
    size_len: int
    inst_len: int
    number_len: int
    number_is_int: bool

    def __init__(self, file: Reader):
        self.signature = file.read_bytes(4)
        if self.signature != b'\x1bLua':
            raise ValueError("Not a valid Lua bytecode file")
        self.version = file.read_uint8()
        self.format = file.read_uint8()
        self.endianness = file.read_uint8()
        self.int_len = file.read_uint8()
        self.size_len = file.read_uint8()
        self.inst_len = file.read_uint8()
        self.number_len = file.read_uint8()
        self.number_is_int = (file.read_uint8() != 0)
