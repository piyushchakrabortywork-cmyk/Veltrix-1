"""
Veltrix Lexer (Tokenizer) — Phase 2
=====================================
Converts raw source code into a stream of tokens.
Tracks line numbers for error reporting.
Supports string interpolation, range operator, and new keywords.
"""

from enum import Enum, auto
from veltrix.errors import VeltrixSyntaxError


# ─── Token Types ──────────────────────────────────────────────────────────────

class TokenType(Enum):
    # Literals
    NUMBER      = auto()
    STRING      = auto()
    BOOLEAN     = auto()
    INTERP_STRING = auto()  # String with {expr} interpolation parts
    COLOR_HEX   = auto()    # E.g., #111111

    # Styling Engine
    STYLE_KEYWORD = auto()
    STYLE       = auto()

    # Identifiers
    IDENTIFIER  = auto()

    # Keywords
    LET         = auto()
    CONSTANT    = auto()
    WRITE       = auto()
    ASK         = auto()
    IF          = auto()
    ELSE        = auto()
    END         = auto()
    FOR         = auto()
    FROM        = auto()
    TO          = auto()
    STEP        = auto()
    IN          = auto()
    WHILE       = auto()
    FUNCTION    = auto()
    RETURN      = auto()
    ADD         = auto()
    REMOVE      = auto()
    MATCH       = auto()
    OTHERWISE   = auto()
    TRY         = auto()
    CATCH       = auto()
    IMPORT      = auto()
    CLASS       = auto()
    SELF        = auto()
    NULL        = auto()
    IS          = auto()

    # GUI
    WINDOW      = auto()
    SHOW        = auto()
    RECTANGLE   = auto()
    CIRCLE      = auto()
    LINE        = auto()

    # Layouts & Components
    VSTACK      = auto()
    HSTACK      = auto()
    GRID        = auto()
    BUTTON      = auto()
    INPUT       = auto()
    CHECKBOX    = auto()
    DROPDOWN    = auto()

    # Events
    ON_CLICK    = auto()
    ON_HOVER    = auto()
    ON_CHANGE   = auto()
    ON_KEYPRESS = auto()

    # Logic
    AND         = auto()
    OR          = auto()
    NOT         = auto()

    # Operators
    PLUS        = auto()
    MINUS       = auto()
    STAR        = auto()
    SLASH       = auto()
    MODULO      = auto()
    ASSIGN      = auto()
    EQ          = auto()
    NEQ         = auto()
    GT          = auto()
    LT          = auto()
    GTE         = auto()
    LTE         = auto()
    ARROW       = auto()   # =>
    RIGHT_ARROW = auto()   # ->
    DOT         = auto()
    DOTDOT      = auto()   # ..

    # Delimiters
    LPAREN      = auto()
    RPAREN      = auto()
    LBRACKET    = auto()
    RBRACKET    = auto()
    LBRACE      = auto()
    RBRACE      = auto()
    COMMA       = auto()
    COLON       = auto()
    SEMICOLON   = auto()

    # Structure
    NEWLINE     = auto()
    EOF         = auto()


# ─── Keywords ─────────────────────────────────────────────────────────────────

KEYWORDS = {
    "Let":       TokenType.LET,
    "Constant":  TokenType.CONSTANT,
    "Write":     TokenType.WRITE,
    "Ask":       TokenType.ASK,
    "If":        TokenType.IF,
    "Else":      TokenType.ELSE,
    "End":       TokenType.END,
    "For":       TokenType.FOR,
    "from":      TokenType.FROM,
    "to":        TokenType.TO,
    "step":      TokenType.STEP,
    "in":        TokenType.IN,
    "While":     TokenType.WHILE,
    "Function":  TokenType.FUNCTION,
    "Return":    TokenType.RETURN,
    "Add":       TokenType.ADD,
    "Remove":    TokenType.REMOVE,
    "Match":     TokenType.MATCH,
    "Otherwise": TokenType.OTHERWISE,
    "Try":       TokenType.TRY,
    "Catch":     TokenType.CATCH,
    "Import":    TokenType.IMPORT,
    "Class":     TokenType.CLASS,
    "Self":      TokenType.SELF,
    "Null":      TokenType.NULL,
    "is":        TokenType.IS,
    "And":       TokenType.AND,
    "Or":        TokenType.OR,
    "Not":       TokenType.NOT,
    "True":      TokenType.BOOLEAN,
    "False":     TokenType.BOOLEAN,
    "not":       TokenType.NOT,
    "if":        TokenType.IF,
    "else":      TokenType.ELSE,
    "style":     TokenType.STYLE,
    "bold":      TokenType.STYLE_KEYWORD,
    "italic":    TokenType.STYLE_KEYWORD,
    "underline": TokenType.STYLE_KEYWORD,
    "strike":    TokenType.STYLE_KEYWORD,
    "color":     TokenType.STYLE_KEYWORD,
    "bg":        TokenType.STYLE_KEYWORD,
    "opacity":   TokenType.STYLE_KEYWORD,
    "gradient":  TokenType.STYLE_KEYWORD,
    "window":    TokenType.WINDOW,
    "show":      TokenType.SHOW,
    "rectangle": TokenType.RECTANGLE,
    "circle":    TokenType.CIRCLE,
    "line":      TokenType.LINE,
    "vstack":    TokenType.VSTACK,
    "hstack":    TokenType.HSTACK,
    "grid":      TokenType.GRID,
    "button":    TokenType.BUTTON,
    "input":     TokenType.INPUT,
    "checkbox":  TokenType.CHECKBOX,
    "dropdown":  TokenType.DROPDOWN,
    "onClick":   TokenType.ON_CLICK,
    "onHover":   TokenType.ON_HOVER,
    "onChange":  TokenType.ON_CHANGE,
    "onKeyPress":TokenType.ON_KEYPRESS,
}


# ─── Token ────────────────────────────────────────────────────────────────────

class Token:
    __slots__ = ("type", "value", "line")

    def __init__(self, type: TokenType, value, line: int):
        self.type = type
        self.value = value
        self.line = line

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, line={self.line})"


# ─── Lexer ────────────────────────────────────────────────────────────────────

class Lexer:
    """Tokenizes Veltrix source code into a list of Tokens."""

    def __init__(self, source: str, filename: str = "<stdin>"):
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.tokens: list[Token] = []

    def error(self, message):
        raise VeltrixSyntaxError(message, self.filename, self.line)

    def peek(self) -> str:
        if self.pos < len(self.source):
            return self.source[self.pos]
        return "\0"

    def peek_ahead(self, offset=1) -> str:
        pos = self.pos + offset
        if pos < len(self.source):
            return self.source[pos]
        return "\0"

    def advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        return ch

    def match(self, expected: str) -> bool:
        if self.pos < len(self.source) and self.source[self.pos] == expected:
            self.pos += 1
            return True
        return False

    def skip_whitespace(self):
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch in (" ", "\t", "\r"):
                self.pos += 1
            else:
                break

    def read_string(self, quote: str) -> Token:
        """Read a string literal, detecting interpolation {expr} parts."""
        start_line = self.line
        result = ""
        has_interpolation = False
        interp_parts = []  # list of (is_expr: bool, content: str)
        current_text = ""

        while self.pos < len(self.source) and self.source[self.pos] != quote:
            ch = self.source[self.pos]
            if ch == "\n":
                self.line += 1
                result += ch
                current_text += ch
                self.pos += 1
            elif ch == "\\" and self.pos + 1 < len(self.source):
                self.pos += 1
                esc = self.source[self.pos]
                if esc == "n":
                    result += "\n"; current_text += "\n"
                elif esc == "t":
                    result += "\t"; current_text += "\t"
                elif esc == "\\":
                    result += "\\"; current_text += "\\"
                elif esc == quote:
                    result += quote; current_text += quote
                elif esc == "{":
                    result += "{"; current_text += "{"
                elif esc == "}":
                    result += "}"; current_text += "}"
                else:
                    result += "\\" + esc
                    current_text += "\\" + esc
                self.pos += 1
            elif ch == "{":
                # Start of interpolation
                has_interpolation = True
                if current_text:
                    interp_parts.append((False, current_text))
                    current_text = ""
                # Read expression until matching }
                self.pos += 1  # skip {
                expr_text = ""
                brace_depth = 1
                while self.pos < len(self.source) and brace_depth > 0:
                    c = self.source[self.pos]
                    if c == "{":
                        brace_depth += 1
                    elif c == "}":
                        brace_depth -= 1
                        if brace_depth == 0:
                            self.pos += 1
                            break
                    elif c == "\n":
                        self.line += 1
                    expr_text += c
                    self.pos += 1
                else:
                    if brace_depth > 0:
                        self.error("Unterminated string interpolation — missing '}'.")
                interp_parts.append((True, expr_text.strip()))
                result += "{" + expr_text + "}"
            else:
                result += ch
                current_text += ch
                self.pos += 1

        if self.pos >= len(self.source):
            self.error("Unterminated string — missing closing quote.")
        self.pos += 1  # skip closing quote

        if has_interpolation:
            if current_text:
                interp_parts.append((False, current_text))
            return Token(TokenType.INTERP_STRING, interp_parts, start_line)
        return Token(TokenType.STRING, result, start_line)

    def read_number(self) -> Token:
        start = self.pos
        while self.pos < len(self.source) and (self.source[self.pos].isdigit() or self.source[self.pos] == "."):
            # Check for .. (range operator) — don't consume second dot
            if self.source[self.pos] == ".":
                if self.pos + 1 < len(self.source) and self.source[self.pos + 1] == ".":
                    break  # stop before ..
                # Check if it's a decimal point
                if self.pos + 1 < len(self.source) and self.source[self.pos + 1].isdigit():
                    self.pos += 1
                else:
                    break
            else:
                self.pos += 1
        text = self.source[start:self.pos]
        value = float(text) if "." in text else int(text)
        return Token(TokenType.NUMBER, value, self.line)

    def read_identifier(self) -> Token:
        start = self.pos
        while self.pos < len(self.source) and (
            self.source[self.pos].isalnum() or self.source[self.pos] == "_"
        ):
            self.pos += 1
        text = self.source[start:self.pos]

        # Check for keywords
        if text in KEYWORDS:
            token_type = KEYWORDS[text]
            value = text
            if token_type == TokenType.BOOLEAN:
                value = (text == "True")
            return Token(token_type, value, self.line)

        # Allow styling keywords to also be identified dynamically if missed
        # Since they are in KEYWORDS, they will be caught above.

        return Token(TokenType.IDENTIFIER, text, self.line)

    def tokenize(self) -> list[Token]:
        """Convert source code into a list of tokens."""
        while self.pos < len(self.source):
            self.skip_whitespace()

            if self.pos >= len(self.source):
                break

            ch = self.source[self.pos]

            # Newline
            if ch == "\n":
                self.tokens.append(Token(TokenType.NEWLINE, "\\n", self.line))
                self.line += 1
                self.pos += 1
                continue

            # Strings
            if ch in ('"', "'"):
                self.pos += 1
                self.tokens.append(self.read_string(ch))
                continue

            # Numbers
            if ch.isdigit():
                self.tokens.append(self.read_number())
                continue

            # Identifiers and keywords
            if ch.isalpha() or ch == "_":
                self.tokens.append(self.read_identifier())
                continue

            # Two-character operators
            if ch == "=" and self.peek_ahead() == ">":
                self.tokens.append(Token(TokenType.ARROW, "=>", self.line))
                self.pos += 2
                continue
            if ch == "=" and self.peek_ahead() == "=":
                self.tokens.append(Token(TokenType.EQ, "==", self.line))
                self.pos += 2
                continue
            if ch == "-" and self.peek_ahead() == ">":
                self.tokens.append(Token(TokenType.RIGHT_ARROW, "->", self.line))
                self.pos += 2
                continue
            if ch == "!" and self.peek_ahead() == "=":
                self.tokens.append(Token(TokenType.NEQ, "!=", self.line))
                self.pos += 2
                continue
            if ch == ">" and self.peek_ahead() == "=":
                self.tokens.append(Token(TokenType.GTE, ">=", self.line))
                self.pos += 2
                continue
            if ch == "<" and self.peek_ahead() == "=":
                self.tokens.append(Token(TokenType.LTE, "<=", self.line))
                self.pos += 2
                continue
            if ch == "." and self.peek_ahead() == ".":
                self.tokens.append(Token(TokenType.DOTDOT, "..", self.line))
                self.pos += 2
                continue

            # Comments & Color Hex
            if ch == "#":
                # Check if it's a color hex: a '#' followed by at least one hex digit
                is_hex = False
                if self.pos + 1 < len(self.source):
                    next_c = self.source[self.pos + 1]
                    if next_c.isdigit() or next_c.lower() in "abcdef":
                        is_hex = True
                        
                if is_hex:
                    self.pos += 1
                    start = self.pos
                    while self.pos < len(self.source) and (self.source[self.pos].isdigit() or self.source[self.pos].lower() in 'abcdef'):
                        self.pos += 1
                    hex_val = self.source[start:self.pos]
                    self.tokens.append(Token(TokenType.COLOR_HEX, f"#{hex_val}", self.line))
                else:
                    # It's a comment, skip until newline
                    while self.pos < len(self.source) and self.source[self.pos] != "\n":
                        self.pos += 1
                continue

            # Single-character operators
            single_ops = {
                "+": TokenType.PLUS,
                "-": TokenType.MINUS,
                "*": TokenType.STAR,
                "/": TokenType.SLASH,
                "%": TokenType.MODULO,
                "=": TokenType.ASSIGN,
                ">": TokenType.GT,
                "<": TokenType.LT,
                ".": TokenType.DOT,
                "(": TokenType.LPAREN,
                ")": TokenType.RPAREN,
                "[": TokenType.LBRACKET,
                "]": TokenType.RBRACKET,
                "{": TokenType.LBRACE,
                "}": TokenType.RBRACE,
                ",": TokenType.COMMA,
                ":": TokenType.COLON,
                ";": TokenType.SEMICOLON,
            }

            if ch in single_ops:
                self.tokens.append(Token(single_ops[ch], ch, self.line))
                self.pos += 1
                continue

            self.error(f"Unexpected character: '{ch}'")

        self.tokens.append(Token(TokenType.EOF, None, self.line))
        return self.tokens
