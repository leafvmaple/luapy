from __future__ import annotations

from typing import Optional
from lua_operator import Operator
from lua_instruction import Instruction
from lua_value import Value
from lua_table import Table
from lua_function import LClosure, PClosure, Proto
from lua_builtins import lua_print, lua_getmetatable, lua_setmetatable, lua_next, lua_ipairs, lua_pairs

LUA_GLOBALS_INDEX = -10002


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

        # Register built-in functions
        self.register("print", lua_print)
        self.register("getmetatable", lua_getmetatable)
        self.register("setmetatable", lua_setmetatable)
        self.register("next", lua_next)
        self.register("ipairs", lua_ipairs)
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
        # Delegate to Value's gettable method with callback
        return t.gettable(key, self._luacall)

    def len(self, idx: int) -> int:
        t = self.stack[idx]
        # Delegate to Value's len method with callback
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
            print(f"-{len(self.call_info)}- " +  str(inst).ljust(40))
            method(inst, self)
            print(f"-{len(self.call_info)}- " +  ''.join(f"[{v}]" for v in self.stack))
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
