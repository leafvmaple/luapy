from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from lua_io import Reader
from lua_protocols import LuaCallable
from lua_table import Table
from lua_function import LClosure, PClosure


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
            self.__read(file)

        self.conv_float_to_int()

    def conv_number_to_str(self):
        if self.is_number():
            self.value = str(self.value)

    def conv_str_to_number(self):
        if self.is_string():
            self.value = float(self.value)
            self.conv_float_to_int()

    def conv_float_to_int(self):
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

    def get_boolean(self) -> bool:
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

    def get_string(self) -> str | None:
        if self.is_number():
            return str(self.value)
        if self.is_string():
            return self.value
        return None
    
    def get_metatable(self) -> Table | None:
        if self.is_table():
            return self.value.getmetatable()
        return None
    
    def gettable(self, key: Value, caller: LuaCallable | None = None) -> Value | None:
        value = self.value.gettable(key) if self.is_table() else None
        if value is not None:
            return value
            
        mt = self.get_metatable()
        index = mt.get(Value("__index")) if mt else None
        if index:
            if index.is_function():
                assert caller is not None, "__index metamethod requires a caller"
                return caller(index.value, self, key)
            if index.is_table():
                return index.gettable(key, caller)
        return None
    
    def len(self, caller: LuaCallable | None = None) -> int:
        mt = self.get_metatable()
        length = mt.get(Value("__len")) if mt else None
        if length and length.is_function():
            assert caller is not None, "__len metamethod requires a caller"
            result = caller(length.value, self)
            int_result = result.get_integer()
            return int_result if int_result is not None else 0

        if self.is_table():
            return self.value.len()
        if self.is_string():
            return len(self.value)
        return 0
    
    def __read(self, file: Reader = None):
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

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other: Value) -> bool:
        return self.value == other.value

    def __repr__(self) -> str:
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
