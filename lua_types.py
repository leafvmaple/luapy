from enum import Enum
from typing import Any

from lua_io import Reader

class LUA_TYPE(Enum):
    NIL = 0
    BOOLEAN = 1
    NUMBER = 3
    STRING = 4

class String:
    size: int
    value: str
    
    def __init__(self, file: Reader):
        self.size = file.read_uint64()
        self.value = file.read_bytes(self.size)[:-1].decode('utf-8') if self.size > 0 else ""

    def __str__(self) -> str:
        return self.value

class Value:
    type: LUA_TYPE
    value: Any
    
    def __init__(self, file: Reader):
        self.type = LUA_TYPE(file.read_uint8())
        if self.type == LUA_TYPE.NIL:
            self.value = None
        elif self.type == LUA_TYPE.BOOLEAN:
            self.value = file.read_uint8() != 0
        elif self.type == LUA_TYPE.NUMBER:
            self.value = file.read_double()
        elif self.type == LUA_TYPE.STRING:
            self.value = String(file)
        else:
            raise ValueError(f"Unknown constant type: {self.type}")
        
    def __str__(self) -> str:
        if self.type == LUA_TYPE.NIL:
            return 'nil'
        elif self.type == LUA_TYPE.BOOLEAN:
            return 'true' if self.value else 'false'
        elif self.type == LUA_TYPE.NUMBER:
            return str(self.value)
        elif self.type == LUA_TYPE.STRING:
            return f'"{self.value}"'
        return str(self.value)