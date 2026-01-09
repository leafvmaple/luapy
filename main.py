from __future__ import annotations

import inspect
from typing import Optional
from lua_io import Reader
from lua_types import Instruction, Header, Function, Value
from lua_utils import to_boolean
from lua_maths import ARITHS, COMPARE


class Operator:
    @staticmethod
    def MOVE(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        state.stack[a] = state.stack[b]

    @staticmethod
    def LOADK(inst: Instruction, state: LuaState):
        a, bx = inst.abx()
        state.stack[a] = state.func.values[bx]

    @staticmethod
    def LOADBOOL(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        state.stack[a] = Value(value=bool(b))
        if c != 0:
            state.pc += 1

    @staticmethod
    def LOADNIL(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        for i in range(a, b + 1):
            state.stack[i] = Value()

    @staticmethod
    def GETUPVAL(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        # Upvalues not implemented yet
        state.stack[a] = Value()

    @staticmethod
    def GETGLOBAL(inst: Instruction, state: LuaState):
        a, bx = inst.abx()
        # Globals not implemented yet
        state.stack[a] = Value()

    @staticmethod
    def GETTABLE(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        # Tables not implemented yet
        state.stack[a] = Value()

    @staticmethod
    def SETGLOBAL(inst: Instruction, state: LuaState):
        a, bx = inst.abx()
        # Globals not implemented yet
        pass

    @staticmethod
    def SETUPVAL(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        # Upvalues not implemented yet
        pass

    @staticmethod
    def SETTABLE(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        # Tables not implemented yet
        pass

    @staticmethod
    def NEWTABLE(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        # Tables not implemented yet
        state.stack[a] = Value()

    @staticmethod
    def SELF(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        # Self/method call not implemented yet
        state.stack[a] = Value()
        state.stack[a + 1] = Value()

    @staticmethod
    def ADD(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        vb = LuaVM.get_rk(state, b)
        vc = LuaVM.get_rk(state, c)
        vb.to_number()
        vc.to_number()
        if vb.is_number() and vc.is_number():
            state.stack[a] = Value(value=vb.value + vc.value)
        else:
            raise TypeError("ADD operands must be numbers")

    @staticmethod
    def SUB(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        vb = LuaVM.get_rk(state, b)
        vc = LuaVM.get_rk(state, c)
        vb.to_number()
        vc.to_number()
        if vb.is_number() and vc.is_number():
            state.stack[a] = Value(value=vb.value - vc.value)
        else:
            raise TypeError("SUB operands must be numbers")

    @staticmethod
    def MUL(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        vb = LuaVM.get_rk(state, b)
        vc = LuaVM.get_rk(state, c)
        vb.to_number()
        vc.to_number()
        if vb.is_number() and vc.is_number():
            state.stack[a] = Value(value=vb.value * vc.value)
        else:
            raise TypeError("MUL operands must be numbers")

    @staticmethod
    def DIV(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        vb = LuaVM.get_rk(state, b)
        vc = LuaVM.get_rk(state, c)
        vb.to_number()
        vc.to_number()
        if vb.is_number() and vc.is_number():
            state.stack[a] = Value(value=vb.value / vc.value)
        else:
            raise TypeError("DIV operands must be numbers")

    @staticmethod
    def MOD(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        vb = LuaVM.get_rk(state, b)
        vc = LuaVM.get_rk(state, c)
        vb.to_number()
        vc.to_number()
        if vb.is_number() and vc.is_number():
            state.stack[a] = Value(value=vb.value % vc.value)
        else:
            raise TypeError("MOD operands must be numbers")

    @staticmethod
    def POW(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        vb = LuaVM.get_rk(state, b)
        vc = LuaVM.get_rk(state, c)
        vb.to_number()
        vc.to_number()
        if vb.is_number() and vc.is_number():
            state.stack[a] = Value(value=vb.value ** vc.value)
        else:
            raise TypeError("POW operands must be numbers")

    @staticmethod
    def UNM(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        vb = state.stack[b]
        vb.to_number()
        if vb.is_number():
            state.stack[a] = Value(value=-vb.value)
        else:
            raise TypeError("UNM operand must be a number")

    @staticmethod
    def NOT(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        vb = state.stack[b]
        state.stack[a] = Value(value=not to_boolean(vb))

    @staticmethod
    def LEN(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        vb = state.stack[b]
        if vb.is_string():
            state.stack[a] = Value(value=len(vb.value))
        else:
            # Tables not implemented yet
            state.stack[a] = Value(value=0)

    @staticmethod
    def CONCAT(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        strings = []
        for i in range(b, c + 1):
            v = state.stack[i]
            v.to_string()
            if v.is_string():
                strings.append(v.value)
            else:
                raise TypeError("CONCAT operands must be strings or numbers")
        state.stack[a] = Value(value=''.join(strings))

    @staticmethod
    def JMP(inst: Instruction, state: LuaState):
        _, offset = inst.asbx()
        state.pc += offset

    @staticmethod
    def EQ(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        vb = LuaVM.get_rk(state, b)
        vc = LuaVM.get_rk(state, c)
        if (vb.value == vc.value) != (a != 0):
            state.pc += 1

    @staticmethod
    def LT(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        vb = LuaVM.get_rk(state, b)
        vc = LuaVM.get_rk(state, c)
        vb.to_number()
        vc.to_number()
        if (vb.value < vc.value) != (a != 0):
            state.pc += 1

    @staticmethod
    def LE(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        vb = LuaVM.get_rk(state, b)
        vc = LuaVM.get_rk(state, c)
        vb.to_number()
        vc.to_number()
        if (vb.value <= vc.value) != (a != 0):
            state.pc += 1

    @staticmethod
    def TEST(inst: Instruction, state: LuaState):
        a, _, c = inst.abc()
        va = state.stack[a]
        if to_boolean(va) != (c != 0):
            state.pc += 1

    @staticmethod
    def TESTSET(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        vb = state.stack[b]
        if to_boolean(vb) == (c != 0):
            state.stack[a] = vb
        else:
            state.pc += 1

    @staticmethod
    def CALL(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        # Function calls not implemented yet
        pass

    @staticmethod
    def TAILCALL(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        # Tail calls not implemented yet
        pass

    @staticmethod
    def RETURN(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        # Return handling not implemented yet
        pass

    @staticmethod
    def FORLOOP(inst: Instruction, state: LuaState):
        a, sbx = inst.asbx()
        step = state.stack[a + 2]
        idx = state.stack[a]
        limit = state.stack[a + 1]

        step.to_number()
        idx.to_number()
        limit.to_number()

        if step.is_number() and idx.is_number() and limit.is_number():
            idx.value += step.value
            state.stack[a] = idx

            if (step.value > 0 and idx.value <= limit.value) or \
               (step.value <= 0 and idx.value >= limit.value):
                state.pc += sbx
                state.stack[a + 3] = idx
        else:
            raise TypeError("FORLOOP operands must be numbers")

    @staticmethod
    def FORPREP(inst: Instruction, state: LuaState):
        a, sbx = inst.asbx()
        init = state.stack[a]
        step = state.stack[a + 2]

        init.to_number()
        step.to_number()

        if init.is_number() and step.is_number():
            state.stack[a] = Value(value=init.value - step.value)
            state.pc += sbx
        else:
            raise TypeError("FORPREP operands must be numbers")

    @staticmethod
    def TFORLOOP(inst: Instruction, state: LuaState):
        a, _, c = inst.abc()
        # Iterator-based for loops not implemented yet
        pass

    @staticmethod
    def SETLIST(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        # Table list initialization not implemented yet
        pass

    @staticmethod
    def CLOSE(inst: Instruction, state: LuaState):
        a, _, _ = inst.abc()
        # Close upvalues not implemented yet
        pass

    @staticmethod
    def CLOSURE(inst: Instruction, state: LuaState):
        a, bx = inst.abx()
        # Closures not implemented yet
        state.stack[a] = Value()

    @staticmethod
    def VARARG(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        # Varargs not implemented yet
        if b > 1:
            for i in range(b - 1):
                state.stack[a + i] = Value()


class LuaState:
    stack: list[Value]
    func: Function
    pc: int

    def __init__(self, func: Optional[Function] = None):
        self.stack = [Value()] * func.maxstacksize if func is not None else []
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
        self.stack.append(Value(value=b))

    def push_number(self, number: float):
        self.stack.append(Value(value=number))

    def push_string(self, s: str):
        self.stack.append(Value(value=s))

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
            self.stack.append(Value(value=length))
        else:
            raise TypeError("Operand must be a string")

    def concat(self, n: int):
        if n == 0:
            self.stack.append(Value(value=""))
        elif n >= 2:
            strings = []
            for _ in range(n):
                value = self.stack.pop()
                value.to_string()
                if not value.is_string():
                    raise TypeError("All operands must be strings")
                strings.append(value.value)
            result = ''.join(reversed(strings))
            self.stack.append(Value(value=result))

    # debug
    def print_stack(self):
        print(f'{self.func.codes[self.pc - 1].op_name().ljust(10)}' + ''.join(f"[{v}]" for v in self.stack))

    def _abs_idx(self, idx: int) -> int:
        if idx >= 0:
            return idx
        return len(self.stack) + idx


class LuaVM:
    @staticmethod
    def fetch(state: LuaState) -> Optional[Instruction]:
        if state.pc >= len(state.func.codes):
            return None
        instrution = state.func.codes[state.pc]
        state.pc += 1
        return instrution

    @staticmethod
    def excute(state: LuaState) -> bool:
        inst = LuaVM.fetch(state)
        if inst is None:
            return False
        op_name = inst.op_name()
        method = getattr(Operator, op_name, None)
        if method:
            method(inst, state)
        # else:
        #     raise NotImplementedError(f"Operator {op_name} not implemented")
        return True

    @staticmethod
    def get_rk(state: LuaState, rk: int) -> Value:
        """Get RK value: if rk >= 256, it's a constant index; otherwise it's a register"""
        if rk >= 256:
            # It's a constant (k)
            return state.func.values[rk - 256]
        else:
            # It's a register (r)
            return state.stack[rk]


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
    while LuaVM.excute(state):
        state.print_stack()
