"""Lua bytecode loader and VM entry point."""
from __future__ import annotations

from lua_io import Reader
from lua_bin import read_header, read_proto
from lua_function import Proto
from lua_state import LuaState
from lua_operator import Operator


class LuaVM:
    @staticmethod
    def fetch(state: LuaState):
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
        return True

    @staticmethod
    def get_rk(state: LuaState, rk: int):
        return state._get_rk(rk)


class PyLua:
    reader: Reader
    header: Header
    main: Proto

    def __init__(self, file_path: str):
        with open(file_path, 'rb') as f:
            self.reader = Reader(f)
            self.header = read_header(self.reader)
            self.main = read_proto(self.reader)

    def __str__(self) -> str:
        return f"{self.main}"


if __name__ == "__main__":
    pylua_file = PyLua("test.luac")
    print(pylua_file)

    state = LuaState(pylua_file.main)
    while LuaVM.excute(state):
        state.print_stack()
    pass
