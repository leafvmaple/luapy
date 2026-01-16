from __future__ import annotations

from lua_lexer import Lexer

class Stat:
    @staticmethod
    def parses(lexer: Lexer) -> list[Stat]:
        stats: list[Stat] = []
        while not lexer.next_token().is_block_end():
            # Here should be the implementation of parsing different kinds of statements
            # For simplicity, we will just break to avoid an infinite loop
            break
        return stats
    
    @staticmethod
    def parse(lexer: Lexer) -> Stat:
        token = lexer.next_token()
        if token.type == "BREAK":
            return BreakStat()
        elif token.type == "LABEL":
            name = lexer.next_token().value  # assuming next token is the label name
            return LabelStat(name)
        elif token.type == "GOTO":
            name = lexer.next_token().value  # assuming next token is the label name
            return GotoStat(name)
        elif token.type == "DO":
            block = Block.parse(lexer)
            return DoStat(block)
        elif token.type == "WHILE":
            exp = Exp()  # placeholder for expression parsing
            block = Block.parse(lexer)
            return WhileStat(exp, block)
        elif token.type == "REPEAT":
            block = Block.parse(lexer)
            exp = Exp()  # placeholder for expression parsing
            return RepeatStat(block, exp)
        elif token.type == "IF":
            exps = []  # placeholder for expression list parsing
            blocks = []  # placeholder for block list parsing
            return IfStat(exps, blocks)
        elif token.type == "FOR":
            varname = lexer.next_token().value  # assuming next token is the variable name
            initexp = Exp()  # placeholder for initial expression parsing
            limitexp = Exp()  # placeholder for limit expression parsing
            stepexp = None  # placeholder for step expression parsing
            block = Block.parse(lexer)
            return ForNumStat(varname, initexp, limitexp, stepexp, block)
        elif token.type == "FORIN":
            varnames = []  # placeholder for variable names parsing
            exps = []  # placeholder for expressions parsing
            block = Block.parse(lexer)
            return ForInStat(varnames, exps, block)
        elif token.type == "LOCAL":
            varnames = []  # placeholder for variable names parsing
            exps = []  # placeholder for expressions parsing
            return LocalVarDeclStat(varnames, exps)
        elif token.type == "ASSIGN":
            varlist = []  # placeholder for variable list parsing
            explist = []  # placeholder for expression list parsing
            return AssignStat(varlist, explist)
        elif token.type == "LOCALFUNC":
            name = lexer.next_token().value  # assuming next token is the function name
            funcbody = Exp()  # placeholder for function body parsing
            return LocalFuncDefStat(name, funcbody)
        else:
            exp = Exp.parse(lexer)
            return ExprStat(exp)

class EmptyStat(Stat):
    def __init__(self):
        pass

class ExprStat(Stat):
    exp: Exp

    def __init__(self, exp: Exp):
        self.exp = exp

class BreakStat(Stat):
    def __init__(self):
        pass

class LabelStat(Stat):
    name: str

    def __init__(self, name: str):
        self.name = name

class GotoStat(Stat):
    name: str

    def __init__(self, name: str):
        self.name = name

class DoStat(Stat):
    block: Block

    def __init__(self, block: Block):
        self.block = block

class WhileStat(Stat):
    exp: Exp
    block: Block

    def __init__(self, exp: Exp, block: Block):
        self.exp = exp
        self.block = block

class RepeatStat(Stat):
    block: Block
    exp: Exp

    def __init__(self, block: Block, exp: Exp):
        self.block = block
        self.exp = exp

class IfStat(Stat):
    exps: list[Exp]
    blocks: list[Block]

    def __init__(self, exps: list[Exp], blocks: list[Block]):
        self.exps = exps
        self.blocks = blocks

class ForNumStat(Stat):
    varname: str
    initexp: Exp
    limitexp: Exp
    stepexp: Exp | None
    block: Block

    def __init__(self, varname: str, initexp: Exp, limitexp: Exp, stepexp: Exp | None, block: Block):
        self.varname = varname
        self.initexp = initexp
        self.limitexp = limitexp
        self.stepexp = stepexp
        self.block = block

class ForInStat(Stat):
    varnames: list[str]
    exps: list[Exp]
    block: Block

    def __init__(self, varnames: list[str], exps: list[Exp], block: Block):
        self.varnames = varnames
        self.exps = exps
        self.block = block

class LocalVarDeclStat(Stat):
    varnames: list[str]
    exps: list[Exp]

    def __init__(self, varnames: list[str], exps: list[Exp]):
        self.varnames = varnames
        self.exps = exps

class AssignStat(Stat):
    explist: list[Exp]
    varlist: list[Exp]

    @classmethod
    def parse(cls, lexer: Lexer) -> AssignStat:
        varlist = []  # placeholder for variable list parsing
        explist = []  # placeholder for expression list parsing
        return cls(varlist, explist)

class LocalFuncDefStat(Stat):
    name: str
    funcbody: Exp

    def __init__(self, name: str, funcbody: Exp):
        self.name = name
        self.funcbody = funcbody

class Exp:
    @staticmethod
    def parse(lexer: Lexer) -> Exp:
        token = lexer.peek_token()
        lexer.next_token()  # consume the token
        if token.type == "NIL":
            return NilExp()
        elif token.type == "TRUE":
            return TrueExp()
        elif token.type == "FALSE":
            return FalseExp()
        elif token.type == "VARARG":
            return VarargExp()
        elif token.type == "NUMBER":
            if '.' in token.value:
                return FloatExp(float(token.value))
            else:
                return IntergerExp(int(token.value))
        elif token.type == "STRING":
            return StringExp(token.value)
        elif token.type == "IDENTIFIER":
            exp = NameExp(token.value)
            if (func_call := FuncCallExp.parse(lexer, exp)) is not None:
                return func_call
            return exp
        else:
            return Exp()

class NilExp(Exp):
    def __init__(self):
        pass

class TrueExp(Exp):
    def __init__(self):
        pass

class FalseExp(Exp):
    def __init__(self):
        pass

class VarargExp(Exp):
    def __init__(self):
        pass

class IntergerExp(Exp):
    value: int

    def __init__(self, value: int):
        self.value = value

class FloatExp(Exp):
    value: float

    def __init__(self, value: float):
        self.value = value

class StringExp(Exp):
    value: str

    def __init__(self, value: str):
        self.value = value

class NameExp(Exp):
    name: str

    def __init__(self, name: str):
        self.name = name

class UnaryOpExp(Exp):
    op: str
    exp: Exp

    def __init__(self, op: str, exp: Exp):
        self.op = op
        self.exp = exp

class BinaryOpExp(Exp):
    op: str
    left: Exp
    right: Exp

    def __init__(self, op: str, left: Exp, right: Exp):
        self.op = op
        self.left = left
        self.right = right

class ConcatExp(Exp):
    exps: list[Exp]

    def __init__(self, exps: list[Exp]):
        self.exps = exps

class TableConstructorExp(Exp):
    fields: list[tuple[Exp | None, Exp]]

    def __init__(self, fields: list[tuple[Exp | None, Exp]]):
        self.fields = fields

class FuncDefExp(Exp):
    param_names: list[str]
    is_vararg: bool
    body: Block

    def __init__(self, param_names: list[str], is_vararg: bool, body: Block):
        self.param_names = param_names
        self.is_vararg = is_vararg
        self.body = body

class ParenExp(Exp):
    exp: Exp

    def __init__(self, exp: Exp):
        self.exp = exp

class TableAccessExp(Exp):
    prefix_exp: Exp
    key_exp: Exp

    def __init__(self, prefix_exp: Exp, key_exp: Exp):
        self.prefix_exp = prefix_exp
        self.key_exp = key_exp

class FuncCallExp(Exp):
    prefix_exp: Exp
    name_exp: StringExp
    args: list[Exp]

    @classmethod
    def parse(cls, lexer: Lexer, prefix: Exp) -> FuncCallExp | None:
        token = lexer.peek_token()
        if token.type != "DOT" and token.type != "LPAREN":
            return None
        exp = cls()
        exp.name_exp = prefix
        exp.args = []
        return exp

class Block:
    last_line: int
    stats: list[Stat]
    ret_exps: list[Exp]

    def __init__(self, last_line: int, stats: list[Stat], ret_exps: list[Exp]):
        self.last_line = last_line
        self.stats = stats
        self.ret_exps = ret_exps

    @classmethod
    def parse(cls, lexer: Lexer) -> Block:
        block = Block(
            stats = Stat.parse(lexer),
            ret_exps=[],
            last_line=0
        )
