from __future__ import annotations

from enum import Enum
from typing import Optional

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


class Instruction:
    instruction: int

    _opcode: int
    _opname: int
    _a: int
    _b: int
    _c: int
    _bx: int
    _sbx: int

    _args: list[int]
    _comment: list[str]

    def __init__(self, file: Reader):
        self._args = []
        self._comment = []

        self.instruction = file.read_uint32()

    def op_name(self) -> str:
        return self._opname

    def abc(self) -> tuple[int, int, int]:
        """Return A, B, C arguments, with None as default for missing values."""
        return self._a, self._b, self._c

    def abx(self) -> tuple[int, int]:
        return self._a, self._bx

    def asbx(self) -> tuple[int, int]:
        return self._a, self._sbx

    def _append_arg(self, arg_type: int, value: int, constants: list[Value]):
        """Get argument representation based on its type."""
        if arg_type != OpArgN:
            if arg_type == OpArgK and value > 255:
                self._comment.append(str(constants[value - 256]))
                value = 255 - value
            self._args.append(value)

    def update_info(self, pc, constants: list[Value], upvalues: list[str]):
        """Update instruction arguments with constant/upvalue info."""
        # Decode instruction
        self._opcode = self.instruction & 0x3F  # bits 0-5
        self._a = (self.instruction >> 6) & 0xFF  # bits 6-13
        self._c = (self.instruction >> 14) & 0x1FF  # bits 14-22
        self._b = (self.instruction >> 23) & 0x1FF  # bits 23-31
        self._bx = (self.instruction >> 14) & 0x3FFFF  # bits 14-31
        self._sbx = self._bx - 131071  # signed Bx

        self._opname = OPCODES[self._opcode]
        mode = OPMODES[self._opcode]

        self._args.append(self._a)
        if mode.mode == 0:  # iABC
            self._append_arg(mode.argb, self._b, constants)
            self._append_arg(mode.argc, self._c, constants)
        elif mode.mode == 1:  # iABx
            if self._opname in ["LOADK", "GETGLOBAL", "SETGLOBAL"]:
                self._comment.append(str(constants[self._bx]))
                self._args.append(-(self._bx + 1))
            else:
                self._args.append(self._bx)
        elif mode.mode == 2:  # iAsBx
            self._args.append(self._sbx)
            self._comment.append(f"to {self._sbx + pc + 2}")

        # Special handling for specific opcodes
        if self._opname == "GETUPVAL" or self._opname == "SETUPVAL":
            if self._args[1] < len(upvalues):
                self._comment.append(upvalues[self._args[1]])

    def __str__(self) -> str:
        parts = [self._opname.ljust(10)]
        parts.append(' '.join(str(arg) for arg in self._args))
        if len(self._comment) > 0:
            parts.append(f"; {' '.join(self._comment)}")

        return '\t'.join(parts)


class LUA_TYPE(Enum):
    NIL = 0
    BOOLEAN = 1
    LIGHTUSERDATA = 2
    NUMBER = 3
    STRING = 4
    TABLE = 5
    FUNCTION = 6
    USERDATA = 7
    THREAD = 8


class Value:
    value: str | float | int | bool | Table | LClosure | None = None

    def __init__(self, value: str | float | int | bool | Table | LClosure | None = None, file: Reader = None):
        if value is not None:
            self.value = value
        elif file is not None:
            _type = LUA_TYPE(file.read_uint8())
            if _type == LUA_TYPE.NIL:
                self.value = None
            elif _type == LUA_TYPE.BOOLEAN:
                self.value = file.read_uint8() != 0
            elif _type == LUA_TYPE.NUMBER:
                self.value = file.read_double()
            elif _type == LUA_TYPE.STRING:
                self.value = file.read_string()
            else:
                raise ValueError(f"Unknown constant type: {_type}")

        if isinstance(self.value, float):
            if self.value.is_integer():
                self.value = int(self.value)

    def to_string(self):
        if self.is_number():
            self.value = str(self.value)

    def string_to_number(self):
        if self.is_string():
            self.value = float(self.value)
            if self.value.is_integer():
                self.value = int(self.value)

    def float_to_integer(self):
        if type(self.value) is float and self.value.is_integer():
            self.value = int(self.value)

    def is_nil(self) -> bool:
        return self.value is None

    def is_boolean(self) -> bool:
        return type(self.value) is bool

    def is_number(self) -> bool:
        return type(self.value) in (int, float)

    def is_string(self) -> bool:
        return type(self.value) is str

    def is_table(self) -> bool:
        return type(self.value) is Table

    def is_function(self) -> bool:
        return type(self.value) in (LClosure, PClosure)

    def type_name(self) -> str:
        if self.is_nil():
            return 'nil'
        elif self.is_boolean():
            return 'boolean'
        elif self.is_number():
            return 'number'
        elif self.is_string():
            return 'string'
        elif self.is_table():
            return 'table'
        elif self.is_function():
            return 'function'
        return 'unknown'

    def to_boolean(self) -> bool:
        if self.is_nil():
            return False
        if self.is_boolean():
            return self.value
        return True

    def get_integer(self) -> int | None:
        if type(self.value) is int:
            return self.value
        if type(self.value) is float:
            if self.value.is_integer():
                return int(self.value)
        return None

    def get_string(self) -> Optional[str]:
        if self.is_number():
            return str(self.value)
        if self.is_string():
            return self.value
        return None

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other: Value) -> bool:
        return self.value == other.value

    def __str__(self) -> str:
        if self.is_nil():
            return 'nil'
        elif self.is_boolean():
            return 'true' if self.value else 'false'
        elif self.is_string():
            return f'"{self.value}"'
        elif self.is_table():
            return 'table'
        elif self.is_function():
            return 'function'
        return str(self.value)


class Table:
    _list: list[Value]
    _map: dict[Value | int, Value]

    def __init__(self):
        self._list = []
        self._map = {}

    def get(self, key: int | Value) -> Optional[Value]:
        int_key = key.get_integer() if type(key) is Value else key
        if int_key is not None:
            if 1 <= int_key <= len(self._list):
                return self._list[int_key - 1]
            return self._map.get(int_key, None)
        return self._map.get(key, None)

    def set(self, key: int | Value, value: Value):
        int_key = key.get_integer() if type(key) is Value else key
        if value.is_nil():
            if int_key is not None:
                if 1 <= int_key <= len(self._list):
                    self._shrink_list(int_key)
            elif key in self._map:
                del self._map[key]
        else:
            if int_key is not None:
                if int_key == len(self._list) + 1:
                    self._list.append(value)
                    self._expand_list()
                elif 1 <= int_key <= len(self._list):
                    self._list[int_key - 1] = value
                else:
                    self._map[int_key] = value
            else:
                self._map[key] = value

    def len(self) -> int:
        return len(self._list)

    def _shrink_list(self, key: int):
        for lua_idx in range(key + 1, len(self._list) + 1):
            self._map[lua_idx] = self._list[lua_idx - 1]
        self._list = self._list[:key - 1]

    def _expand_list(self):
        while (len(self._list) + 1) in self._map:
            key = len(self._list) + 1
            self._list.append(self._map[key])
            del self._map[key]


class LocalVar:
    name: str
    startpc: int
    endpc: int

    def __init__(self, file: Reader):
        self.name = file.read_string()
        self.startpc = file.read_uint32()
        self.endpc = file.read_uint32()

    def __str__(self) -> str:
        return f"{self.name}\t{self.startpc + 1}\t{self.endpc + 1}"


class Debug:
    lineinfos: list[int]
    locvars: list[LocalVar]
    upvalues: list[str]

    def __init__(self, file: Reader):
        sizelineinfo = file.read_uint32()
        self.lineinfos = [file.read_uint32() for _ in range(sizelineinfo)]
        sizelocvars = file.read_uint32()
        self.locvars = [LocalVar(file) for _ in range(sizelocvars)]
        sizeupvalues = file.read_uint32()
        self.upvalues = [file.read_string() for _ in range(sizeupvalues)]

    def __str__(self) -> str:
        parts = []
        parts.append(f'locals ({len(self.locvars)}):')
        parts.extend(f"\t{i}\t{value}" for i, value in enumerate(self.locvars))

        parts.append(f'upvalues ({len(self.upvalues)}):')
        parts.extend(f"\t{i}\t{value}" for i, value in enumerate(self.upvalues))

        return '\n'.join(parts)


class Proto:
    source: str
    type: str = "main"
    linedefined: int
    lastlinedefined: int
    nups: int
    numparams: int
    is_vararg: bool
    maxstacksize: int
    codes: list[Instruction]
    consts: list[Value]
    protos: list[Proto]
    debug: Debug

    def __init__(self, file: Reader, parent: Optional[str] = None):
        self.source = file.read_string()
        if parent is not None:
            self.source = parent  # type: ignore
            self.type = "function"
        self.linedefined = file.read_uint32()
        self.lastlinedefined = file.read_uint32()
        self.nups = file.read_uint8()
        self.numparams = file.read_uint8()
        self.is_vararg = file.read_uint8() != 0
        self.maxstacksize = file.read_uint8()

        # Code
        sizecode = file.read_uint32()
        self.codes = [Instruction(file) for _ in range(sizecode)]

        # Constants
        sizek = file.read_uint32()
        self.consts = [Value(file=file) for _ in range(sizek)]
        sizep = file.read_uint32()
        self.protos = [Proto(file, self.source) for _ in range(sizep)]

        self.debug = Debug(file)

        for pc, code in enumerate(self.codes):
            code.update_info(pc, self.consts, self.debug.upvalues)

    def __str__(self) -> str:
        parts = []
        parts.append(f"{self.type} <{self.source}:{self.linedefined},{self.lastlinedefined}> ({len(self.codes)} instructions)")
        parts.append(f"{self.numparams} params, {self.maxstacksize} slots, {len(self.debug.upvalues)} upvalues, \
                     {len(self.debug.locvars)} locals, {len(self.consts)} constants, {len(self.protos)} functions")
        parts.extend(f"\t{pc + 1}\t{code}" for pc, code in enumerate(self.codes))
        parts.append(f'constants ({len(self.consts)}):')
        parts.extend(f"\t{i + 1}\t{value}" for i, value in enumerate(self.consts))
        parts.append(str(self.debug))
        parts.extend(str(sub) for sub in self.protos)

        return '\n' + '\n'.join(parts)

class Closure:
    stack: list[Value]
    upvalues: list[Value]

class LClosure(Closure):
    varargs: list[Value]
    func: Proto
    nrets: int  # number of expected return values
    ret_idx: int
    pc: int

    def __init__(self, func: Proto = None):
        self.stack = [Value()] * func.maxstacksize
        self.upvalues = [Value()] * func.nups  # Initialize upvalues based on function prototype
        self.varargs = []
        self.func = func
        self.nrets = 0
        self.ret_idx = 0
        self.pc = 0

    def fetch(self) -> Optional[Instruction]:
        if self.pc >= len(self.func.codes):
            return None
        instrution = self.func.codes[self.pc]
        self.pc += 1
        return instrution

    # debug
    def print_stack(self):
        pass
        # print(f'{self.func.codes[self.pc - 1].op_name().ljust(10)}' + ''.join(f"[{v}]" for v in self.stack))


class PClosure(Closure):
    func: callable

    def __init__(self, func: callable):
        self.func = func
        self.stack = []
        self.varargs = []
