from lua_types import LUA_TYPE, Value

def toboolean(value: Value) -> bool:
    if value.type == LUA_TYPE.NIL:
        return False
    if value.type == LUA_TYPE.BOOLEAN:
        return value.value
    return True