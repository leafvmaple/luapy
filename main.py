from __future__ import annotations

import struct
from typing import Any, BinaryIO, Optional

# Lua bytecode constant types
LUA_TNIL = 0
LUA_TBOOLEAN = 1
LUA_TNUMBER = 3
LUA_TSTRING = 4

class Reader:
    def __init__(self, file: BinaryIO):
        self.file = file

    def read_bytes(self, n: int) -> bytes:
        data = self.file.read(n)
        if len(data) != n:
            raise EOFError("Unexpected end of file")
        return data
    
    def read_uint8(self) -> int:
        """Read a single unsigned byte."""
        return struct.unpack('B', self.read_bytes(1))[0]
    
    def read_uint32(self) -> int:
        """Read an unsigned 32-bit integer."""
        return struct.unpack('I', self.read_bytes(4))[0]
    
    def read_uint64(self) -> int:
        """Read an unsigned 64-bit integer."""
        return struct.unpack('Q', self.read_bytes(8))[0]
    
    def read_double(self) -> float:
        """Read a double-precision float."""
        return struct.unpack('d', self.read_bytes(8))[0]

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


class String:
    size: int
    value: str
    
    def __init__(self, file: Reader):
        self.size = file.read_uint64()
        self.value = file.read_bytes(self.size)[:-1].decode('utf-8') if self.size > 0 else ""

    def __str__(self) -> str:
        return self.value

class Value:
    type: int
    value: Any
    
    def __init__(self, file: Reader):
        self.type = file.read_uint8()
        if self.type == LUA_TNIL:
            self.value = None
        elif self.type == LUA_TBOOLEAN:
            self.value = file.read_uint8() != 0
        elif self.type == LUA_TNUMBER:
            self.value = file.read_double()
        elif self.type == LUA_TSTRING:
            self.value = String(file)
        else:
            raise ValueError(f"Unknown constant type: {self.type}")
        
    def __str__(self) -> str:
        if self.type == LUA_TNIL:
            return 'nil'
        elif self.type == LUA_TBOOLEAN:
            return 'true' if self.value else 'false'
        elif self.type == LUA_TNUMBER:
            return str(self.value)
        elif self.type == LUA_TSTRING:
            return f'"{self.value}"'
        return str(self.value)

class Instruction:
    _instruction: int

    def __init__(self, file: Reader):
        self._instruction = file.read_uint32()

    def __str__(self):
        return f"0x{self._instruction:08x}"

class Code:
    sizecode: int
    code: list[int]
    
    def __init__(self, file: Reader):
        self.sizecode = file.read_uint32()
        self.code = [Instruction(file) for _ in range(self.sizecode)]

    def __str__(self) -> str:
        return '\n'.join(f"\t{pc + 1}\t{code}" for pc, code in enumerate(self.code))

class Constants:
    sizek: int
    values: list[Value]
    sizep: int
    subfunctions: list['Function']

    def __init__(self, file: Reader, source: str):
        self.sizek = file.read_uint32()
        self.values = [Value(file) for _ in range(self.sizek)]
        self.sizep = file.read_uint32()
        self.subfunctions = [Function(file, source) for _ in range(self.sizep)]

    def __str__(self) -> str:
        parts = []
        parts.append(f'constants ({self.sizek}):')
        parts.extend(f"\t{i + 1}\t{value}" for i, value in enumerate(self.values))

        return '\n'.join(parts)

class LocalVar:
    name: String
    startpc: int
    endpc: int
    
    def __init__(self, file: Reader):
        self.name = String(file)
        self.startpc = file.read_uint32()
        self.endpc = file.read_uint32()
    
    def __str__(self) -> str:
        return f"{self.name}\t{self.startpc + 1}\t{self.endpc + 1}"

class Debug:
    sizelineinfo: int
    lineinfo: list[int]
    sizelocvars: int
    locvars: list[LocalVar]
    sizeupvalues: int
    upvalue_names: list[String]
    
    def __init__(self, file: Reader):
        self.sizelineinfo = file.read_uint32()
        self.lineinfo = [file.read_uint32() for _ in range(self.sizelineinfo)]
        self.sizelocvars = file.read_uint32()
        self.locvars = [LocalVar(file) for _ in range(self.sizelocvars)]
        self.sizeupvalues = file.read_uint32()
        self.upvalue_names = [String(file) for _ in range(self.sizeupvalues)]

    def __str__(self) -> str:
        parts = []
        parts.append(f'locals ({self.sizelocvars}):')
        parts.extend(f"\t{i}\t{value}" for i, value in enumerate(self.locvars))

        parts.append(f'upvalues ({self.sizeupvalues}):')
        parts.extend(f"\t{i}\t{value}" for i, value in enumerate(self.upvalue_names))

        return '\n'.join(parts)

class Function:
    source: String
    type: str = "main"
    linedefined: int
    lastlinedefined: int
    nups: int
    numparams: int
    is_vararg: bool
    maxstacksize: int
    code: Code
    constants: Constants
    debug: Debug
    
    def __init__(self, file: Reader, parent: Optional[str] = None):
        self.source = String(file)
        if parent is not None:
            self.source = parent  # type: ignore
            self.type = "function"
        self.linedefined = file.read_uint32()
        self.lastlinedefined = file.read_uint32()
        self.nups = file.read_uint8()
        self.numparams = file.read_uint8()
        self.is_vararg = file.read_uint8() != 0
        self.maxstacksize = file.read_uint8()
        self.code = Code(file)
        self.constants = Constants(file, str(self.source))
        self.debug = Debug(file)

    def __str__(self) -> str:
        parts = []
        parts.append(f"{self.type} <{self.source}:{self.linedefined},{self.lastlinedefined}> ({self.code.sizecode} instructions)")
        parts.append(f"{self.numparams} params, {self.debug.sizeupvalues} upvalues, {self.debug.sizelocvars} locals, {self.constants.sizek} constants, {self.constants.sizep} functions")
        parts.append(str(self.code))
        parts.append(str(self.constants))
        parts.append(str(self.debug))
        parts.extend(str(sub) for sub in self.constants.subfunctions)

        return '\n' + '\n'.join(parts)

class PyLua:
    reader: Reader
    header: Header
    main: Function
    
    def __init__(self, file_path: str):
        with open(file_path, 'rb') as f:
            self.reader = Reader(f)
            self.header = Header(self.reader)
            self.main = Function(self.reader)

    def __str__(self) -> str:
        return f"{self.main}"


if __name__ == "__main__":
    pylua_file = PyLua("test.luac")
    print(pylua_file)