import sys
from veltrix.lexer import Lexer
from veltrix.parser import Parser

with open("examples/age_checker.vlx", "r") as f:
    source = f.read()

lexer = Lexer(source, "age_checker.vlx")
tokens = lexer.tokenize()
print(tokens[:10])

parser = Parser(tokens, "age_checker.vlx")
prog = parser.parse()
print(prog)
