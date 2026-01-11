from __future__ import annotations

from typing import Optional
from lua_io import Reader
from lua_types import LClosure, PClosure, Instruction, Header, Proto, Table, Value


LUA_GLOBALS_INDEX = -10002


def lua_print(state: LuaState) -> list[Value]:
    n = state.get_top()
    outputs = []
    for i in range(n):
        outputs.append(str(state.stack[i]))
    print('\t'.join(outputs))
    return []


class Operator:
    @staticmethod
    def MOVE(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        state.stack[a] = state.stack[b]

    @staticmethod
    def LOADK(inst: Instruction, state: LuaState):
        a, bx = inst.abx()
        state.stack[a] = state.func.consts[bx]

    @staticmethod
    def LOADBOOL(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        state.stack[a] = Value(value=bool(b))
        if c != 0:
            state.call_info[-1].pc += 1

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
        name = state.func.consts[bx].value
        state.stack[a] = state.get_global(name)

    @staticmethod
    def GETTABLE(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        table_value = state.stack[b]
        key = LuaVM.get_rk(state, c)
        if table_value.is_table():
            result = table_value.value.get(key)
            state.stack[a] = result if result is not None else Value()
        else:
            raise TypeError("GETTABLE requires a table")

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
        table_value = state.stack[a]
        key = LuaVM.get_rk(state, b)
        value = LuaVM.get_rk(state, c)
        if table_value.is_table():
            table_value.value.set(key, value)
        else:
            raise TypeError("SETTABLE requires a table")

    @staticmethod
    def NEWTABLE(inst: Instruction, state: LuaState):
        a, _, _ = inst.abc()
        state.stack[a] = Value(value=Table())

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
        vb.string_to_number()
        vc.string_to_number()
        if vb.is_number() and vc.is_number():
            state.stack[a] = Value(value=vb.value + vc.value)
        else:
            raise TypeError("ADD operands must be numbers")

    @staticmethod
    def SUB(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        vb = LuaVM.get_rk(state, b)
        vc = LuaVM.get_rk(state, c)
        vb.string_to_number()
        vc.string_to_number()
        if vb.is_number() and vc.is_number():
            state.stack[a] = Value(value=vb.value - vc.value)
        else:
            raise TypeError("SUB operands must be numbers")

    @staticmethod
    def MUL(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        vb = LuaVM.get_rk(state, b)
        vc = LuaVM.get_rk(state, c)
        vb.string_to_number()
        vc.string_to_number()
        if vb.is_number() and vc.is_number():
            state.stack[a] = Value(value=vb.value * vc.value)
        else:
            raise TypeError("MUL operands must be numbers")

    @staticmethod
    def DIV(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        vb = LuaVM.get_rk(state, b)
        vc = LuaVM.get_rk(state, c)
        vb.string_to_number()
        vc.string_to_number()
        if vb.is_number() and vc.is_number():
            state.stack[a] = Value(value=vb.value / vc.value)
        else:
            raise TypeError("DIV operands must be numbers")

    @staticmethod
    def MOD(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        vb = LuaVM.get_rk(state, b)
        vc = LuaVM.get_rk(state, c)
        vb.string_to_number()
        vc.string_to_number()
        if vb.is_number() and vc.is_number():
            state.stack[a] = Value(value=vb.value % vc.value)
        else:
            raise TypeError("MOD operands must be numbers")

    @staticmethod
    def POW(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        vb = LuaVM.get_rk(state, b)
        vc = LuaVM.get_rk(state, c)
        vb.string_to_number()
        vc.string_to_number()
        if vb.is_number() and vc.is_number():
            state.stack[a] = Value(value=vb.value ** vc.value)
        else:
            raise TypeError("POW operands must be numbers")

    @staticmethod
    def UNM(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        vb = state.stack[b]
        vb.string_to_number()
        if vb.is_number():
            state.stack[a] = Value(value=-vb.value)
        else:
            raise TypeError("UNM operand must be a number")

    @staticmethod
    def NOT(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        vb = state.stack[b]
        state.stack[a] = Value(value=not vb.to_boolean())

    @staticmethod
    def LEN(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        vb = state.stack[b]
        if vb.is_string():
            state.stack[a] = Value(value=len(vb.value))
        elif vb.is_table():
            state.stack[a] = Value(value=vb.value.len())
        else:
            raise TypeError("LEN operand must be a string or table")

    @staticmethod
    def CONCAT(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        strings = []
        for i in range(b, c + 1):
            v = state.stack[i]
            s = v.get_string()
            if s:
                strings.append(s)
            else:
                raise TypeError("CONCAT operands must be strings or numbers")
        state.stack[a] = Value(value=''.join(strings))

    @staticmethod
    def JMP(inst: Instruction, state: LuaState):
        _, offset = inst.asbx()
        state.jump(offset)

    @staticmethod
    def EQ(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        vb = LuaVM.get_rk(state, b)
        vc = LuaVM.get_rk(state, c)
        if (vb.value == vc.value) != (a != 0):
            state.jump(1)

    @staticmethod
    def LT(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        vb = LuaVM.get_rk(state, b)
        vc = LuaVM.get_rk(state, c)
        vb.string_to_number()
        vc.string_to_number()
        if (vb.value < vc.value) != (a != 0):
            state.jump(1)

    @staticmethod
    def LE(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        vb = LuaVM.get_rk(state, b)
        vc = LuaVM.get_rk(state, c)
        vb.string_to_number()
        vc.string_to_number()
        if (vb.value <= vc.value) != (a != 0):
            state.jump(1)

    @staticmethod
    def TEST(inst: Instruction, state: LuaState):
        a, _, c = inst.abc()
        va = state.stack[a]
        if va.to_boolean() != (c != 0):
            state.jump(1)

    @staticmethod
    def TESTSET(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        vb = state.stack[b]
        if vb.to_boolean() == (c != 0):
            state.stack[a] = vb
        else:
            state.jump(1)

    @staticmethod
    def CALL(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        # a: 函数在栈中的位置
        # b: 参数个数 + 1 (0表示从a+1到栈顶都是参数)
        # c: 返回值个数 + 1 (0表示保留所有返回值)

        func_value = state.stack[a]
        if not func_value.is_function():
            raise TypeError("CALL requires a function")
        
        nargs = b - 1 if b > 0 else len(state.stack) - a - 1

        if type(func_value.value) is LClosure:
            nargs = b - 1 if b > 0 else len(state.stack) - a - 1
            state.prepare_call(func_value.value, a, nargs, c - 1)
        else:
            state.py_call(func_value.value, a, nargs, c - 1)

    @staticmethod
    def TAILCALL(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        # Tail calls not implemented yet
        pass

    @staticmethod
    def RETURN(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        state.return_from_call(a, b - 1)

    @staticmethod
    def FORLOOP(inst: Instruction, state: LuaState):
        a, sbx = inst.asbx()
        step = state.stack[a + 2]
        idx = state.stack[a]
        limit = state.stack[a + 1]

        step.string_to_number()
        idx.string_to_number()
        limit.string_to_number()

        if step.is_number() and idx.is_number() and limit.is_number():
            idx.value += step.value
            state.stack[a] = idx

            if (step.value > 0 and idx.value <= limit.value) or \
               (step.value <= 0 and idx.value >= limit.value):
                state.jump(sbx)
                state.stack[a + 3] = idx
        else:
            raise TypeError("FORLOOP operands must be numbers")

    @staticmethod
    def FORPREP(inst: Instruction, state: LuaState):
        a, sbx = inst.asbx()
        init = state.stack[a]
        step = state.stack[a + 2]

        init.string_to_number()
        step.string_to_number()

        if init.is_number() and step.is_number():
            state.stack[a] = Value(value=init.value - step.value)
            state.jump(sbx)
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
        table_value = state.stack[a]

        if not table_value.is_table():
            raise TypeError("SETLIST requires a table")

        # LFIELDS_PER_FLUSH in Lua 5.1 is 50
        LFIELDS_PER_FLUSH = 50

        # If c == 0, the actual c value is in the next instruction
        if c == 0:
            c = state.fetch().instruction

        # Calculate starting index: (c-1) * 50 + 1
        idx = (c - 1) * LFIELDS_PER_FLUSH

        # If b == 0, set all values from A+1 to top of stack
        if b == 0:
            b = len(state.stack) - a - 1

        # Set values from stack[a+1] to stack[a+b] into table
        for i in range(1, b + 1):
            value = state.stack[a + i]
            table_value.value.set(idx + i, value)

    @staticmethod
    def CLOSE(inst: Instruction, state: LuaState):
        a, _, _ = inst.abc()
        # Close upvalues not implemented yet
        pass

    @staticmethod
    def CLOSURE(inst: Instruction, state: LuaState):
        a, bx = inst.abx()
        # 获取子函数原型
        proto = state.func.protos[bx]
        # 创建闭包（暂时不处理upvalues）
        state.stack[a] = Value(value=LClosure(proto))

    @staticmethod
    def VARARG(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        varargs = state.call_info[-1].varargs
        if b == 0:
            b = len(varargs) + 1
        for i in range(b - 1):
            state.stack[a + i] = varargs[i]


class LuaState:
    call_info: list[LClosure | PClosure]
    func: Proto
    stack: list[Value]
    registry: Table
    globals: Table

    def __init__(self, main: Proto):
        self.call_info = [LClosure(main)]
        self.registry = Table()
        self.registry.set(Value(LUA_GLOBALS_INDEX), Value(value=Table()))
        self.globals = self.registry.get(Value(LUA_GLOBALS_INDEX)).value

        self.func = self.call_info[-1].func
        self.stack = self.call_info[-1].stack

        self.register("print", lua_print)

    def get_top(self) -> int:
        return len(self.stack)

    def set_top(self, idx: int):
        while len(self.stack) > idx:
            self.stack.pop()
        while len(self.stack) < idx:
            self.stack.append(Value())

    def get_global(self, name: str) -> Value:
        key = Value(value=name)
        value = self.globals.get(key)
        return value if value is not None else Value()

    def set_global(self, name: str, value: Value):
        key = Value(value=name)
        self.globals.set(key, value)

    def push_closure(self, closure: LClosure | PClosure):
        self.call_info.append(closure)
        self.func = self.call_info[-1].func
        self.stack = self.call_info[-1].stack

    def pop_closure(self) -> LClosure:
        frame = self.call_info.pop()
        if len(self.call_info) > 0:
            self.func = self.call_info[-1].func
            self.stack = self.call_info[-1].stack
        return frame

    def register(self, name: str, func: callable):
        self.globals.set(Value(value=name), Value(value=PClosure(func)))

    def prepare_call(self, closure: LClosure, func_idx: int = 0, args_count: int = 0, nrets: int = 0):
        for i in range(args_count):
            value = self.stack[func_idx + 1 + i]
            if i < closure.func.numparams:
                closure.stack[i] = value
            else:
                closure.varargs.append(value)

        closure.nrets = nrets
        closure.ret_idx = func_idx
        self.push_closure(closure)

    def py_call(self, closure: PClosure, func_idx: int = 0, args_count: int = 0, nrets: int = 0):
        for i in range(args_count):
            value = self.stack[func_idx + 1 + i]
            closure.stack.append(value)

        self.push_closure(closure)
        rets = closure.func(self)
        self.pop_closure()

        ret_count = len(rets)

        for i in range(nrets):
            ret_value = rets[i] if i < ret_count else Value()
            self.stack.append(ret_value)

    def return_from_call(self, ret_start, ret_count: int = 0):
        closure = self.pop_closure()

        if len(self.call_info) == 0:
            return

        # Handle return values
        if ret_count == -1:
            ret_count = len(closure.stack) - ret_start

        for i in range(closure.nrets):
            ret_value = closure.stack[ret_start + i] if i < ret_count else Value()
            self.stack[closure.ret_idx + i] = ret_value

    def jump(self, offset: int):
        self.call_info[-1].pc += offset

    def fetch(self) -> Optional[Instruction]:
        if len(self.call_info) == 0:
            return None
        return self.call_info[-1].fetch()

    # debug
    def print_stack(self):
        pass
        # self.call_info[-1].print_stack()


class LuaVM:
    @staticmethod
    def fetch(state: LuaState) -> Optional[Instruction]:
        return state.fetch()

    @staticmethod
    def excute(state: LuaState) -> bool:
        inst = LuaVM.fetch(state)
        if inst is None:
            return False
        op_name = inst.op_name()
        method = getattr(Operator, op_name, None)
        if method:
            method(inst, state)
            print(f'{op_name.ljust(10)}' + ''.join(f"[{v}]" for v in state.stack))
        # else:
        #     raise NotImplementedError(f"Operator {op_name} not implemented")
        return True

    @staticmethod
    def get_rk(state: LuaState, rk: int) -> Value:
        """Get RK value: if rk >= 256, it's a constant index; otherwise it's a register"""
        if rk >= 256:
            # It's a constant (k)
            return state.func.consts[rk - 256]
        else:
            # It's a register (r)
            return state.stack[rk]


class PyLua:
    reader: Reader
    header: Header
    main: Proto

    def __init__(self, file_path: str):
        with open(file_path, 'rb') as f:
            self.reader = Reader(f)
            self.header = Header(self.reader)
            self.main = Proto(self.reader)

    def __str__(self) -> str:
        return f"{self.main}"


if __name__ == "__main__":
    pylua_file = PyLua("test.luac")
    print(pylua_file)

    state = LuaState(pylua_file.main)
    while LuaVM.excute(state):
        state.print_stack()
    pass
