from __future__ import annotations

import inspect
from typing import Optional
from lua_io import Reader
from lua_types import Instruction, Header, Function, Value
from lua_utils import to_boolean
from lua_maths import ARITHS, COMPARE

def move(inst: Instruction, state: LuaState):
    a, b, _ = inst.abc()
    state.check_stack(a)
    state.stack[a] = state.stack[b]

def load_nil(inst: Instruction, state: LuaState):
    a, b, _ = inst.abc()
    state.check_stack(a + b)
    for i in range(b + 1):
        state.stack[a + i] = Value()

def load_k(inst: Instruction, state: LuaState):
    a, b, _ = inst.abc()
    state.check_stack(a)
    state.stack[a] = state.func.values[-(b + 1)]

def jmp(inst: Instruction, state: LuaState):
    offset = inst.sbx()
    state.pc += offset

OPERATOR = {
    "MOVE": lambda inst, state: move(inst, state),
    "LOADNIL": lambda inst, state: load_nil(inst, state),
    "LOADK": lambda inst, state: load_k(inst, state),
    "JMP": lambda inst, state: jmp(inst, state),
}

class LuaState:
    stack: list[Value]
    func: Function
    pc: int

    def __init__(self, func: Optional[Function] = None):
        self.stack = []
        self.func = func
        self.pc = 0

    def get_top(self) -> int:
        return len(self.stack)
    
    def set_top(self, idx: int):
        while len(self.stack) > idx:
            self.stack.pop()
        while len(self.stack) < idx:
            self.stack.append(Value())
    
    def push(self, value: Value):
        self.stack.append(value)
    
    def pop(self, n: int = 1):
        for _ in range(n):
            self.stack.pop()
    
    def copy(self, src: int, desc: int):
        self.stack[desc] = self.stack[src]

    def replace(self, idx: int):
        idx = self._abs_idx(idx)
        self.stack[idx - 1] = self.stack.pop()

    def check_stack(self, n: int):
        if n >= len(self.stack):
            self.stack.extend([Value()] * (n - len(self.stack) + 1))

    def push_value(self, idx: int):
        idx = self._abs_idx(idx)
        self.stack.append(self.stack[idx - 1])

    def typ_ename(self, idx: int) -> str:
        return self.stack[idx - 1].type_name()
    
    def to_boolean(self, idx: int) -> bool:
        value = self.stack[idx - 1]
        return to_boolean(value)
    
    def to_number(self, idx: int) -> Optional[float]:
        value = self.stack[idx - 1]
        if value.is_number():
            return value.value
        return None
    
    def to_string(self, idx: int) -> Optional[str]:
        self.stack[idx - 1].to_string()
        value = self.stack[idx - 1]
        if value.is_string():
            return value.value
        return None
    
    def push_nil(self):
        self.stack.append(Value())

    def push_boolean(self, b: bool):
        self.stack.append(Value(value= b))
    
    def push_number(self, number: float):
        self.stack.append(Value(value= number))

    def push_string(self, s: str):
        self.stack.append(Value(value= s))

    def arith(self, op: str):
        operator = ARITHS[op]
        num_params = len(inspect.signature(operator).parameters)
        
        a = self.stack.pop()
        a.to_number()
        if not a.is_number():
            raise TypeError("Operand must be a number")
        if num_params == 1:
            result = operator(a.value)
        elif num_params == 2:
            b = self.stack.pop()
            b.to_number()
            if not b.is_number():
                raise TypeError("Both operands must be numbers")
            result = operator(a.value, b.value)
        
        self.stack.append(Value(value=result))

    def compare(self, idx1: int, idx2: int, op: str) -> bool:
        operator = COMPARE[op]
        a = self.stack[idx1 - 1]
        b = self.stack[idx2 - 1]
        a.to_number()
        b.to_number()
        if not a.is_number() or not b.is_number():
            raise TypeError("Both operands must be numbers")
        return operator(a.value, b.value)
    
    def len(self, idx: int):
        value = self.stack[idx - 1]
        if value.is_string():
            length = len(value.value)
            self.stack.append(Value(value= length))
        else:
            raise TypeError("Operand must be a string")
        
    def concat(self, n: int):
        if n == 0:
            self.stack.append(Value(value= ""))
        elif n >= 2:
            strings = []
            for _ in range(n):
                value = self.stack.pop()
                value.to_string()
                if not value.is_string():
                    raise TypeError("All operands must be strings")
                strings.append(value.value)
            result = ''.join(reversed(strings))
            self.stack.append(Value(value= result))

    # debug
    def print_stack(self):
        print(''.join(f"[{v}]" for v in self.stack))

    def _abs_idx(self, idx: int) -> int:
        if idx >= 0:
            return idx
        return len(self.stack) + idx

class LuaVM:
    @staticmethod
    @staticmethod
    def fetch(state: LuaState) -> Instruction:
        instrution = state.func.codes[state.pc]
        state.pc += 1
        return instrution

    @staticmethod
    def excute(state: LuaState):
        inst = LuaVM.fetch(state)
        op_name = inst.op_name()
        if op_name in OPERATOR:
            OPERATOR[op_name](inst, state)
        else:
            raise NotImplementedError(f"Operator {op_name} not implemented")

    def get_rk(state: LuaState, rk: int) -> Value:
        pass


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

    state = LuaState(pylua_file.main)
    LuaVM.excute(state)
    state.print_stack()
    LuaVM.excute(state)
    state.print_stack()
    LuaVM.excute(state)
    state.print_stack()
    
