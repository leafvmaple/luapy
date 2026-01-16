from __future__ import annotations

TOKEN_TYPE = {
    '+': "PLUS",
    '-': "MINUS",
    '*': "MULTIPLY",
    '/': "DIVIDE",
    '=': "EQUALS",
    ';': "SEMICOLON",
    '(': "LPAREN",
    ')': "RPAREN",
    ',': "COMMA",
    '{': "LBRACE",
    '}': "RBRACE",
    '[': "LBRACKET",
    ']': "RBRACKET"
}

class Token:
    type: str
    value: str | None
    line: int

    def __init__(self, type: str, value: str | None, line: int):
        self.type = type
        self.value = value
        self.line = line

    def is_block_end(self) -> bool:
        return self.type in ("EOF", "END", "ELSE", "ELSEIF", "EOF")
    
    def is_return(self) -> bool:
        return self.type == "RETURN"

class Lexer:
    chunk: str
    chunk_name: str
    line: int
    pos: int
    token: Token | None = None

    def __init__(self, chunk: str, chunk_name: str = ""):
        self.chunk = chunk
        self.chunk_name = chunk_name
        self.line = 1
        self.pos = 0

    @classmethod
    def from_file(cls, filepath: str):
        with open(filepath, 'r') as f:
            chunk = f.read()
        return cls(chunk, filepath)

    def _get_next_token(self) -> Token:
        self.skip_whitespace()
        if self.is_eof():
            return Token("EOF", None, self.line)
        char = self.peek_char()
        if char.isalpha() or char == '_':
            return self.read_identifier()
        elif char.isdigit():
            return self.read_number()
        elif char == '"':
            return self.read_string()
        elif char == '-':
            self.advance_char()
            if not self.is_eof() and self.peek_char() == '-':
                self.advance_char()
                return self.read_comment()
            else:
                return Token("MINUS", '-', self.line)
        elif char in '+*/=;(),{}[]':
            token_type = TOKEN_TYPE.get(char, "UNKNOWN")
            self.advance_char()
            return Token(token_type, char, self.line)
        # Add more token types as needed
        self.advance_char()
        return Token("UNKNOWN", char, self.line)
    
    def next_token(self) -> Token:
        self.token = self._get_next_token()
        return self.token
    
    def peek_token(self) -> Token:
        return self.token
    
    def read_identifier(self) -> Token:
        start_pos = self.pos
        while not self.is_eof() and ((char := self.peek_char()) and char.isalnum() or char == '_'):
            self.advance_char()
        value = self.chunk[start_pos: self.pos]
        return Token("IDENTIFIER", value, self.line)
    
    def read_number(self) -> Token:
        start_pos = self.pos
        while not self.is_eof() and self.peek_char().isdigit():
            self.advance_char()
        value = self.chunk[start_pos: self.pos]
        return Token("NUMBER", value, self.line)
    
    def read_string(self) -> Token:
        self.advance_char()  # skip opening quote
        start_pos = self.pos
        while not self.is_eof() and self.peek_char() != '"':
            self.advance_char()
        value = self.chunk[start_pos: self.pos]
        self.advance_char()  # skip closing quote
        return Token("STRING", value, self.line)
    
    def read_comment(self) -> Token:
        start_pos = self.pos
        while not self.is_eof() and self.peek_char() != '\n':
            self.advance_char()
        value = self.chunk[start_pos: self.pos]
        return Token("COMMENT", value, self.line)

    def skip_whitespace(self):
        while not self.is_eof() and (char := self.peek_char()).isspace():
            if char == '\n':
                self.line += 1
            self.advance_char()

    def is_eof(self) -> bool:
        return self.pos >= len(self.chunk)
    
    def peek_char(self) -> str:
        return self.chunk[self.pos]
    
    def advance_char(self):
        self.pos += 1

    def test(self):
        while not self.is_eof():
            token = self.next_token()
            print(f"{token.line}: {token.type} -> {token.value}")