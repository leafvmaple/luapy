from __future__ import annotations

from typing import Optional
from lua_io import Reader
from lua_types import String, Value
from lua_utils import toboolean

# Lua 5.1 opcodes
OPCODES = [
    "MOVE", "LOADK", "LOADBOOL", "LOADNIL", "GETUPVAL",
    "GETGLOBAL", "GETTABLE", "SETGLOBAL", "SETUPVAL", "SETTABLE",
    "NEWTABLE", "SELF", "ADD", "SUB", "MUL",
    "DIV", "MOD", "POW", "UNM", "NOT",
    "LEN", "CONCAT", "JMP", "EQ", "LT",
    "LE", "TEST", "TESTSET", "CALL", "TAILCALL",
    "RETURN", "FORLOOP", "FORPREP", "TFORLOOP", "SETLIST",
    "CLOSE", "CLOSURE", "VARARG"
]

# Instruction formats
# iABC: A:8 C:9 B:9 OP:6
# iABx: A:8 Bx:18 OP:6
# iAsBx: A:8 sBx:18 OP:6
OpArgN = 0  # argument is not used
OpArgU = 1  # argument is used
OpArgR = 2  # argument is a register or a jump offset
OpArgK = 3  # argument is a constant or register/constant

class OpMode:
    def __init__(self, t, a, b, c, mode):
        self.testflag = t  # operator is a test (next instruction must be a jump)
        self.setareg = a   # instruction set register A
        self.argb = b      # B arg mode
        self.argc = c      # C arg mode
        self.mode = mode   # op mode (iABC, iABx, iAsBx)

# OpMode(testflag, setareg, argb, argc, mode)
# mode: 0=iABC, 1=iABx, 2=iAsBx
OPMODES = [
    OpMode(0, 1, OpArgR, OpArgN, 0),  # MOVE
    OpMode(0, 1, OpArgK, OpArgN, 1),  # LOADK
    OpMode(0, 1, OpArgU, OpArgU, 0),  # LOADBOOL
    OpMode(0, 1, OpArgU, OpArgN, 0),  # LOADNIL
    OpMode(0, 1, OpArgU, OpArgN, 0),  # GETUPVAL
    OpMode(0, 1, OpArgK, OpArgN, 1),  # GETGLOBAL
    OpMode(0, 1, OpArgR, OpArgK, 0),  # GETTABLE
    OpMode(0, 0, OpArgK, OpArgN, 1),  # SETGLOBAL
    OpMode(0, 0, OpArgU, OpArgN, 0),  # SETUPVAL
    OpMode(0, 0, OpArgK, OpArgK, 0),  # SETTABLE
    OpMode(0, 1, OpArgU, OpArgU, 0),  # NEWTABLE
    OpMode(0, 1, OpArgR, OpArgK, 0),  # SELF
    OpMode(0, 1, OpArgK, OpArgK, 0),  # ADD
    OpMode(0, 1, OpArgK, OpArgK, 0),  # SUB
    OpMode(0, 1, OpArgK, OpArgK, 0),  # MUL
    OpMode(0, 1, OpArgK, OpArgK, 0),  # DIV
    OpMode(0, 1, OpArgK, OpArgK, 0),  # MOD
    OpMode(0, 1, OpArgK, OpArgK, 0),  # POW
    OpMode(0, 1, OpArgR, OpArgN, 0),  # UNM
    OpMode(0, 1, OpArgR, OpArgN, 0),  # NOT
    OpMode(0, 1, OpArgR, OpArgN, 0),  # LEN
    OpMode(0, 1, OpArgR, OpArgR, 0),  # CONCAT
    OpMode(0, 0, OpArgR, OpArgN, 2),  # JMP
    OpMode(1, 0, OpArgK, OpArgK, 0),  # EQ
    OpMode(1, 0, OpArgK, OpArgK, 0),  # LT
    OpMode(1, 0, OpArgK, OpArgK, 0),  # LE
    OpMode(1, 0, OpArgN, OpArgU, 0),  # TEST
    OpMode(1, 1, OpArgR, OpArgU, 0),  # TESTSET
    OpMode(0, 1, OpArgU, OpArgU, 0),  # CALL
    OpMode(0, 1, OpArgU, OpArgU, 0),  # TAILCALL
    OpMode(0, 0, OpArgU, OpArgN, 0),  # RETURN
    OpMode(0, 1, OpArgR, OpArgN, 2),  # FORLOOP
    OpMode(0, 1, OpArgR, OpArgN, 2),  # FORPREP
    OpMode(0, 0, OpArgN, OpArgU, 0),  # TFORLOOP
    OpMode(0, 0, OpArgU, OpArgU, 0),  # SETLIST
    OpMode(0, 0, OpArgN, OpArgN, 0),  # CLOSE
    OpMode(0, 1, OpArgU, OpArgN, 1),  # CLOSURE
    OpMode(0, 1, OpArgU, OpArgN, 0),  # VARARG
]

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

class Instruction:
    instruction: int

    _opcode: int
    _opname: int
    _args: list[int]
    _comment: Optional[str]

    def __init__(self, file: Reader):
        self._args = []
        self._comment = None

        self.instruction = file.read_uint32()
        # Decode instruction
        self._opcode = self.instruction & 0x3F  # bits 0-5
        A = (self.instruction >> 6) & 0xFF  # bits 6-13
        C = (self.instruction >> 14) & 0x1FF  # bits 14-22
        B = (self.instruction >> 23) & 0x1FF  # bits 23-31
        Bx = (self.instruction >> 14) & 0x3FFFF  # bits 14-31
        sBx = Bx - 131071  # signed Bx

        self._opname = OPCODES[self._opcode]
        mode = OPMODES[self._opcode]

        self._args.append(A)
        if mode.mode == 0:  # iABC
            self._append_arg(mode.argb, B)
            self._append_arg(mode.argc, C)
        elif mode.mode == 1:  # iABx
            if self._opname in ["LOADK", "GETGLOBAL", "SETGLOBAL"]:
                self._args.append(-(Bx + 1))
            else:
                self._args.append(Bx)
        elif mode.mode == 2:  # iAsBx
            self._args.append(sBx)

    def _append_arg(self, arg_type: int, value: int):
        """Get argument representation based on its type."""
        if arg_type != OpArgK:
            if arg_type == OpArgK and value > 255:
                value = 255 - value
            self._args.append(value)

    def update_info(self, constants: list[Value], upvalues: list[String]):
        """Update instruction arguments with constant/upvalue info."""
        for arg in self._args:
            if arg < 0:
                self._comment = str(constants[-(arg + 1)])

        # Special handling for specific opcodes
        if self._opname == "GETUPVAL" or self._opname == "SETUPVAL":
            if self._args[1] < len(upvalues):
                self._comment = str(upvalues[self._args[1]])
    
    def __str__(self) -> str:
        parts = [self._opname.ljust(10)]
        parts.append(f"{self._args[0]} {self._args[1]}")
        if self._comment is not None:
            parts.append(f"; {self._comment}")

        return '\t'.join(parts)

class Code:
    sizecode: int
    codes: list[Instruction]
    
    def __init__(self, file: Reader):
        self.sizecode = file.read_uint32()
        self.codes = [Instruction(file) for _ in range(self.sizecode)]

    def update_info(self, constants: list[Value], upvalues: list[String]):
        for code in self.codes:
            code.update_info(constants, upvalues)

    def __str__(self) -> str:
        return '\n'.join(f"\t{pc + 1}\t{code}" for pc, code in enumerate(self.codes))

class Constants:
    sizek: int
    values: list[Value]
    sizep: int
    subfunctions: list[Function]

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

        self.code.update_info(self.constants.values, self.debug.upvalue_names)

    def __str__(self) -> str:
        parts = []
        parts.append(f"{self.type} <{self.source}:{self.linedefined},{self.lastlinedefined}> ({self.code.sizecode} instructions)")
        parts.append(f"{self.numparams} params, {self.maxstacksize} slots, {self.debug.sizeupvalues} upvalues, {self.debug.sizelocvars} locals, {self.constants.sizek} constants, {self.constants.sizep} functions")
        parts.append(str(self.code))
        parts.append(str(self.constants))
        parts.append(str(self.debug))
        parts.extend(str(sub) for sub in self.constants.subfunctions)

        return '\n' + '\n'.join(parts)

class LuaState:
    stack: list[Value]

    def __init__(self):
        self.stack = []

    def gettop(self) -> int:
        return len(self.stack)
    
    def pop(self, n: int = 1):
        for _ in range(n):
            self.stack.pop()
    
    def copy(self, src: int, desc: int):
        self.stack[desc] = self.stack[src]

    def pushvalue(self, idx: int):
        self.stack.append(self.stack[idx])

    def type(self, idx: int) -> int:
        return self.stack[idx].type
    
    def toboolean(self, idx: int) -> bool:
        value = self.stack[idx]
        return toboolean(value)

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