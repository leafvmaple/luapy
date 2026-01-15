from __future__ import annotations

from typing import Optional
from lua_io import Reader
from lua_types import LClosure, PClosure, Instruction, Header, Proto, Table, Value


LUA_GLOBALS_INDEX = -10002


class CheckNumber:
    @staticmethod
    def check(val: Value) -> bool:
        val.conv_str_to_number()
        if val.is_number():
            return True
        return False
    
    def checks(va: Value, vb: Value) -> bool:
        return CheckNumber.check(va) and CheckNumber.check(vb)
    
class CompareCheck:
    @staticmethod
    def checks(va: Value, vb: Value) -> bool:
        if va.is_number() and vb.is_number():
            return True
        if va.is_string() and vb.is_string():
            return True
        return False

class ArithOperator:
    op: callable
    check: CheckNumber
    meta: str

    def __init__(self, op: callable, check: CheckNumber, meta: str):
        self.op = op
        self.meta = meta
        self.check = check

    def solve(self, L: LuaState, a: int, b: Optional[int] = None) -> Value | bool:
        va = L._get_rk(a)
        mt = va.get_metatable()
        if b is None:
            if self.check.check(va) is not None:
                return Value(value=self.op(va.value))
            else:
                if mt:
                    meta_func = mt.get(Value(self.meta))
                    if meta_func and meta_func.is_function():
                        return L._luacall(meta_func.value, va)
        else:
            vb = L._get_rk(b)
            if self.check.checks(va, vb):
                return Value(value=self.op(va.value, vb.value))
            else:
                if mt is None:
                    mt = vb.get_metatable()
                if mt:
                    meta_func = mt.get(Value(self.meta))
                    if meta_func and meta_func.is_function():
                        return L._luacall(meta_func.value, va, vb)
        return False

    def arith(self, L: LuaState, idx: int, a: int, b: Optional[int] = None):
        res = self.solve(L, a, b)
        if res:
            L.stack[idx] = res

    def compare(self, L: LuaState, a: int, b: int) -> bool:
        res = self.solve(L, a, b)
        if type(res) is Value and res.is_boolean():
            return res.value
        return False


ARITH = {
    "ADD": ArithOperator(lambda a, b: a + b , CheckNumber, "__add"),
    "SUB": ArithOperator(lambda a, b: a - b , CheckNumber, "__sub"),
    "MUL": ArithOperator(lambda a, b: a * b , CheckNumber, "__mul"),
    "DIV": ArithOperator(lambda a, b: a / b , CheckNumber, "__div"),
    "MOD": ArithOperator(lambda a, b: a % b , CheckNumber, "__mod"),
    "POW": ArithOperator(lambda a, b: a ** b, CheckNumber, "__pow"),
    "UNM": ArithOperator(lambda a: -a       , CheckNumber, "__unm"),
    "BNOT": ArithOperator(lambda a: ~a      , CheckNumber, "__bnot"),

    "EQ": ArithOperator(lambda a, b: a == b , CompareCheck, "__eq"),
    "LT": ArithOperator(lambda a, b: a < b  , CompareCheck, "__lt"),
    "LE": ArithOperator(lambda a, b: a <= b , CompareCheck, "__le"),
}


def lua_print(state: LuaState) -> int:
    n = state.get_top()
    outputs = []
    for i in range(n):
        outputs.append(str(state.stack[i]))
    print(', '.join(outputs))
    return 0

def lua_getmetatable(state: LuaState) -> int:
    idx = state.get_top() - 1
    state.stack[0] = state.getmetatable(idx)
    return 1

def lua_setmetatable(state: LuaState) -> int:
    idx = state.get_top() - 2
    state.setmetatable(idx)
    return 0

def lua_next(state: LuaState) -> int:
    result = state.next(0)
    if result is not None:
        state.pushvalue(result[0])
        state.pushvalue(result[1])
        return 2
    else:
        return 0

def lua_pairs(state: LuaState) -> int:
    table = state.stack[0]
    if not table.is_table():
        raise TypeError("pairs expects a table")
    state.pushpyfunction(lua_next)
    state.pushvalue(table)
    state.pushnil()
    return 3

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
        closure = state.call_info[-1]
        if b < len(closure.upvalues):
            state.stack[a] = closure.upvalues[b]
        else:
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
        name = state.func.consts[bx].value
        state.set_global(name, state.stack[a])

    @staticmethod
    def SETUPVAL(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        closure = state.call_info[-1]
        if b < len(closure.upvalues):
            closure.upvalues[b] = state.stack[a]

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
        vb = state.stack[b]
        key = LuaVM.get_rk(state, c)
        result = state.gettable(b, key)
        state.stack[a + 1] = vb
        state.stack[a] = result if result is not None else Value()

    @staticmethod
    def ADD(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        ARITH["ADD"].arith(state, a, b, c)

    @staticmethod
    def SUB(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        ARITH["SUB"].arith(state, a, b, c)

    @staticmethod
    def MUL(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        ARITH["MUL"].arith(state, a, b, c)

    @staticmethod
    def DIV(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        ARITH["DIV"].arith(state, a, b, c)

    @staticmethod
    def MOD(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        ARITH["MOD"].arith(state, a, b, c)

    @staticmethod
    def POW(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        ARITH["POW"].arith(state, a, b, c)

    @staticmethod
    def UNM(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        ARITH["UNM"].arith(state, a, b)

    @staticmethod
    def NOT(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        vb = state.stack[b]
        state.stack[a] = Value(not vb.get_boolean())

    @staticmethod
    def LEN(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        state.stack[a] = Value(state.len(b))

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
        if (ARITH['EQ'].compare(state, b, c)) != (a != 0):
            state.jump(1)

    @staticmethod
    def LT(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        if (ARITH['LT'].compare(state, b, c)) != (a != 0):
            state.jump(1)

    @staticmethod
    def LE(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        if (ARITH['LE'].compare(state, b, c)) != (a != 0):
            state.jump(1)

    @staticmethod
    def TEST(inst: Instruction, state: LuaState):
        a, _, c = inst.abc()
        va = state.stack[a]
        if va.get_boolean() != (c != 0):
            state.jump(1)

    @staticmethod
    def TESTSET(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        vb = state.stack[b]
        if vb.get_boolean() == (c != 0):
            state.stack[a] = vb
        else:
            state.jump(1)

    @staticmethod
    def CALL(inst: Instruction, state: LuaState):
        a, b, c = inst.abc()
        # a: 函数在栈中的位置
        # b: 参数个数 + 1 (0表示从a+1到栈顶都是参数)
        # c: 返回值个数 + 1 (0表示保留所有返回值)
        nargs = b - 1 if b > 0 else len(state.stack) - a - 1
        state.call(a, nargs, c - 1)

    @staticmethod
    def TAILCALL(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        # a: 函数在栈中的位置
        # b: 参数个数 + 1 (0表示从a+1到栈顶都是参数)
        # c: 返回值个数（尾调用中总是0）

        func_value = state.stack[a]
        if not func_value.is_function():
            raise TypeError("TAILCALL requires a function")
        
        nargs = b - 1 if b > 0 else len(state.stack) - a - 1
        if type(func_value.value) is LClosure:
            current_closure = state.call_info[-1]

            new_closure = func_value.value
            new_closure.stack = [Value()] * new_closure.func.maxstacksize
            new_closure.pc = 0
            new_closure.varargs = []

            for i in range(nargs):
                value = state.stack[a + 1 + i]
                if i < new_closure.func.numparams:
                    new_closure.stack[i] = value
                else:
                    new_closure.varargs.append(value)

            new_closure.nrets = current_closure.nrets
            new_closure.ret_idx = current_closure.ret_idx

            state.call_info[-1] = new_closure
            state.func = new_closure.func
            state.stack = new_closure.stack
        else:
            state.pycall(func_value.value, a, nargs, -1)

    @staticmethod
    def RETURN(inst: Instruction, state: LuaState):
        a, b, _ = inst.abc()
        state.poscall(a, b - 1)

    @staticmethod
    def FORLOOP(inst: Instruction, state: LuaState):
        a, sbx = inst.asbx()
        step = state.stack[a + 2]
        idx = state.stack[a]
        limit = state.stack[a + 1]

        step.conv_str_to_number()
        idx.conv_str_to_number()
        limit.conv_str_to_number()

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

        init.conv_str_to_number()
        step.conv_str_to_number()

        if init.is_number() and step.is_number():
            state.stack[a] = Value(value=init.value - step.value)
            state.jump(sbx)
        else:
            raise TypeError("FORPREP operands must be numbers")

    @staticmethod
    def TFORLOOP(inst: Instruction, state: LuaState):
        a, _, c = inst.abc()
        func_idx = a + 3
        for i in range(3):
            state.stack[func_idx + i] = state.stack[a + i]
        state.call(func_idx, 2, c)
        next_inst = state.fetch()
        _, sbx = next_inst.asbx()
        if not state.stack[func_idx].is_nil():
            state.stack[func_idx - 1] = state.stack[func_idx]
            state.jump(sbx)

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
        proto = state.func.protos[bx]
        state.stack[a] = Value(value=LClosure(proto))
        closure = state.stack[a].value
        for i in range(proto.nups):
            upval_inst = state.fetch()
            _, upval_b, _ = upval_inst.abc()
            if upval_inst.op_name() == "GETUPVAL":
                closure.upvalues[i] = state.call_info[-1].upvalues[upval_b]
            elif upval_inst.op_name() == "MOVE":
                closure.upvalues[i] = state.stack[upval_b]
            else:
                raise ValueError("Invalid upvalue instruction")

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

    # Global
    mt: Table

    def __init__(self, main: Proto):
        self.call_info = [LClosure(main)]
        self.registry = Table()
        self.registry.set(Value(LUA_GLOBALS_INDEX), Value(value=Table()))
        self.globals = self.registry.get(Value(LUA_GLOBALS_INDEX)).value
        self.mt = Table()

        self.func = self.call_info[-1].func
        self.stack = self.call_info[-1].stack

        self.register("print", lua_print)
        self.register("getmetatable", lua_getmetatable)
        self.register("setmetatable", lua_setmetatable)
        self.register("next", lua_next)
        self.register("pairs", lua_pairs)

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

    def getmetatable(self, idx: int):
        obj = self.stack[idx]
        mt = obj.get_metatable()
        return mt if mt is not None else self.mt.get(Value(obj.type_name()))

    def setmetatable(self, idx: int):
        obj = self.stack[idx]
        mt = self.stack[-1]
        assert mt.is_table(), "Metatable must be a table"
        if obj.is_table():
            obj.value.setmetatable(mt.value)
        else:
            self.mt.set(Value(obj.type_name()), mt)

    def gettable(self, idx: int, key: Value) -> Value:
        t = self.stack[idx]
        return t.gettable(key, self._luacall)

    def len(self, idx: int) -> int:
        t = self.stack[idx]
        return t.len(self._luacall)

    def call(self, idx: int, nargs: int, nrets: int):
        func_value = self.stack[idx]
        if func_value.is_function():
            if type(func_value.value) is LClosure:
                self.precall(func_value.value, idx, nargs, nrets)
                while self.excute(): pass
            else:
                self.pycall(func_value.value, idx, nargs, nrets)
        elif func_value.is_table():
            mt = func_value.get_metatable()
            func_value = mt.get(Value("__call")) if mt else None
            if func_value and func_value.is_function():
                self.stack[idx] = self._luacall(func_value.value, *self.stack[idx: idx + nargs + 1])
        else:
            raise TypeError("CALL error")

    def excute(self) -> bool:
        inst = self.fetch()
        if inst is None:
            return False
        op_name = inst.op_name()
        method = getattr(Operator, op_name, None)
        if method:
            print(f"-{len(state.call_info)}- " +  str(inst).ljust(40))
            method(inst, self)
            print(f"-{len(state.call_info)}- " +  ''.join(f"[{v}]" for v in state.stack))
        if op_name == "RETURN":
            return False
        return True

    def precall(self, closure: LClosure, func_idx: int = 0, nargs: int = 0, nrets: int = 0):
        closure.stack = [Value()] * closure.func.maxstacksize
        closure.pc = 0
        closure.varargs = []
        for i in range(nargs):
            value = self.stack[func_idx + 1 + i]
            if i < closure.func.numparams:
                closure.stack[i] = value
            else:
                closure.varargs.append(value)

        closure.nrets = nrets
        closure.ret_idx = func_idx
        self.push_closure(closure)

    def pycall(self, closure: PClosure, func_idx: int = 0, args_count: int = 0, nrets: int = 0):
        closure.stack = []
        for i in range(args_count):
            value = self.stack[func_idx + 1 + i]
            closure.stack.append(value)

        self.push_closure(closure)
        ret_count = closure.func(self)
        self.pop_closure()

        ret_start = len(closure.stack) - ret_count

        for i in range(nrets):
            ret_value = closure.stack[ret_start + i] if i < ret_count else Value()
            self.stack[func_idx + i] = ret_value

    def poscall(self, ret_start, ret_count: int = 0):
        closure = self.pop_closure()

        # Handle return values
        if ret_count == -1:
            ret_count = len(closure.stack) - ret_start

        if closure.nrets == -1:
            closure.nrets = ret_count

        for i in range(closure.nrets):
            ret_value = closure.stack[ret_start + i] if i < ret_count else Value()
            self.stack[closure.ret_idx + i] = ret_value

    def next(self, idx: int) -> Optional[tuple[Value, Value]]:
        table = self.stack[idx]
        key = self.stack[-1]
        if not table.is_table():
            raise TypeError("next expects a table")
        return table.value.next(key)

    def pushpyfunction(self, func: callable):
        self.stack.append(Value(value=PClosure(func)))

    def pushvalue(self, val: Value):
        self.stack.append(val)

    def pushnil(self):
        self.stack.append(Value())

    def _luacall(self, func, *args) -> Value:
        nargs = len(args)
        func_idx = len(self.stack)
        self.stack.append(Value(value=func))
        self.stack.extend(args)
        self.call(func_idx, nargs, 1)
        res = self.stack[func_idx]
        while len(self.stack) > func_idx:
            self.stack.pop()
        return res
    
    def _get_rk(self, rk: int) -> Value:
        """Get RK value: if rk >= 256, it's a constant index; otherwise it's a register"""
        if rk >= 256:
            # It's a constant (k)
            return self.func.consts[rk - 256]
        else:
            # It's a register (r)
            return self.stack[rk]

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
            print(f"-{len(state.call_info)}- " +  str(inst).ljust(40))
            method(inst, state)
            print(f"-{len(state.call_info)}- " +  ''.join(f"[{v}]" for v in state.stack))
        # else:
        #     raise NotImplementedError(f"Operator {op_name} not implemented")
        return True

    @staticmethod
    def get_rk(state: LuaState, rk: int) -> Value:
        return state._get_rk(rk)


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
