from __future__ import annotations

import struct

class reader:
    def __init__(self, file):
        self.file = file

    def read_bytes(self, n):
        data = self.file.read(n)
        if len(data) != n:
            raise EOFError("Unexpected end of file")
        return data

class binary:
    def __repr__(self):
        attrs = ', '.join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"

class header(binary):
    signature: bytes
    version: int
    format: int
    endianness: int
    int_len: int
    size_len: int
    inst_len: int
    number_len: int
    number_is_int: bool
    def __init__(self, file: reader):
        self.signature = file.read_bytes(4)
        if self.signature != b'\x1bLua':
            raise ValueError("Not a valid Lua bytecode file")
        self.version = struct.unpack('B', file.read_bytes(1))[0]
        self.format = struct.unpack('B', file.read_bytes(1))[0]
        self.endianness = struct.unpack('B', file.read_bytes(1))[0]
        self.int_len = struct.unpack('B', file.read_bytes(1))[0]
        self.size_len = struct.unpack('B', file.read_bytes(1))[0]
        self.inst_len = struct.unpack('B', file.read_bytes(1))[0]
        self.number_len = struct.unpack('B', file.read_bytes(1))[0]
        number_format = struct.unpack('B', file.read_bytes(1))[0]
        self.number_is_int = (number_format == 0)


class string(binary):
    size: int
    value: str
    def __init__(self, file: reader):
        self.size = struct.unpack('Q', file.read_bytes(8))[0]
        self.value = file.read_bytes(self.size)[:-1].decode('utf-8')

    def __repr__(self):
        return self.value

class value(binary):
    type: int
    value: any
    def __init__(self, file: reader):
        self.type = struct.unpack('B', file.read_bytes(1))[0]
        if self.type == 0:  # nil
            self.value = None
        elif self.type == 1:  # boolean
            self.value = struct.unpack('B', file.read_bytes(1))[0] != 0
        elif self.type == 3:  # number
            self.value = struct.unpack('d', file.read_bytes(8))[0]
        elif self.type == 4:  # string
            self.value = string(file).value
        else:
            raise ValueError(f"Unknown constant type: {self.type}")
        
    def __repr__(self):
        if self.type == 4:
            return f'"{self.value}"'
        return self.value

class Code(binary):
    sizecode: int
    code: list[int]
    def __init__(self, file: reader):
        self.sizecode = struct.unpack('I', file.read_bytes(4))[0]
        self.code = [struct.unpack('I', file.read_bytes(4))[0] for _ in range(self.sizecode)]

    def __repr__(self):
        return '\n'.join(f"\t{pc}\t0x{code:08x}" for pc, code in enumerate(self.code))

class Constants(binary):
    sizek: int
    values: list[value]
    sizep: int
    subfunctions: list[function]

    def __init__(self, file: reader, source: str):
        self.sizek = struct.unpack('I', file.read_bytes(4))[0]
        self.values = [value(file) for _ in range(self.sizek)]
        self.sizep = struct.unpack('I', file.read_bytes(4))[0]
        self.subfunctions = [function(file, source) for _ in range(self.sizep)]

    def __repr__(self):
        return f'constants ({self.sizek}):\n' + \
            '\n'.join(f"\t{i + 1}\t{value}\n" for i, value in enumerate(self.values)) + \
            '\n'.join(f"{sub}" for sub in self.subfunctions)

class function(binary):
    source: string
    type: str = "main"
    linedefined: int
    lastlinedefined: int
    nups: int
    numparams: int
    is_vararg: int
    maxstacksize: int
    code: Code
    constants: Constants
    def __init__(self, file: reader, parent: string = None):
        self.source = string(file)
        if parent is not None:
            self.source = parent
            self.type = "function"
        self.linedefined = struct.unpack('I', file.read_bytes(4))[0]
        self.lastlinedefined = struct.unpack('I', file.read_bytes(4))[0]
        self.nups = struct.unpack('B', file.read_bytes(1))[0]
        self.numparams = struct.unpack('B', file.read_bytes(1))[0]
        self.is_vararg = struct.unpack('B', file.read_bytes(1))[0]
        self.maxstacksize = struct.unpack('B', file.read_bytes(1))[0]
        self.code = Code(file)
        self.constants = Constants(file, self.source)

    def __repr__(self):
        return f"\n{self.type} <{self.source}:{self.linedefined},{self.lastlinedefined}>" + \
            f" ({self.code.sizecode} instruntions)\n" + \
            f"{self.numparams} params, {self.nups} upvalues, " + \
            f"{self.constants.sizek} constants, {self.constants.sizep} functions\n" + \
            f"{self.code}\n" + \
            f"{self.constants}"

class pylua(binary):
    def __init__(self, file_path: str):
        with open(file_path, 'rb') as f:
            self.reader = reader(f)
            self.header = header(self.reader)
            self.main = function(self.reader)

    def __repr__(self):
        return f"{self.main}"
    
    def __str__(self):
        return self.__repr__()

if __name__ == "__main__":
    pylua_file = pylua("test.luac")
    print(pylua_file)