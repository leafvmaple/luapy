from __future__ import annotations
from typing import TYPE_CHECKING

from lua_io import Reader
if TYPE_CHECKING:
    from lua_value import Value


# Instruction argument modes
OpArgN = 0  # argument is not used
OpArgU = 1  # argument is used
OpArgR = 2  # argument is a register or a jump offset
OpArgK = 3  # argument is a constant or register/constant

# Instruction formats: iABC, iABx, iAsBx
iABC, iABx, iAsBx = 0, 1, 2


class OpCode:
    """Lua 5.1 opcode definition with mode information."""
    def __init__(self, name: str, testflag: int, setareg: int, argb: int, argc: int, mode: int):
        self.name = name
        self.testflag = testflag  # operator is a test (next instruction must be a jump)
        self.setareg = setareg    # instruction set register A
        self.argb = argb          # B arg mode
        self.argc = argc          # C arg mode
        self.mode = mode          # op mode (iABC=0, iABx=1, iAsBx=2)


# Lua 5.1 opcodes with their properties
# OpCode(name, testflag, setareg, argb, argc, mode)
OPCODES = [
    OpCode("MOVE",      0, 1, OpArgR, OpArgN, iABC),
    OpCode("LOADK",     0, 1, OpArgK, OpArgN, iABx),
    OpCode("LOADBOOL",  0, 1, OpArgU, OpArgU, iABC),
    OpCode("LOADNIL",   0, 1, OpArgU, OpArgN, iABC),
    OpCode("GETUPVAL",  0, 1, OpArgU, OpArgN, iABC),
    OpCode("GETGLOBAL", 0, 1, OpArgK, OpArgN, iABx),
    OpCode("GETTABLE",  0, 1, OpArgR, OpArgK, iABC),
    OpCode("SETGLOBAL", 0, 0, OpArgK, OpArgN, iABx),
    OpCode("SETUPVAL",  0, 0, OpArgU, OpArgN, iABC),
    OpCode("SETTABLE",  0, 0, OpArgK, OpArgK, iABC),
    OpCode("NEWTABLE",  0, 1, OpArgU, OpArgU, iABC),
    OpCode("SELF",      0, 1, OpArgR, OpArgK, iABC),
    OpCode("ADD",       0, 1, OpArgK, OpArgK, iABC),
    OpCode("SUB",       0, 1, OpArgK, OpArgK, iABC),
    OpCode("MUL",       0, 1, OpArgK, OpArgK, iABC),
    OpCode("DIV",       0, 1, OpArgK, OpArgK, iABC),
    OpCode("MOD",       0, 1, OpArgK, OpArgK, iABC),
    OpCode("POW",       0, 1, OpArgK, OpArgK, iABC),
    OpCode("UNM",       0, 1, OpArgR, OpArgN, iABC),
    OpCode("NOT",       0, 1, OpArgR, OpArgN, iABC),
    OpCode("LEN",       0, 1, OpArgR, OpArgN, iABC),
    OpCode("CONCAT",    0, 1, OpArgR, OpArgR, iABC),
    OpCode("JMP",       0, 0, OpArgR, OpArgN, iAsBx),
    OpCode("EQ",        1, 0, OpArgK, OpArgK, iABC),
    OpCode("LT",        1, 0, OpArgK, OpArgK, iABC),
    OpCode("LE",        1, 0, OpArgK, OpArgK, iABC),
    OpCode("TEST",      1, 0, OpArgN, OpArgU, iABC),
    OpCode("TESTSET",   1, 1, OpArgR, OpArgU, iABC),
    OpCode("CALL",      0, 1, OpArgU, OpArgU, iABC),
    OpCode("TAILCALL",  0, 1, OpArgU, OpArgU, iABC),
    OpCode("RETURN",    0, 0, OpArgU, OpArgN, iABC),
    OpCode("FORLOOP",   0, 1, OpArgR, OpArgN, iAsBx),
    OpCode("FORPREP",   0, 1, OpArgR, OpArgN, iAsBx),
    OpCode("TFORLOOP",  0, 0, OpArgN, OpArgU, iABC),
    OpCode("SETLIST",   0, 0, OpArgU, OpArgU, iABC),
    OpCode("CLOSE",     0, 0, OpArgN, OpArgN, iABC),
    OpCode("CLOSURE",   0, 1, OpArgU, OpArgN, iABx),
    OpCode("VARARG",    0, 1, OpArgU, OpArgN, iABC),
]


class Instruction:
    instruction: int
    _opcode_idx: int
    _opcode: OpCode
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
        # Decode instruction
        self._opcode_idx = self.instruction & 0x3F  # bits 0-5
        self._opcode = OPCODES[self._opcode_idx]
        self._a = (self.instruction >> 6) & 0xFF  # bits 6-13
        self._c = (self.instruction >> 14) & 0x1FF  # bits 14-22
        self._b = (self.instruction >> 23) & 0x1FF  # bits 23-31
        self._bx = (self.instruction >> 14) & 0x3FFFF  # bits 14-31
        self._sbx = self._bx - (0x3FFFF >> 1)  # signed Bx (convert 18-bit unsigned to signed)

    def op_name(self) -> str:
        return self._opcode.name

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
        self._args.append(self._a)
        
        if self._opcode.mode == iABC:
            self._append_arg(self._opcode.argb, self._b, constants)
            self._append_arg(self._opcode.argc, self._c, constants)
        elif self._opcode.mode == iABx:
            if self._opcode.name in ["LOADK", "GETGLOBAL", "SETGLOBAL"]:
                self._comment.append(str(constants[self._bx]))
                self._args.append(-(self._bx + 1))
            else:
                self._args.append(self._bx)
        elif self._opcode.mode == iAsBx:
            self._args.append(self._sbx)
            self._comment.append(f"to {self._sbx + pc + 2}")

        # Special handling for specific opcodes
        if self._opcode.name in ["GETUPVAL", "SETUPVAL"]:
            if self._args[1] < len(upvalues):
                self._comment.append(upvalues[self._args[1]])

    def __str__(self) -> str:
        parts = [self._opcode.name.ljust(10)]
        parts.append(' '.join(str(arg) for arg in self._args))
        if len(self._comment) > 0:
            parts.append(f"; {' '.join(self._comment)}")

        return '\t'.join(parts)