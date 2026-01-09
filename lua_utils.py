from lua_types import LUA_TYPE, Value

def to_boolean(value: Value) -> bool:
    if value.is_nil():
        return False
    if value.is_boolean():
        return value.value
    return True