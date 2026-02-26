"""
Veltrix Parser — Phase 2
==========================
Recursive-descent parser that converts a token stream into an AST.
Handles all Veltrix language constructs including classes, arrow functions,
typed parameters, null safety, string interpolation, ranges, inline
conditions, and enhanced pattern matching.
"""

from veltrix.lexer import Token, TokenType, Lexer
from veltrix.ast_nodes import (
    ASTNode, Program, NumberLiteral, StringLiteral, BoolLiteral, NullLiteral,
    Identifier, BinaryOp, UnaryOp, LetDeclaration, ConstantDeclaration,
    Assignment, WriteStatement, AskStatement, IfStatement, ForLoop, ForEachLoop,
    WhileLoop, FunctionDef, FunctionCall, ReturnStatement, ListLiteral, MapLiteral,
    ListAccess, MapAccess, AddToList, RemoveFromList, MatchStatement, MatchRange,
    TryCatch, ImportStatement, ListAssignment, MapAssignment,
    ClassDef, SelfAccess, SelfAssignment, MethodCall, ArrowFunction,
    TypedParam, StringInterpolation, RangeExpression, InlineCondition,
    IsNullCheck, IsNotNullCheck, Property, PropertyBlock, ColorLiteral,
    StyleApplication, StyleBlock, StyleProperty, GradientProperty,
    ShowWindowStmt, LayoutBlock, ComponentBlock
)
from veltrix.errors import VeltrixSyntaxError


class Parser:
    """Parses a list of tokens into a Veltrix AST."""

    def __init__(self, tokens: list[Token], filename: str = "<stdin>", legacy_mode: bool = False):
        self.tokens = tokens
        self.filename = filename
        self.pos = 0
        self.legacy_mode = legacy_mode

    # ── Helpers ───────────────────────────────────────────────────────────

    def current(self) -> Token:
        return self.tokens[self.pos]

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def peek_type(self) -> TokenType:
        return self.tokens[self.pos].type

    def peek_ahead_type(self, offset=1) -> TokenType:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx].type
        return TokenType.EOF

    def at_end(self) -> bool:
        return self.tokens[self.pos].type == TokenType.EOF

    def advance(self) -> Token:
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def expect(self, token_type: TokenType, message: str = None) -> Token:
        if self.peek_type() != token_type:
            got = self.current()
            msg = message or f"Expected {token_type.name}, got {got.type.name} ('{got.value}')"
            raise VeltrixSyntaxError(msg, self.filename, got.line)
        return self.advance()

    def match(self, *types: TokenType) -> Token | None:
        if self.peek_type() in types:
            return self.advance()
        return None

    def skip_newlines(self):
        while not self.at_end() and self.peek_type() == TokenType.NEWLINE:
            self.advance()

    def expect_statement_terminator(self):
        """Require a semicolon in strict mode, but fall back to newlines/EOF in legacy mode."""
        if self.at_end():
            return
            
        if self.peek_type() == TokenType.SEMICOLON:
            self.advance()
            return
            
        if self.legacy_mode:
            if self.peek_type() == TokenType.NEWLINE:
                self.advance()
                return
            if self.peek_type() in (TokenType.END, TokenType.ELSE, TokenType.CATCH,
                                    TokenType.OTHERWISE, TokenType.RBRACE):
                return
        
        # If we got here and it's strict mode, we throw an error for missing ;
        # NOTE: sometimes we might be parked on a NEWLINE instead of SEMICOLON.
        # Skip newlines optionally? No, if strict, newlines are just whitespace.
        got = self.current()
        raise VeltrixSyntaxError(
            "Expected ';' after statement",
            self.filename, got.line, hint="Make sure every executable statement ends with ';'"
        )

    def expect_newline_or_eof(self):
        """Used for block headers and legacy statements."""
        if self.at_end():
            return
        if self.peek_type() == TokenType.NEWLINE:
            self.advance()
            return
        # Allow if next token is End, Else, Catch, Otherwise, or start of block
        if self.peek_type() in (TokenType.END, TokenType.ELSE, TokenType.CATCH,
                                TokenType.OTHERWISE, TokenType.RBRACE):
            return
        got = self.current()
        raise VeltrixSyntaxError(
            f"Expected end of line, got '{got.value}'",
            self.filename, got.line
        )

    def expect_property_terminator(self):
        """Require a comma in block properties."""
        if self.peek_type() == TokenType.COMMA:
            self.advance()
            return
        
        # If the next token is RBRACE, trailing comma is optional, so we can return
        if self.peek_type() == TokenType.RBRACE:
            return
            
        got = self.current()
        raise VeltrixSyntaxError(
            "Expected ',' after property",
            self.filename, got.line, hint="Property declarations inside blocks MUST end with ','"
        )

    # ── Main entry ────────────────────────────────────────────────────────

    def parse(self) -> Program:
        """Parse the full token stream into a Program AST."""
        self.skip_newlines()
        statements = []
        while not self.at_end():
            stmt = self.parse_statement()
            if stmt is not None:
                statements.append(stmt)
            self.skip_newlines()
        return Program(statements=statements, line=1)

    # ── Statements ────────────────────────────────────────────────────────

    def parse_statement(self) -> ASTNode:
        """Dispatch to the correct statement parser."""
        tt = self.peek_type()

        if tt == TokenType.LET:
            return self.parse_let()
        if tt == TokenType.CONSTANT:
            return self.parse_constant()
        if tt == TokenType.WRITE:
            return self.parse_write()
        if tt == TokenType.ASK:
            return self.parse_ask()
        if tt == TokenType.IF:
            return self.parse_if()
        if tt == TokenType.FOR:
            return self.parse_for()
        if tt == TokenType.WHILE:
            return self.parse_while()
        if tt == TokenType.FUNCTION:
            return self.parse_function()
        if tt == TokenType.RETURN:
            return self.parse_return()
        if tt == TokenType.ADD:
            return self.parse_add_to_list()
        if tt == TokenType.REMOVE:
            return self.parse_remove_from_list()
        if tt == TokenType.MATCH:
            return self.parse_match()
        if tt == TokenType.TRY:
            return self.parse_try()
        if tt == TokenType.IMPORT:
            return self.parse_import()
        if tt == TokenType.CLASS:
            return self.parse_class()
        if tt == TokenType.SELF:
            return self.parse_self_statement()

        if tt == TokenType.SHOW:
            return self.parse_show()
            
        # Style statements (treated as expressions, but we can allow them as top-level if we expect ;)
        if tt in (TokenType.STYLE, TokenType.STYLE_KEYWORD):
            expr = self.parse_expression()
            self.expect_statement_terminator()
            return expr
            
        if tt in (TokenType.IDENTIFIER, TokenType.WINDOW, TokenType.RECTANGLE, TokenType.CIRCLE, TokenType.LINE,
                  TokenType.VSTACK, TokenType.HSTACK, TokenType.GRID,
                  TokenType.BUTTON, TokenType.INPUT, TokenType.CHECKBOX, TokenType.DROPDOWN):
            return self.parse_identifier_statement()

        got = self.current()
        raise VeltrixSyntaxError(
            f"Unexpected token: '{got.value}'",
            self.filename, got.line
        )

    # ── Let ───────────────────────────────────────────────────────────────

    def parse_show(self) -> ASTNode:
        tok = self.advance()
        self.expect(TokenType.WINDOW, "Expected 'window' after 'show'")
        self.expect_statement_terminator()
        return ShowWindowStmt(line=tok.line)

    def parse_let(self) -> ASTNode:
        """Let name [: Type] = expr"""
        tok = self.advance()  # consume Let
        name_tok = self.expect(TokenType.IDENTIFIER, "Expected variable name after 'Let'")
        name = name_tok.value

        # Optional type annotation
        type_ann = None
        if self.peek_type() == TokenType.COLON:
            self.advance()  # skip :
            type_tok = self.expect(TokenType.IDENTIFIER, "Expected type name after ':'")
            type_ann = type_tok.value

        self.expect(TokenType.ASSIGN, "Expected '=' after variable name")

        # Check for arrow function: Let name = (params) => expr
        value = self.parse_expression()

        # Check for inline condition: value if cond else other
        if self.peek_type() == TokenType.IF and isinstance(self.peek(), Token) and self.peek().value == "if":
            value = self.parse_inline_condition(value)

        self.expect_statement_terminator()
        return LetDeclaration(name=name, value=value, type_annotation=type_ann, line=tok.line)

    # ── Constant ──────────────────────────────────────────────────────────

    def parse_constant(self) -> ASTNode:
        tok = self.advance()
        name_tok = self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.ASSIGN)
        value = self.parse_expression()
        self.expect_statement_terminator()
        return ConstantDeclaration(name=name_tok.value, value=value, line=tok.line)

    # ── Write ─────────────────────────────────────────────────────────────

    def parse_write(self) -> ASTNode:
        tok = self.advance()
        expr = self.parse_expression()
        self.expect_statement_terminator()
        return WriteStatement(expression=expr, line=tok.line)

    # ── Ask ───────────────────────────────────────────────────────────────

    def parse_ask(self) -> ASTNode:
        tok = self.advance()
        prompt = self.parse_expression()
        self.expect(TokenType.IDENTIFIER, "Expected 'Into' after prompt")
        var_tok = self.expect(TokenType.IDENTIFIER, "Expected variable name after 'Into'")
        self.expect_statement_terminator()
        return AskStatement(prompt=prompt, variable=var_tok.value, line=tok.line)

    # ── If ────────────────────────────────────────────────────────────────

    def parse_if(self) -> ASTNode:
        tok = self.advance()  # consume If
        condition = self.parse_expression()
        self.expect_newline_or_eof()

        body = self.parse_block(
            {TokenType.END, TokenType.ELSE}
        )

        else_body = []
        if self.peek_type() == TokenType.ELSE:
            self.advance()
            self.skip_newlines()
            # Check for "Else If" (elif)
            if self.peek_type() == TokenType.IF:
                else_body = [self.parse_if()]
            else:
                self.skip_newlines()
                else_body = self.parse_block({TokenType.END})
                self.expect(TokenType.END)
                self.expect_newline_or_eof()
                return IfStatement(condition=condition, body=body, else_body=else_body, line=tok.line)
        
        if self.peek_type() == TokenType.END:
            self.advance()
            self.expect_newline_or_eof()

        return IfStatement(condition=condition, body=body, else_body=else_body, line=tok.line)

    # ── For ───────────────────────────────────────────────────────────────

    def parse_for(self) -> ASTNode:
        tok = self.advance()  # consume For
        var_tok = self.expect(TokenType.IDENTIFIER, "Expected variable name after 'For'")
        var_name = var_tok.value

        # Check: For i in ... (foreach) vs For i from ... to ... (classic)
        if self.peek_type() == TokenType.IN:
            self.advance()  # consume 'in'
            iterable = self.parse_expression()
            self.expect_newline_or_eof()
            body = self.parse_block({TokenType.END})
            self.expect(TokenType.END)
            self.expect_newline_or_eof()
            return ForEachLoop(variable=var_name, iterable=iterable, body=body, line=tok.line)

        # Classic: For i from start to end [step s]
        self.expect(TokenType.FROM, "Expected 'from' or 'in' after variable in For loop")
        start = self.parse_expression()
        self.expect(TokenType.TO, "Expected 'to' in For loop")
        end = self.parse_expression()

        step = None
        if self.peek_type() == TokenType.STEP:
            self.advance()
            step = self.parse_expression()

        self.expect_newline_or_eof()
        body = self.parse_block({TokenType.END})
        self.expect(TokenType.END)
        self.expect_newline_or_eof()
        return ForLoop(variable=var_name, start=start, end=end, step=step, body=body, line=tok.line)

    # ── While ─────────────────────────────────────────────────────────────

    def parse_while(self) -> ASTNode:
        tok = self.advance()
        condition = self.parse_expression()
        self.expect_newline_or_eof()
        body = self.parse_block({TokenType.END})
        self.expect(TokenType.END)
        self.expect_newline_or_eof()
        return WhileLoop(condition=condition, body=body, line=tok.line)

    # ── Function ──────────────────────────────────────────────────────────

    def parse_function(self) -> ASTNode:
        tok = self.advance()  # consume Function
        name_tok = self.expect(TokenType.IDENTIFIER, "Expected function name")
        self.expect(TokenType.LPAREN)
        params = self.parse_param_list()
        self.expect(TokenType.RPAREN)

        # Optional return type: Function Name(params): ReturnType
        return_type = None
        if self.peek_type() == TokenType.COLON:
            self.advance()
            rt_tok = self.expect(TokenType.IDENTIFIER, "Expected return type after ':'")
            return_type = rt_tok.value

        self.expect_newline_or_eof()
        body = self.parse_block({TokenType.END})
        self.expect(TokenType.END)
        self.expect_newline_or_eof()

        # Normalize params to plain strings for backward compat
        param_names = []
        for p in params:
            if isinstance(p, TypedParam):
                param_names.append(p)
            else:
                param_names.append(p)

        return FunctionDef(name=name_tok.value, params=param_names, body=body,
                           return_type=return_type, line=tok.line)

    def parse_param_list(self) -> list:
        """Parse comma-separated parameter list, supporting optional type annotations."""
        params = []
        if self.peek_type() == TokenType.RPAREN:
            return params

        while True:
            name_tok = self.expect(TokenType.IDENTIFIER, "Expected parameter name")
            if self.peek_type() == TokenType.COLON:
                self.advance()
                type_tok = self.expect(TokenType.IDENTIFIER, "Expected type name")
                params.append(TypedParam(name=name_tok.value, type_annotation=type_tok.value))
            else:
                params.append(name_tok.value)
            if not self.match(TokenType.COMMA):
                break

        return params

    # ── Return ────────────────────────────────────────────────────────────

    def parse_return(self) -> ASTNode:
        tok = self.advance()
        value = None
        if self.peek_type() not in (TokenType.NEWLINE, TokenType.EOF, TokenType.END, TokenType.SEMICOLON):
            value = self.parse_expression()
        self.expect_statement_terminator()
        return ReturnStatement(value=value, line=tok.line)

    # ── Class ─────────────────────────────────────────────────────────────

    def parse_class(self) -> ASTNode:
        """Class ClassName ... End"""
        tok = self.advance()  # consume Class
        name_tok = self.expect(TokenType.IDENTIFIER, "Expected class name")
        self.expect_newline_or_eof()
        self.skip_newlines()

        methods = []
        while self.peek_type() != TokenType.END and not self.at_end():
            self.skip_newlines()
            if self.peek_type() == TokenType.END:
                break
            if self.peek_type() == TokenType.FUNCTION:
                method = self.parse_function()
                methods.append(method)
            else:
                got = self.current()
                raise VeltrixSyntaxError(
                    f"Expected 'Function' or 'End' inside class, got '{got.value}'",
                    self.filename, got.line
                )
            self.skip_newlines()

        self.expect(TokenType.END, "Expected 'End' to close class definition")
        self.expect_newline_or_eof()
        return ClassDef(name=name_tok.value, methods=methods, line=tok.line)

    # ── Self statement ────────────────────────────────────────────────────

    def parse_self_statement(self) -> ASTNode:
        """Self.attr = value"""
        tok = self.advance()  # consume Self
        self.expect(TokenType.DOT, "Expected '.' after 'Self'")
        attr_tok = self.expect(TokenType.IDENTIFIER, "Expected attribute name after 'Self.'")

        if self.peek_type() == TokenType.ASSIGN:
            self.advance()
            value = self.parse_expression()
            self.expect_statement_terminator()
            return SelfAssignment(attribute=attr_tok.value, value=value, line=tok.line)

        # Otherwise it's an expression starting with Self — shouldn't happen as statement
        raise VeltrixSyntaxError(
            "Self.attribute must be followed by '=' in a statement",
            self.filename, tok.line
        )

    # ── Add/Remove ────────────────────────────────────────────────────────

    def parse_add_to_list(self) -> ASTNode:
        tok = self.advance()  # Add
        value = self.parse_expression()
        self.expect(TokenType.TO, "Expected 'to' after value in Add statement")
        list_tok = self.expect(TokenType.IDENTIFIER, "Expected list name")
        self.expect_statement_terminator()
        return AddToList(value=value, list_name=list_tok.value, line=tok.line)

    def parse_remove_from_list(self) -> ASTNode:
        tok = self.advance()  # Remove
        value = self.parse_expression()
        self.expect(TokenType.FROM, "Expected 'from' after value in Remove statement")
        list_tok = self.expect(TokenType.IDENTIFIER, "Expected list name")
        self.expect_statement_terminator()
        return RemoveFromList(value=value, list_name=list_tok.value, line=tok.line)

    # ── Match ─────────────────────────────────────────────────────────────

    def parse_match(self) -> ASTNode:
        tok = self.advance()  # Match
        subject = self.parse_expression()
        self.expect_newline_or_eof()
        self.skip_newlines()

        cases = []
        while self.peek_type() not in (TokenType.END, TokenType.EOF):
            self.skip_newlines()
            if self.peek_type() == TokenType.END:
                break

            if self.peek_type() == TokenType.OTHERWISE:
                self.advance()
                self.expect_newline_or_eof()
                body = self.parse_block({TokenType.END}, is_match_body=True)
                cases.append((None, body))
                break

            # Parse case value
            case_value = self.parse_expression()

            # Check for range in match: value to value
            if self.peek_type() == TokenType.TO:
                self.advance()
                end_value = self.parse_expression()
                case_value = MatchRange(start=case_value, end=end_value, line=case_value.line)

            self.expect_newline_or_eof()
            body = self.parse_block({TokenType.END, TokenType.OTHERWISE}, is_match_body=True)
            cases.append((case_value, body))

        self.expect(TokenType.END, "Expected 'End' to close Match statement")
        self.expect_newline_or_eof()
        return MatchStatement(subject=subject, cases=cases, line=tok.line)

    # ── Try/Catch ─────────────────────────────────────────────────────────

    def parse_try(self) -> ASTNode:
        tok = self.advance()  # Try
        self.expect_newline_or_eof()
        try_body = self.parse_block({TokenType.CATCH})
        self.expect(TokenType.CATCH)
        self.expect_newline_or_eof()
        catch_body = self.parse_block({TokenType.END})
        self.expect(TokenType.END)
        self.expect_newline_or_eof()
        return TryCatch(try_body=try_body, catch_body=catch_body, line=tok.line)

    # ── Import ────────────────────────────────────────────────────────────

    def parse_import(self) -> ASTNode:
        tok = self.advance()
        path_tok = self.expect(TokenType.STRING, "Expected file path after 'Import'")
        self.expect_statement_terminator()
        return ImportStatement(filepath=path_tok.value, line=tok.line)

    # ── Identifier statement ──────────────────────────────────────────────

    def parse_identifier_statement(self) -> ASTNode:
        """Handle: property block, assignment, function call, method call, index assignment."""
        name_tok = self.advance()  # consume identifier
        line = name_tok.line

        # Property block, Layout block, or Component block
        if self.peek_type() in (TokenType.STRING, TokenType.LBRACE, TokenType.INTERP_STRING, TokenType.SEMICOLON, TokenType.EOF):
            # A component without braces e.g. `checkbox "Accept Terms";`
            if self.peek_type() in (TokenType.STRING, TokenType.INTERP_STRING):
                str_tok = self.advance()
                block_name = StringLiteral(value=str_tok.value, line=str_tok.line)
            else:
                block_name = None
            
            properties = []
            children = []

            if self.peek_type() == TokenType.LBRACE:
                self.advance() # consume {
                self.skip_newlines()
                while self.peek_type() != TokenType.RBRACE and not self.at_end():
                    tt = self.peek_type()
                    is_prop = False
                    
                    if tt in (TokenType.IDENTIFIER, TokenType.STYLE_KEYWORD) or tt.name.startswith("ON_"):
                        pa = self.peek_ahead_type()
                        if pa in (TokenType.COLON, TokenType.LBRACE):
                            is_prop = True

                    if is_prop:
                        prop_name_tok = self.advance()
                        if self.peek_type() == TokenType.COLON:
                            self.advance()
                            prop_val = self.parse_expression()
                            properties.append(Property(name=prop_name_tok.value, value=prop_val, line=prop_name_tok.line))
                        elif self.peek_type() == TokenType.LBRACE:
                            self.advance() # consume {
                            body = self.parse_block({TokenType.RBRACE})
                            self.expect(TokenType.RBRACE)
                            # Create anonymous function
                            func_val = FunctionDef(name=f"<{prop_name_tok.value}>", params=[], body=body, line=prop_name_tok.line)
                            properties.append(Property(name=prop_name_tok.value, value=func_val, line=prop_name_tok.line))
                        self.expect_property_terminator()
                    else:
                        stmt = self.parse_statement()
                        if stmt is not None:
                            children.append(stmt)
                    
                    self.skip_newlines()
                
                self.expect(TokenType.RBRACE, "Expected '}' to close block")

            self.expect_statement_terminator()
            
            val = name_tok.value
            if val in ("vstack", "hstack", "grid"):
                return LayoutBlock(layout_type=val, properties=properties, children=children, line=line)
            elif val in ("button", "input", "checkbox", "dropdown"):
                return ComponentBlock(component_type=val, name=block_name, properties=properties, children=children, line=line)
            else:
                return PropertyBlock(block_type=val, name=block_name, properties=properties, line=line)

        # Assignment: name = expr
        if self.peek_type() == TokenType.ASSIGN:
            self.advance()
            value = self.parse_expression()
            # Check for inline condition
            if self.peek_type() == TokenType.IF and self.peek().value == "if":
                value = self.parse_inline_condition(value)
            self.expect_statement_terminator()
            return Assignment(name=name_tok.value, value=value, line=line)

        # Dot access: name.attr = expr or name.method(args)
        if self.peek_type() == TokenType.DOT:
            obj = Identifier(name=name_tok.value, line=line)
            while self.peek_type() == TokenType.DOT:
                self.advance()  # consume .
                attr_tok = self.expect(TokenType.IDENTIFIER, "Expected attribute name after '.'")

                if self.peek_type() == TokenType.LPAREN:
                    # Method call
                    self.advance()
                    args = self.parse_arguments()
                    self.expect(TokenType.RPAREN)
                    obj = MethodCall(obj=obj, method_name=attr_tok.value, args=args, line=line)
                elif self.peek_type() == TokenType.ASSIGN:
                    # Attribute assignment
                    self.advance()
                    value = self.parse_expression()
                    self.expect_statement_terminator()
                    return MapAssignment(obj=obj, key=attr_tok.value, value=value, line=line)
                else:
                    obj = MapAccess(obj=obj, key=attr_tok.value, line=line)

            self.expect_statement_terminator()
            return obj

        # Index access: name[idx] = expr
        if self.peek_type() == TokenType.LBRACKET:
            self.advance()
            index = self.parse_expression()
            self.expect(TokenType.RBRACKET)
            obj = Identifier(name=name_tok.value, line=line)

            if self.peek_type() == TokenType.ASSIGN:
                self.advance()
                value = self.parse_expression()
                self.expect_statement_terminator()
                return ListAssignment(obj=obj, index=index, value=value, line=line)

            # Just an index access expression as statement — unusual but possible
            self.expect_statement_terminator()
            return ListAccess(obj=obj, index=index, line=line)

        # Function call: name(args)
        if self.peek_type() == TokenType.LPAREN:
            self.advance()
            args = self.parse_arguments()
            self.expect(TokenType.RPAREN)
            self.expect_statement_terminator()
            return FunctionCall(name=name_tok.value, args=args, line=line)

        raise VeltrixSyntaxError(
            f"Unexpected token after '{name_tok.value}'",
            self.filename, line
        )

    # ── Block ─────────────────────────────────────────────────────────────

    def parse_block(self, stop_tokens: set, is_match_body: bool = False) -> list:
        """Parse statements until we hit a stop token."""
        statements = []
        self.skip_newlines()

        while not self.at_end() and self.peek_type() not in stop_tokens:
            if is_match_body:
                # In match bodies, also stop at case values (numbers, strings)
                tt = self.peek_type()
                if tt in (TokenType.NUMBER, TokenType.STRING, TokenType.BOOLEAN,
                          TokenType.IDENTIFIER, TokenType.MINUS):
                    # Check if this looks like a new case (not part of expression)
                    # A new case starts at the beginning of a line after newlines
                    break

            stmt = self.parse_statement()
            if stmt is not None:
                statements.append(stmt)
            self.skip_newlines()

        return statements

    # ── Expressions ───────────────────────────────────────────────────────

    def parse_expression(self) -> ASTNode:
        """Entry point for expression parsing."""
        expr = self.parse_or()

        # Check for inline condition: expr if cond else other
        # Only handle this at top-level expression parse in certain contexts
        return expr

    def parse_inline_condition(self, true_value: ASTNode) -> ASTNode:
        """Parse: value if condition else other_value (already have true_value)."""
        tok = self.advance()  # consume 'if'
        condition = self.parse_or()
        self.expect(TokenType.ELSE, "Expected 'else' in inline condition")
        false_value = self.parse_or()
        return InlineCondition(true_value=true_value, condition=condition,
                               false_value=false_value, line=tok.line)

    def parse_or(self) -> ASTNode:
        left = self.parse_and()
        while self.peek_type() == TokenType.OR:
            op = self.advance()
            right = self.parse_and()
            left = BinaryOp(left=left, op="Or", right=right, line=op.line)
        return left

    def parse_and(self) -> ASTNode:
        left = self.parse_not()
        while self.peek_type() == TokenType.AND:
            op = self.advance()
            right = self.parse_not()
            left = BinaryOp(left=left, op="And", right=right, line=op.line)
        return left

    def parse_not(self) -> ASTNode:
        if self.peek_type() == TokenType.NOT:
            op = self.advance()
            operand = self.parse_not()
            return UnaryOp(op="Not", operand=operand, line=op.line)
        return self.parse_comparison()

    def parse_comparison(self) -> ASTNode:
        left = self.parse_is_check()
        comp_ops = {TokenType.EQ, TokenType.NEQ, TokenType.GT, TokenType.LT,
                    TokenType.GTE, TokenType.LTE}
        while self.peek_type() in comp_ops:
            op = self.advance()
            right = self.parse_is_check()
            left = BinaryOp(left=left, op=op.value, right=right, line=op.line)
        return left

    def parse_is_check(self) -> ASTNode:
        """Handle: expr is Null, expr is not Null."""
        left = self.parse_addition()

        if self.peek_type() == TokenType.IS:
            is_tok = self.advance()  # consume 'is'

            # is not Null
            if self.peek_type() == TokenType.NOT:
                self.advance()  # consume 'not'
                if self.peek_type() == TokenType.NULL:
                    self.advance()  # consume Null
                    return IsNotNullCheck(expression=left, line=is_tok.line)
                raise VeltrixSyntaxError(
                    "Expected 'Null' after 'is not'",
                    self.filename, is_tok.line
                )

            # is Null
            if self.peek_type() == TokenType.NULL:
                self.advance()  # consume Null
                return IsNullCheck(expression=left, line=is_tok.line)

            raise VeltrixSyntaxError(
                "Expected 'Null' or 'not Null' after 'is'",
                self.filename, is_tok.line
            )

        return left

    def parse_addition(self) -> ASTNode:
        left = self.parse_multiplication()
        while self.peek_type() in (TokenType.PLUS, TokenType.MINUS):
            op = self.advance()
            right = self.parse_multiplication()
            left = BinaryOp(left=left, op=op.value, right=right, line=op.line)
        return left

    def parse_multiplication(self) -> ASTNode:
        left = self.parse_unary()
        while self.peek_type() in (TokenType.STAR, TokenType.SLASH, TokenType.MODULO):
            op = self.advance()
            right = self.parse_unary()
            left = BinaryOp(left=left, op=op.value, right=right, line=op.line)
        return left

    def parse_unary(self) -> ASTNode:
        if self.peek_type() == TokenType.MINUS:
            op = self.advance()
            operand = self.parse_unary()
            return UnaryOp(op="-", operand=operand, line=op.line)
        return self.parse_postfix()

    def parse_postfix(self) -> ASTNode:
        """Handle member access (.key), index access ([expr]), and function calls (args)."""
        node = self.parse_primary()

        while True:
            if self.peek_type() == TokenType.DOT:
                self.advance()
                attr_tok = self.expect(TokenType.IDENTIFIER, "Expected attribute name after '.'")

                if self.peek_type() == TokenType.LPAREN:
                    # Method call
                    self.advance()
                    args = self.parse_arguments()
                    self.expect(TokenType.RPAREN)
                    node = MethodCall(obj=node, method_name=attr_tok.value, args=args, line=attr_tok.line)
                else:
                    node = MapAccess(obj=node, key=attr_tok.value, line=attr_tok.line)

            elif self.peek_type() == TokenType.LBRACKET:
                self.advance()
                index = self.parse_expression()
                self.expect(TokenType.RBRACKET)
                node = ListAccess(obj=node, index=index, line=node.line)

            elif self.peek_type() == TokenType.LPAREN:
                # Function call on expression result
                if isinstance(node, Identifier):
                    self.advance()
                    args = self.parse_arguments()
                    self.expect(TokenType.RPAREN)
                    node = FunctionCall(name=node.name, args=args, line=node.line)
                elif isinstance(node, MapAccess):
                    # obj.method(args)
                    self.advance()
                    args = self.parse_arguments()
                    self.expect(TokenType.RPAREN)
                    node = MethodCall(obj=node.obj, method_name=node.key,
                                     args=args, line=node.line)
                else:
                    break

            elif self.peek_type() == TokenType.DOTDOT:
                # Range: expr..expr
                self.advance()
                end = self.parse_addition()
                node = RangeExpression(start=node, end=end, line=node.line)

            else:
                break

        return node

    def parse_primary(self) -> ASTNode:
        """Parse a primary expression (literals, identifiers, grouped, etc.)."""
        tok = self.peek()

        if tok.type == TokenType.NUMBER:
            self.advance()
            return NumberLiteral(value=tok.value, line=tok.line)

        if tok.type == TokenType.STRING:
            self.advance()
            return StringLiteral(value=tok.value, line=tok.line)

        if tok.type == TokenType.INTERP_STRING:
            self.advance()
            return self.build_interpolation(tok)

        if tok.type == TokenType.BOOLEAN:
            self.advance()
            return BoolLiteral(value=tok.value, line=tok.line)

        if tok.type == TokenType.COLOR_HEX:
            self.advance()
            return ColorLiteral(value=tok.value, line=tok.line)

        if tok.type == TokenType.NULL:
            self.advance()
            return NullLiteral(line=tok.line)

        if tok.type == TokenType.SELF:
            self.advance()
            if self.peek_type() == TokenType.DOT:
                self.advance()
                attr_tok = self.expect(TokenType.IDENTIFIER, "Expected attribute name after 'Self.'")
                return SelfAccess(attribute=attr_tok.value, line=tok.line)
            raise VeltrixSyntaxError("Expected '.' after 'Self'", self.filename, tok.line)

        if tok.type == TokenType.IDENTIFIER:
            self.advance()
            if self.peek_type() in (TokenType.STRING, TokenType.INTERP_STRING):
                target = self.parse_expression()
                return StyleApplication(properties=[], gradient=None, target=target, style_name=tok.value, line=tok.line)
            return Identifier(name=tok.value, line=tok.line)

        if tok.type == TokenType.LPAREN:
            return self.parse_paren_expr()

        if tok.type == TokenType.LBRACKET:
            return self.parse_list_literal()

        if tok.type == TokenType.LBRACE:
            return self.parse_map_literal()

        if tok.type == TokenType.STYLE_KEYWORD:
            return self.parse_style_application()
            
        if tok.type == TokenType.STYLE:
            return self.parse_style_block()

        raise VeltrixSyntaxError(
            f"Unexpected token in expression: '{tok.value}'",
            self.filename, tok.line
        )

    def parse_paren_expr(self) -> ASTNode:
        """Parse parenthesized expression or arrow function."""
        open_tok = self.advance()  # consume (

        # Check if this looks like an arrow function: (params) => expr
        # Save position in case we need to backtrack
        saved_pos = self.pos

        # Try to parse as arrow function parameter list
        try:
            params = self._try_parse_arrow_params()
            if params is not None and self.peek_type() == TokenType.RPAREN:
                self.advance()  # consume )
                if self.peek_type() == TokenType.ARROW:
                    self.advance()  # consume =>
                    body = self.parse_expression()
                    return ArrowFunction(params=params, body=body, line=open_tok.line)
                else:
                    # Not an arrow function, backtrack
                    self.pos = saved_pos
            else:
                # Didn't look like arrow params, backtrack
                self.pos = saved_pos
        except (VeltrixSyntaxError, IndexError):
            self.pos = saved_pos

        # Regular parenthesized expression
        expr = self.parse_expression()
        self.expect(TokenType.RPAREN, "Expected closing ')'")
        return expr

    def _try_parse_arrow_params(self) -> list | None:
        """Try to parse arrow function params. Returns list of names or None."""
        params = []
        if self.peek_type() == TokenType.RPAREN:
            return params  # empty params

        while True:
            if self.peek_type() != TokenType.IDENTIFIER:
                return None
            params.append(self.advance().value)
            if self.peek_type() == TokenType.COMMA:
                self.advance()
            else:
                break
        return params

    def build_interpolation(self, tok: Token) -> ASTNode:
        """Build a StringInterpolation node from INTERP_STRING token."""
        parts = []
        for is_expr, content in tok.value:
            if is_expr:
                # Parse the expression
                lexer = Lexer(content + "\n", self.filename)
                inner_tokens = lexer.tokenize()
                inner_parser = Parser(inner_tokens, self.filename)
                expr = inner_parser.parse_expression()
                parts.append(expr)
            else:
                parts.append(StringLiteral(value=content, line=tok.line))
        return StringInterpolation(parts=parts, line=tok.line)

    def parse_list_literal(self) -> ASTNode:
        tok = self.advance()  # consume [
        elements = []
        self.skip_newlines()
        while self.peek_type() != TokenType.RBRACKET:
            elements.append(self.parse_expression())
            self.skip_newlines()
            if not self.match(TokenType.COMMA):
                break
            self.skip_newlines()
        self.expect(TokenType.RBRACKET, "Expected ']' to close list")
        return ListLiteral(elements=elements, line=tok.line)

    def parse_map_literal(self) -> ASTNode:
        tok = self.advance()  # consume {
        pairs = []
        self.skip_newlines()
        while self.peek_type() != TokenType.RBRACE:
            key_tok = self.expect(TokenType.IDENTIFIER, "Expected key name in map")
            self.expect(TokenType.COLON, "Expected ':' after map key")
            value = self.parse_expression()
            pairs.append((key_tok.value, value))
            self.skip_newlines()
            if not self.match(TokenType.COMMA):
                break
            self.skip_newlines()
        self.expect(TokenType.RBRACE, "Expected '}' to close map")
        return MapLiteral(pairs=pairs, line=tok.line)

    def parse_style_application(self) -> ASTNode:
        tok = self.advance() # consume bold, italic, color, bg...
        
        props = []
        gradient = None
        
        # Determine based on exact keyword
        if tok.value == "color":
            color_val = self.parse_expression() # could be string or color literal
            props.append(StyleProperty(name="color", value=color_val, line=tok.line))
        elif tok.value == "bg":
            bg_val = self.parse_expression()
            props.append(StyleProperty(name="bg", value=bg_val, line=tok.line))
        elif tok.value == "opacity":
            opacity_val = self.parse_expression()
            props.append(StyleProperty(name="opacity", value=opacity_val, line=tok.line))
        elif tok.value == "gradient":
            start_color = self.parse_expression()
            self.expect(TokenType.RIGHT_ARROW, "Expected '->' for gradient")
            end_color = self.parse_expression()
            gradient = GradientProperty(start_color=start_color, end_color=end_color, line=tok.line)
        else: # bold, italic, underline, strike
            # these are just boolean presence flags, we give them a BoolLiteral
            bool_true = BoolLiteral(value=True, line=tok.line)
            props.append(StyleProperty(name=tok.value, value=bool_true, line=tok.line))
            
        # Target should be exactly following
        target = self.parse_expression()
        
        return StyleApplication(properties=props, gradient=gradient, target=target, line=tok.line)

    def parse_style_block(self) -> ASTNode:
        tok = self.advance() # consume 'style'
        
        self.expect(TokenType.LBRACE, "Expected '{' after 'style'")
        self.skip_newlines()
        
        properties = []
        while self.peek_type() != TokenType.RBRACE and not self.at_end():
            if self.peek_type() in (TokenType.IDENTIFIER, TokenType.STYLE_KEYWORD):
                prop_name_tok = self.advance()
            else:
                raise VeltrixSyntaxError("Expected style property name", self.filename, self.current().line if self.pos < len(self.tokens) else tok.line)
            self.expect(TokenType.COLON, "Expected ':' after style property name")
            
            prop_val = self.parse_expression()
            properties.append(Property(name=prop_name_tok.value, value=prop_val, line=prop_name_tok.line))
            
            self.skip_newlines()
            if self.match(TokenType.COMMA):
                self.skip_newlines()
            
        self.expect(TokenType.RBRACE, "Expected '}' to close style block")
        
        target = None
        if self.peek_type() not in (TokenType.SEMICOLON, TokenType.NEWLINE, TokenType.EOF, TokenType.RBRACE, TokenType.RBRACKET, TokenType.RPAREN, TokenType.COMMA):
            target = self.parse_expression()
        
        return StyleBlock(properties=properties, target=target, line=tok.line)

    def parse_arguments(self) -> list:
        """Parse comma-separated argument list."""
        args = []
        if self.peek_type() == TokenType.RPAREN:
            return args
        args.append(self.parse_expression())
        while self.match(TokenType.COMMA):
            args.append(self.parse_expression())
        return args
