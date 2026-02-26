"""
Veltrix Bytecode Compiler — Phase 2
=====================================
Walks the AST and emits bytecode instructions into CodeObjects.
Handles scope management, constant pool, and function compilation.
"""

from veltrix.ast_nodes import *
from veltrix.bytecode import OpCode, CodeObject
from veltrix.runtime import VeltrixNull
from veltrix.errors import VeltrixCompileError


class Compiler:
    """
    Compiles a Veltrix AST into a CodeObject containing bytecode instructions.
    """

    def __init__(self, filename: str = "<unknown>"):
        self.filename = filename
        self.code_stack: list[CodeObject] = []  # stack of code objects being compiled
        self.scope_depth = 0
        self.constants_set: set = set()  # track constant variable names

    @property
    def code(self) -> CodeObject:
        """The current CodeObject being compiled into."""
        return self.code_stack[-1]

    def emit(self, opcode: OpCode, operand: int = 0, line: int = 0) -> int:
        """Emit an instruction and return its index."""
        return self.code.add_instruction(opcode, operand, line)

    def emit_constant(self, value, line: int = 0) -> int:
        """Add a constant and emit LOAD_CONST."""
        idx = self.code.add_constant(value)
        return self.emit(OpCode.LOAD_CONST, idx, line)

    # ── Main Entry ────────────────────────────────────────────────────────

    def compile(self, program: Program) -> CodeObject:
        """Compile a full program into a top-level CodeObject."""
        code = CodeObject(name="<module>", source_file=self.filename)
        self.code_stack.append(code)

        for stmt in program.statements:
            self.compile_statement(stmt)

        # Ensure there's always a return
        if not code.instructions or code.instructions[-1].opcode != OpCode.RETURN:
            self.emit(OpCode.LOAD_NULL, line=0)
            self.emit(OpCode.RETURN, line=0)

        self.code_stack.pop()
        return code

    # ── Statement Dispatch ────────────────────────────────────────────────

    def compile_statement(self, node: ASTNode):
        """Compile a single statement node."""
        line = node.line

        if isinstance(node, LetDeclaration):
            self.compile_let(node)
        elif isinstance(node, ConstantDeclaration):
            self.compile_constant_decl(node)
        elif isinstance(node, Assignment):
            self.compile_assignment(node)
        elif isinstance(node, WriteStatement):
            self.compile_write(node)
        elif isinstance(node, AskStatement):
            self.compile_ask(node)
        elif isinstance(node, IfStatement):
            self.compile_if(node)
        elif isinstance(node, ForLoop):
            self.compile_for(node)
        elif isinstance(node, ForEachLoop):
            self.compile_foreach(node)
        elif isinstance(node, WhileLoop):
            self.compile_while(node)
        elif isinstance(node, FunctionDef):
            self.compile_function_def(node)
        elif isinstance(node, ReturnStatement):
            self.compile_return(node)
        elif isinstance(node, FunctionCall):
            self.compile_expression(node)
            self.emit(OpCode.POP, line=line)
        elif isinstance(node, MethodCall):
            self.compile_expression(node)
            self.emit(OpCode.POP, line=line)
        elif isinstance(node, AddToList):
            self.compile_add_to_list(node)
        elif isinstance(node, RemoveFromList):
            self.compile_remove_from_list(node)
        elif isinstance(node, MatchStatement):
            self.compile_match(node)
        elif isinstance(node, TryCatch):
            self.compile_try_catch(node)
        elif isinstance(node, ImportStatement):
            self.compile_import(node)
        elif isinstance(node, ClassDef):
            self.compile_class(node)
        elif isinstance(node, SelfAssignment):
            self.compile_self_assignment(node)
        elif isinstance(node, ListAssignment):
            self.compile_list_assignment(node)
        elif isinstance(node, MapAssignment):
            self.compile_map_assignment(node)
        elif isinstance(node, MapAccess):
            # Allow standalone member access as statement (e.g. obj.method – rare)
            self.compile_expression(node)
            self.emit(OpCode.POP, line=line)
        elif isinstance(node, PropertyBlock):
            self.compile_property_block(node)
        elif isinstance(node, LayoutBlock):
            self.compile_layout_block(node)
        elif isinstance(node, ComponentBlock):
            self.compile_component_block(node)
        elif isinstance(node, ShowWindowStmt):
            self.compile_show_window(node)
        else:
            raise VeltrixCompileError(
                f"Cannot compile statement: {type(node).__name__}",
                self.filename, line
            )

    # ── Expression Dispatch ───────────────────────────────────────────────

    def compile_expression(self, node: ASTNode):
        """Compile an expression, leaving its value on the stack."""
        line = node.line

        if isinstance(node, NumberLiteral):
            self.emit_constant(node.value, line)
        elif isinstance(node, StringLiteral):
            self.emit_constant(node.value, line)
        elif isinstance(node, BoolLiteral):
            self.emit_constant(node.value, line)
        elif isinstance(node, ColorLiteral):
            # Hex colors are essentially strings in VM 1.0/2.0
            self.emit_constant(node.value, line)
        elif isinstance(node, NullLiteral):
            self.emit(OpCode.LOAD_NULL, line=line)
        elif isinstance(node, Identifier):
            self.compile_load_variable(node.name, line)
        elif isinstance(node, BinaryOp):
            self.compile_binary_op(node)
        elif isinstance(node, UnaryOp):
            self.compile_unary_op(node)
        elif isinstance(node, FunctionCall):
            self.compile_function_call(node)
        elif isinstance(node, MethodCall):
            self.compile_method_call(node)
        elif isinstance(node, ListLiteral):
            for elem in node.elements:
                self.compile_expression(elem)
            self.emit(OpCode.BUILD_LIST, len(node.elements), line)
        elif isinstance(node, MapLiteral):
            for key, val in node.pairs:
                self.emit_constant(key, line)
                self.compile_expression(val)
            self.emit(OpCode.BUILD_MAP, len(node.pairs), line)
        elif isinstance(node, ListAccess):
            self.compile_expression(node.obj)
            self.compile_expression(node.index)
            self.emit(OpCode.GET_INDEX, line=line)
        elif isinstance(node, MapAccess):
            self.compile_expression(node.obj)
            name_idx = self.code.add_constant(node.key)
            self.emit(OpCode.GET_ATTR, name_idx, line)
        elif isinstance(node, SelfAccess):
            self.emit(OpCode.GET_SELF, line=line)
            name_idx = self.code.add_constant(node.attribute)
            self.emit(OpCode.GET_ATTR, name_idx, line)
        elif isinstance(node, ArrowFunction):
            self.compile_arrow_function(node)
        elif isinstance(node, StringInterpolation):
            self.compile_interpolation(node)
        elif isinstance(node, RangeExpression):
            self.compile_expression(node.start)
            self.compile_expression(node.end)
            self.emit(OpCode.BUILD_RANGE, line=line)
        elif isinstance(node, InlineCondition):
            self.compile_inline_condition(node)
        elif isinstance(node, IsNullCheck):
            self.compile_expression(node.expression)
            self.emit(OpCode.IS_NULL, line=line)
        elif isinstance(node, IsNotNullCheck):
            self.compile_expression(node.expression)
            self.emit(OpCode.IS_NOT_NULL, line=line)
        elif isinstance(node, StyleApplication):
            self.compile_style_application(node)
        elif isinstance(node, StyleBlock):
            self.compile_style_block(node)
        else:
            raise VeltrixCompileError(
                f"Cannot compile expression: {type(node).__name__}",
                self.filename, line
            )

    # ── Variable Operations ───────────────────────────────────────────────

    def compile_load_variable(self, name: str, line: int):
        """Load a variable — check locals first, then globals."""
        slot = self.code.resolve_local(name)
        if slot >= 0:
            self.emit(OpCode.LOAD_VAR, slot, line)
        else:
            name_idx = self.code.add_constant(name)
            self.emit(OpCode.LOAD_GLOBAL, name_idx, line)

    def compile_store_variable(self, name: str, line: int, is_new: bool = True):
        """Store a variable — locals if in function scope, globals at top level."""
        if self.scope_depth > 0 or len(self.code_stack) > 1:
            # We're inside a function or nested scope — use locals
            slot = self.code.resolve_local(name)
            if slot < 0:
                slot = self.code.add_local(name)
            self.emit(OpCode.STORE_VAR, slot, line)
        else:
            # Top-level — use globals
            slot = self.code.resolve_local(name)
            if slot < 0 and is_new:
                slot = self.code.add_local(name)
            if slot >= 0:
                self.emit(OpCode.STORE_VAR, slot, line)
            else:
                name_idx = self.code.add_constant(name)
                self.emit(OpCode.STORE_GLOBAL, name_idx, line)

    # ── GUI ───────────────────────────────────────────────────────────────

    def compile_property_block(self, node: PropertyBlock):
        line = node.line
        if node.block_type == "window":
            if node.name:
                self.compile_expression(node.name)
            else:
                self.emit(OpCode.LOAD_NULL, line=line)
                
            prop_count = 0
            for prop in node.properties:
                self.emit_constant(prop.name, line)
                self.compile_expression(prop.value)
                prop_count += 1
                
            self.emit(OpCode.BUILD_WINDOW, prop_count, line)
            
        elif node.block_type in ("rectangle", "circle", "line"):
            self.emit_constant(node.block_type, line)
            
            prop_count = 0
            for prop in node.properties:
                self.emit_constant(prop.name, line)
                self.compile_expression(prop.value)
                prop_count += 1
                
            self.emit(OpCode.BUILD_SHAPE, prop_count, line)

    def compile_layout_block(self, node: LayoutBlock):
        line = node.line
        self.emit_constant(node.layout_type, line)
        prop_count = 0
        for prop in node.properties:
            self.emit_constant(prop.name, line)
            self.compile_expression(prop.value)
            prop_count += 1
        self.emit(OpCode.SETUP_LAYOUT, prop_count, line)
        for child in node.children:
            self.compile_statement(child)
        self.emit(OpCode.END_LAYOUT, 0, line)

    def compile_component_block(self, node: ComponentBlock):
        line = node.line
        self.emit_constant(node.component_type, line)
        if node.name:
            self.compile_expression(node.name)
        else:
            self.emit(OpCode.LOAD_NULL, line)
            
        prop_count = 0
        for prop in node.properties:
            self.emit_constant(prop.name, line)
            self.compile_expression(prop.value)
            prop_count += 1
        self.emit(OpCode.SETUP_COMPONENT, prop_count, line)
        for child in node.children:
            self.compile_statement(child)
        self.emit(OpCode.END_COMPONENT, 0, line)

    def compile_show_window(self, node: ShowWindowStmt):
        self.emit(OpCode.SHOW_WINDOW, line=node.line)

    # ── Let & Constant ────────────────────────────────────────────────────

    def compile_let(self, node: LetDeclaration):
        self.compile_expression(node.value)
        name = node.name
        slot = self.code.add_local(name)
        self.emit(OpCode.STORE_VAR, slot, node.line)

    def compile_constant_decl(self, node: ConstantDeclaration):
        self.compile_expression(node.value)
        name = node.name
        self.constants_set.add(name)
        slot = self.code.add_local(name)
        self.emit(OpCode.STORE_CONST_VAR, slot, node.line)

    # ── Assignment ────────────────────────────────────────────────────────

    def compile_assignment(self, node: Assignment):
        self.compile_expression(node.value)
        slot = self.code.resolve_local(node.name)
        if slot >= 0:
            # Check if this is a constant at compile time
            if node.name in self.constants_set:
                self.emit(OpCode.STORE_CONST_VAR, slot, node.line)
            else:
                self.emit(OpCode.STORE_VAR, slot, node.line)
        else:
            name_idx = self.code.add_constant(node.name)
            self.emit(OpCode.STORE_GLOBAL, name_idx, node.line)

    def compile_list_assignment(self, node: ListAssignment):
        self.compile_expression(node.obj)
        self.compile_expression(node.index)
        self.compile_expression(node.value)
        self.emit(OpCode.SET_INDEX, line=node.line)

    def compile_map_assignment(self, node: MapAssignment):
        self.compile_expression(node.obj)
        self.compile_expression(node.value)
        name_idx = self.code.add_constant(node.key)
        self.emit(OpCode.SET_ATTR, name_idx, node.line)

    def compile_self_assignment(self, node: SelfAssignment):
        self.emit(OpCode.GET_SELF, line=node.line)
        self.compile_expression(node.value)
        name_idx = self.code.add_constant(node.attribute)
        self.emit(OpCode.SET_ATTR, name_idx, node.line)

    # ── Write & Ask ───────────────────────────────────────────────────────

    def compile_write(self, node: WriteStatement):
        self.compile_expression(node.expression)
        self.emit(OpCode.PRINT, line=node.line)

    def compile_ask(self, node: AskStatement):
        self.compile_expression(node.prompt)
        prompt_display_idx = self.code.add_constant("__prompt__")
        self.emit(OpCode.INPUT, 0, node.line)
        self.compile_store_variable(node.variable, node.line)

    # ── If ────────────────────────────────────────────────────────────────

    def compile_if(self, node: IfStatement):
        self.compile_expression(node.condition)
        # Jump to else branch if false
        else_jump = self.emit(OpCode.POP_JUMP_IF_FALSE, 0, node.line)

        # Compile then body
        for stmt in node.body:
            self.compile_statement(stmt)

        if node.else_body:
            # Jump over else branch
            end_jump = self.emit(OpCode.JUMP, 0, node.line)
            # Patch else jump target
            self.code.patch_jump(else_jump, self.code.size)
            # Compile else body
            for stmt in node.else_body:
                self.compile_statement(stmt)
            # Patch end jump target
            self.code.patch_jump(end_jump, self.code.size)
        else:
            self.code.patch_jump(else_jump, self.code.size)

    # ── For ───────────────────────────────────────────────────────────────

    def compile_for(self, node: ForLoop):
        line = node.line
        var_name = node.variable

        # Initialize loop variable: var = start
        self.compile_expression(node.start)
        slot = self.code.add_local(var_name)
        self.emit(OpCode.STORE_VAR, slot, line)

        # Compute end and store in a temp
        self.compile_expression(node.end)
        end_slot = self.code.add_local(f"__for_end_{var_name}__")
        self.emit(OpCode.STORE_VAR, end_slot, line)

        # Compute step (default 1)
        if node.step:
            self.compile_expression(node.step)
        else:
            self.emit_constant(1, line)
        step_slot = self.code.add_local(f"__for_step_{var_name}__")
        self.emit(OpCode.STORE_VAR, step_slot, line)

        # Loop condition: var <= end
        loop_start = self.code.size
        self.emit(OpCode.LOAD_VAR, slot, line)
        self.emit(OpCode.LOAD_VAR, end_slot, line)
        self.emit(OpCode.CMP_LTE, line=line)
        exit_jump = self.emit(OpCode.POP_JUMP_IF_FALSE, 0, line)

        # Body
        for stmt in node.body:
            self.compile_statement(stmt)

        # Increment: var = var + step
        self.emit(OpCode.LOAD_VAR, slot, line)
        self.emit(OpCode.LOAD_VAR, step_slot, line)
        self.emit(OpCode.ADD, line=line)
        self.emit(OpCode.STORE_VAR, slot, line)

        # Jump back to loop start
        self.emit(OpCode.JUMP, loop_start, line)
        # Patch exit
        self.code.patch_jump(exit_jump, self.code.size)

    def compile_foreach(self, node: ForEachLoop):
        line = node.line
        var_name = node.variable

        # Evaluate iterable and store
        self.compile_expression(node.iterable)
        iter_slot = self.code.add_local(f"__foreach_iter_{var_name}__")
        self.emit(OpCode.STORE_VAR, iter_slot, line)

        # Index counter
        self.emit_constant(0, line)
        idx_slot = self.code.add_local(f"__foreach_idx_{var_name}__")
        self.emit(OpCode.STORE_VAR, idx_slot, line)

        # Loop variable
        var_slot = self.code.add_local(var_name)

        # Length check: idx < length(iterable)
        loop_start = self.code.size

        # Get length: we push iterable, then use a special approach
        # We'll compute: idx < len via instructions
        self.emit(OpCode.LOAD_VAR, idx_slot, line)
        # Push iterable and get its length (we'll use GET_ATTR with "length" or a built-in)
        # Simplification: use a helper approach — store length in a temp too
        # Let's compute length once before the loop starts
        # Actually, let's restructure: compute len before loop
        # We need to backtrack — let's emit length before the loop
        # Insert before loop_start... Actually let's use a simpler approach with a length slot

        # OK, let's redo: compute length before loop
        # Remove the idx < len instruction we just emitted
        self.code.instructions.pop()  # remove LOAD_VAR idx

        # Compute length
        self.emit(OpCode.LOAD_VAR, iter_slot, line)
        # We need a built-in length call. Let's load the global 'length' function and call it
        len_name_idx = self.code.add_constant("length")
        self.emit(OpCode.LOAD_GLOBAL, len_name_idx, line)
        self.emit(OpCode.LOAD_VAR, iter_slot, line)
        self.emit(OpCode.CALL, 1, line)
        len_slot = self.code.add_local(f"__foreach_len_{var_name}__")
        self.emit(OpCode.STORE_VAR, len_slot, line)

        # Now actual loop start
        loop_start = self.code.size
        self.emit(OpCode.LOAD_VAR, idx_slot, line)
        self.emit(OpCode.LOAD_VAR, len_slot, line)
        self.emit(OpCode.CMP_LT, line=line)
        exit_jump = self.emit(OpCode.POP_JUMP_IF_FALSE, 0, line)

        # var = iterable[idx]
        self.emit(OpCode.LOAD_VAR, iter_slot, line)
        self.emit(OpCode.LOAD_VAR, idx_slot, line)
        self.emit(OpCode.GET_INDEX, line=line)
        self.emit(OpCode.STORE_VAR, var_slot, line)

        # Body
        for stmt in node.body:
            self.compile_statement(stmt)

        # idx += 1
        self.emit(OpCode.LOAD_VAR, idx_slot, line)
        self.emit_constant(1, line)
        self.emit(OpCode.ADD, line=line)
        self.emit(OpCode.STORE_VAR, idx_slot, line)

        # Jump back
        self.emit(OpCode.JUMP, loop_start, line)
        self.code.patch_jump(exit_jump, self.code.size)

    # ── While ─────────────────────────────────────────────────────────────

    def compile_while(self, node: WhileLoop):
        line = node.line
        loop_start = self.code.size

        self.compile_expression(node.condition)
        exit_jump = self.emit(OpCode.POP_JUMP_IF_FALSE, 0, line)

        for stmt in node.body:
            self.compile_statement(stmt)

        self.emit(OpCode.JUMP, loop_start, line)
        self.code.patch_jump(exit_jump, self.code.size)

    # ── Functions ─────────────────────────────────────────────────────────

    def compile_function_def(self, node: FunctionDef):
        """Compile a function definition into a nested CodeObject."""
        func_code = CodeObject(name=node.name, source_file=self.filename)
        func_code.num_params = len(node.params)

        # Register params as locals
        for p in node.params:
            if isinstance(p, TypedParam):
                func_code.add_local(p.name)
            else:
                func_code.add_local(p)

        # Compile function body
        self.code_stack.append(func_code)
        saved_constants = self.constants_set.copy()

        for stmt in node.body:
            self.compile_statement(stmt)

        # Ensure return
        if not func_code.instructions or func_code.instructions[-1].opcode != OpCode.RETURN:
            self.emit(OpCode.LOAD_NULL, line=node.line)
            self.emit(OpCode.RETURN, line=node.line)

        self.constants_set = saved_constants
        self.code_stack.pop()

        # Emit MAKE_FUNCTION in parent code
        func_idx = self.code.add_constant(func_code)
        self.emit(OpCode.MAKE_FUNCTION, func_idx, node.line)

        # Store function by name
        slot = self.code.add_local(node.name)
        self.emit(OpCode.STORE_VAR, slot, node.line)

    def compile_arrow_function(self, node: ArrowFunction):
        """Compile an arrow function: (params) => expr."""
        func_code = CodeObject(name="<arrow>", source_file=self.filename)
        func_code.num_params = len(node.params)

        for p in node.params:
            func_code.add_local(p)

        self.code_stack.append(func_code)

        # The body is a single expression — compile and return it
        self.compile_expression(node.body)
        self.emit(OpCode.RETURN, line=node.line)

        self.code_stack.pop()

        func_idx = self.code.add_constant(func_code)
        self.emit(OpCode.MAKE_FUNCTION, func_idx, node.line)

    # ── Function Call ─────────────────────────────────────────────────────

    def compile_function_call(self, node: FunctionCall):
        line = node.line
        if node.obj:
            # Method call via FunctionCall with obj (legacy path)
            self.compile_expression(node.obj)
            name_idx = self.code.add_constant(node.name)
            self.emit(OpCode.GET_ATTR, name_idx, line)
            for arg in node.args:
                self.compile_expression(arg)
            self.emit(OpCode.CALL, len(node.args), line)
        else:
            # Regular function call
            self.compile_load_variable(node.name, line)
            for arg in node.args:
                self.compile_expression(arg)
            self.emit(OpCode.CALL, len(node.args), line)

    def compile_method_call(self, node: MethodCall):
        line = node.line
        self.compile_expression(node.obj)
        name_idx = self.code.add_constant(node.method_name)
        self.emit(OpCode.GET_ATTR, name_idx, line)
        for arg in node.args:
            self.compile_expression(arg)
        self.emit(OpCode.CALL, len(node.args), line)

    # ── Return ────────────────────────────────────────────────────────────

    def compile_return(self, node: ReturnStatement):
        if node.value:
            self.compile_expression(node.value)
        else:
            self.emit(OpCode.LOAD_NULL, line=node.line)
        self.emit(OpCode.RETURN, line=node.line)

    # ── Add/Remove from list ──────────────────────────────────────────────

    def compile_add_to_list(self, node: AddToList):
        self.compile_load_variable(node.list_name, node.line)
        self.compile_expression(node.value)
        self.emit(OpCode.LIST_APPEND, line=node.line)

    def compile_remove_from_list(self, node: RemoveFromList):
        self.compile_load_variable(node.list_name, node.line)
        self.compile_expression(node.value)
        self.emit(OpCode.LIST_REMOVE, line=node.line)

    # ── Match ─────────────────────────────────────────────────────────────

    def compile_match(self, node: MatchStatement):
        line = node.line
        end_jumps = []

        for case_value, case_body in node.cases:
            if case_value is None:
                # Otherwise (default) case
                for stmt in case_body:
                    self.compile_statement(stmt)
                break

            if isinstance(case_value, MatchRange):
                # Range case: subject >= start And subject <= end
                self.compile_expression(node.subject)
                self.compile_expression(case_value.start)
                self.emit(OpCode.CMP_GTE, line=line)
                first_check = self.emit(OpCode.POP_JUMP_IF_FALSE, 0, line)

                self.compile_expression(node.subject)
                self.compile_expression(case_value.end)
                self.emit(OpCode.CMP_LTE, line=line)
                second_check = self.emit(OpCode.POP_JUMP_IF_FALSE, 0, line)

                for stmt in case_body:
                    self.compile_statement(stmt)
                end_jumps.append(self.emit(OpCode.JUMP, 0, line))

                self.code.patch_jump(first_check, self.code.size)
                self.code.patch_jump(second_check, self.code.size)
            else:
                # Exact match
                self.compile_expression(node.subject)
                self.compile_expression(case_value)
                self.emit(OpCode.CMP_EQ, line=line)
                skip_jump = self.emit(OpCode.POP_JUMP_IF_FALSE, 0, line)

                for stmt in case_body:
                    self.compile_statement(stmt)
                end_jumps.append(self.emit(OpCode.JUMP, 0, line))

                self.code.patch_jump(skip_jump, self.code.size)

        for j in end_jumps:
            self.code.patch_jump(j, self.code.size)

    # ── Try/Catch ─────────────────────────────────────────────────────────

    def compile_try_catch(self, node: TryCatch):
        line = node.line
        # SETUP_TRY → catch_target
        setup = self.emit(OpCode.SETUP_TRY, 0, line)

        for stmt in node.try_body:
            self.compile_statement(stmt)

        self.emit(OpCode.END_TRY, line=line)
        end_jump = self.emit(OpCode.JUMP, 0, line)

        # Catch target
        self.code.patch_jump(setup, self.code.size)

        for stmt in node.catch_body:
            self.compile_statement(stmt)

        self.code.patch_jump(end_jump, self.code.size)

    # ── Import ────────────────────────────────────────────────────────────

    def compile_import(self, node: ImportStatement):
        path_idx = self.code.add_constant(node.filepath)
        self.emit(OpCode.IMPORT, path_idx, node.line)

    # ── Class ─────────────────────────────────────────────────────────────

    def compile_class(self, node: ClassDef):
        line = node.line

        # Compile each method into a CodeObject
        method_count = len(node.methods)
        for method in node.methods:
            # Compile method as a function
            func_code = CodeObject(name=method.name, source_file=self.filename)
            # 'Self' is always first param (implicit), plus declared params
            func_code.add_local("Self")
            func_code.num_params = len(method.params) + 1  # +1 for Self

            for p in method.params:
                if isinstance(p, TypedParam):
                    func_code.add_local(p.name)
                else:
                    func_code.add_local(p)

            self.code_stack.append(func_code)
            for stmt in method.body:
                self.compile_statement(stmt)
            # Ensure return
            if not func_code.instructions or func_code.instructions[-1].opcode != OpCode.RETURN:
                self.emit(OpCode.LOAD_NULL, line=line)
                self.emit(OpCode.RETURN, line=line)
            self.code_stack.pop()

            # Push method name and CodeObject
            self.emit_constant(method.name, line)
            func_idx = self.code.add_constant(func_code)
            self.emit(OpCode.MAKE_FUNCTION, func_idx, line)

        # MAKE_CLASS with name and method count
        self.emit_constant(method_count, line)  # push method count
        name_idx = self.code.add_constant(node.name)
        self.emit(OpCode.MAKE_CLASS, name_idx, line)

        # Store class by name
        slot = self.code.add_local(node.name)
        self.emit(OpCode.STORE_VAR, slot, line)

    # ── Binary Operators ──────────────────────────────────────────────────

    def compile_binary_op(self, node: BinaryOp):
        line = node.line
        self.compile_expression(node.left)
        self.compile_expression(node.right)

        op_map = {
            "+": OpCode.ADD,
            "-": OpCode.SUB,
            "*": OpCode.MUL,
            "/": OpCode.DIV,
            "%": OpCode.MOD,
            "==": OpCode.CMP_EQ,
            "!=": OpCode.CMP_NEQ,
            ">": OpCode.CMP_GT,
            ">=": OpCode.CMP_GTE,
            "<": OpCode.CMP_LT,
            "<=": OpCode.CMP_LTE,
            "And": OpCode.AND,
            "Or": OpCode.OR,
        }

        if node.op in op_map:
            self.emit(op_map[node.op], line=line)
        else:
            raise VeltrixCompileError(
                f"Unknown operator: '{node.op}'",
                self.filename, line
            )

    # ── Unary Operators ───────────────────────────────────────────────────

    def compile_unary_op(self, node: UnaryOp):
        self.compile_expression(node.operand)
        if node.op == "-":
            self.emit(OpCode.NEGATE, line=node.line)
        elif node.op == "Not":
            self.emit(OpCode.NOT, line=node.line)
        else:
            raise VeltrixCompileError(
                f"Unknown unary operator: '{node.op}'",
                self.filename, node.line
            )

    # ── String Interpolation ──────────────────────────────────────────────

    def compile_interpolation(self, node: StringInterpolation):
        """Compile "Hello {name}" into concatenation sequence."""
        if not node.parts:
            self.emit_constant("", node.line)
            return

        # Compile first part
        self.compile_expression(node.parts[0])

        # Concatenate remaining parts
        for part in node.parts[1:]:
            self.compile_expression(part)
            self.emit(OpCode.ADD, line=node.line)

    # ── Inline Condition ──────────────────────────────────────────────────

    def compile_inline_condition(self, node: InlineCondition):
        line = node.line
        self.compile_expression(node.condition)
        else_jump = self.emit(OpCode.POP_JUMP_IF_FALSE, 0, line)
        self.compile_expression(node.true_value)
        end_jump = self.emit(OpCode.JUMP, 0, line)
        self.code.patch_jump(else_jump, self.code.size)
        self.compile_expression(node.false_value)
        self.code.patch_jump(end_jump, self.code.size)

    # ── Styling ───────────────────────────────────────────────────────────

    def compile_style_application(self, node: StyleApplication):
        """Build a style map and then emit BUILD_STYLE."""
        line = node.line
        
        # Load the target expression first (it'll be at bottom of stack chunk)
        if node.target:
            self.compile_expression(node.target)
        else:
            from .ast_nodes import NullLiteral
            self.compile_expression(NullLiteral(line=line))
            
        if getattr(node, 'style_name', None):
            # Load the style block and apply it
            from .ast_nodes import Identifier
            self.compile_expression(Identifier(name=node.style_name, line=line))
            self.emit(OpCode.APPLY_STYLE, 0, line)
            return

        
        prop_count = 0
        for prop in node.properties:
            self.emit_constant(prop.name, line)
            self.compile_expression(prop.value)
            prop_count += 1
            
        if node.gradient:
            self.emit_constant("gradient_start", line)
            self.compile_expression(node.gradient.start_color)
            self.emit_constant("gradient_end", line)
            self.compile_expression(node.gradient.end_color)
            prop_count += 2
            
        self.emit(OpCode.BUILD_STYLE, prop_count, line)

    def compile_style_block(self, node: StyleBlock):
        line = node.line
        if node.target:
            self.compile_expression(node.target)
        else:
            from .ast_nodes import NullLiteral
            self.compile_expression(NullLiteral(line=line))
        
        prop_count = 0
        for prop in node.properties:
            self.emit_constant(prop.name, line)
            self.compile_expression(prop.value)
            prop_count += 1
            
        # gradient property would just be a generic property here, or parsed specifically.
        # we can just use the generic ones for now block.
            
        self.emit(OpCode.BUILD_STYLE, prop_count, line)
