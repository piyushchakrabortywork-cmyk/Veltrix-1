"""
Veltrix Virtual Machine — Phase 2
====================================
Stack-based bytecode interpreter. Executes CodeObjects produced by the
Veltrix compiler. Features a value stack, call stack with frames,
instruction pointer, and heap for objects.
"""

import os
from veltrix.bytecode import OpCode, CodeObject, Instruction
from veltrix.runtime import (
    VeltrixNull, VeltrixClosure, VeltrixClass, VeltrixInstance, VeltrixRange,
    NativeFunction, is_truthy, format_value, create_builtins, type_of,
    VeltrixBoundMethod, VeltrixStyledText
)
from veltrix.styling import StyleValidator
from veltrix.errors import (
    VeltrixError, VeltrixVMError, VeltrixDivisionError, VeltrixTypeError,
    VeltrixIndexError, VeltrixKeyError, VeltrixNullError, VeltrixNameError,
    VeltrixAttributeError, VeltrixConstantError, StackTrace,
)


# ─── Call Frame ───────────────────────────────────────────────────────────────

class CallFrame:
    """Represents one activation record on the call stack."""
    __slots__ = ("code", "ip", "locals", "stack_base", "self_ref", "constants", "is_init")

    def __init__(self, code: CodeObject, stack_base: int, self_ref=None, is_init: bool = False):
        self.code = code
        self.ip = 0
        self.locals = [VeltrixNull] * code.num_locals
        self.stack_base = stack_base
        self.self_ref = self_ref  # instance for method calls
        self.constants: set = set()  # slots that are constants
        self.is_init = is_init

    @property
    def name(self):
        return self.code.name

    @property
    def source_file(self):
        return self.code.source_file


# ─── Try Context ──────────────────────────────────────────────────────────────

class TryContext:
    """Tracks a try/catch block for exception handling."""
    __slots__ = ("catch_target", "frame_index", "stack_depth")

    def __init__(self, catch_target, frame_index, stack_depth):
        self.catch_target = catch_target
        self.frame_index = frame_index
        self.stack_depth = stack_depth


# ─── Virtual Machine ─────────────────────────────────────────────────────────

class VeltrixVM:
    """
    The Veltrix stack-based virtual machine.
    Executes bytecode instructions from a CodeObject.
    """

    MAX_STACK = 65536
    MAX_FRAMES = 1024

    def __init__(self, filename: str = "<unknown>"):
        self.filename = filename
        self.stack: list = []
        self.frames: list[CallFrame] = []
        self.globals: dict = create_builtins()
        self.try_stack: list[TryContext] = []
        self.imported_files: set = set()

    @property
    def frame(self) -> CallFrame:
        """Current call frame."""
        return self.frames[-1]

    # ── Stack Operations ──────────────────────────────────────────────────

    def push(self, value):
        if len(self.stack) >= self.MAX_STACK:
            self.error("Stack overflow — too many nested operations.")
        self.stack.append(value)

    def pop(self):
        if not self.stack:
            self.error("Stack underflow — internal VM error.")
        return self.stack.pop()

    def peek(self, offset=0):
        return self.stack[-(1 + offset)]

    # ── Error Handling ────────────────────────────────────────────────────

    def build_stack_trace(self) -> StackTrace:
        trace = StackTrace()
        for f in self.frames:
            line = 0
            if f.ip > 0 and f.ip <= len(f.code.instructions):
                line = f.code.instructions[f.ip - 1].line
            elif f.code.instructions:
                line = f.code.instructions[0].line
            trace.push(f.code.name, f.code.source_file, line)
        return trace

    def error(self, message, hint=None):
        line = 0
        func_name = None
        if self.frames:
            f = self.frame
            if f.ip > 0 and f.ip <= len(f.code.instructions):
                line = f.code.instructions[f.ip - 1].line
            func_name = f.code.name if f.code.name != "<module>" else None
        raise VeltrixVMError(
            message, self.filename, line, hint,
            function_name=func_name,
            stack_trace=self.build_stack_trace()
        )

    # ── Main Execution ────────────────────────────────────────────────────

    def run(self, code: CodeObject):
        """Execute a compiled CodeObject."""
        # Initialize locals for top-level code
        frame = CallFrame(code, 0)
        self.frames.append(frame)
        
        # Set VM callback for GUI events
        from veltrix.gui import EventDispatcher
        EventDispatcher.set_vm_callback(self.call_closure_sync)
        
        self.execute()

    def call_closure_sync(self, closure, *args):
        if not closure or not isinstance(closure, VeltrixClosure):
            return
            
        base_frames = len(self.frames)
        func_code = closure.code
        
        new_frame = CallFrame(func_code, len(self.stack))
        for i, arg in enumerate(args):
            if i < len(new_frame.locals):
                new_frame.locals[i] = arg
                
        self.frames.append(new_frame)
        self.execute(target_frames=base_frames)

    def execute(self, target_frames: int = 0):
        """Main fetch-decode-execute loop."""
        while len(self.frames) > target_frames:
            frame = self.frame
            code = frame.code
            instructions = code.instructions

            while frame.ip < len(instructions):
                instr = instructions[frame.ip]
                frame.ip += 1
                op = instr.opcode

                try:
                    # ── Constants ──
                    if op == OpCode.LOAD_CONST:
                        self.push(code.constants[instr.operand])

                    elif op == OpCode.LOAD_NULL:
                        self.push(VeltrixNull)

                    # ── Variables ──
                    elif op == OpCode.STORE_VAR:
                        frame.locals[instr.operand] = self.pop()

                    elif op == OpCode.LOAD_VAR:
                        val = frame.locals[instr.operand]
                        self.push(val)

                    elif op == OpCode.STORE_CONST_VAR:
                        slot = instr.operand
                        value = self.pop()
                        if slot in frame.constants:
                            # This is a reassignment of a constant — raise error
                            var_name = frame.code.local_names[slot] if slot < len(frame.code.local_names) else "<unknown>"
                            raise VeltrixConstantError(
                                var_name,
                                self.filename, instr.line,
                                stack_trace=self.build_stack_trace()
                            )
                        frame.locals[slot] = value
                        frame.constants.add(slot)

                    elif op == OpCode.STORE_GLOBAL:
                        name = code.constants[instr.operand]
                        self.globals[name] = self.pop()

                    elif op == OpCode.LOAD_GLOBAL:
                        name = code.constants[instr.operand]
                        if name in self.globals:
                            self.push(self.globals[name])
                        else:
                            # Try to find in enclosing frames' locals
                            found = False
                            for f in reversed(self.frames[:-1]):
                                slot = f.code.resolve_local(name)
                                if slot >= 0:
                                    self.push(f.locals[slot])
                                    found = True
                                    break
                            if not found:
                                raise VeltrixNameError(
                                    name, self.filename, instr.line,
                                    stack_trace=self.build_stack_trace()
                                )

                    # ── Arithmetic ──
                    elif op == OpCode.ADD:
                        right = self.pop()
                        left = self.pop()
                        if isinstance(left, str) or isinstance(right, str):
                            self.push(format_value(left) + format_value(right))
                        else:
                            try:
                                self.push(left + right)
                            except TypeError:
                                self.push(format_value(left) + format_value(right))

                    elif op == OpCode.SUB:
                        right = self.pop()
                        left = self.pop()
                        self.push(left - right)

                    elif op == OpCode.MUL:
                        right = self.pop()
                        left = self.pop()
                        self.push(left * right)

                    elif op == OpCode.DIV:
                        right = self.pop()
                        left = self.pop()
                        if right == 0:
                            raise VeltrixDivisionError(
                                self.filename, instr.line,
                                stack_trace=self.build_stack_trace()
                            )
                        result = left / right
                        if isinstance(left, int) and isinstance(right, int) and result == int(result):
                            self.push(int(result))
                        else:
                            self.push(result)

                    elif op == OpCode.MOD:
                        right = self.pop()
                        left = self.pop()
                        if right == 0:
                            raise VeltrixDivisionError(
                                self.filename, instr.line,
                                stack_trace=self.build_stack_trace()
                            )
                        self.push(left % right)

                    elif op == OpCode.NEGATE:
                        self.push(-self.pop())

                    # ── Comparison ──
                    elif op == OpCode.CMP_EQ:
                        right = self.pop()
                        left = self.pop()
                        self.push(left == right)

                    elif op == OpCode.CMP_NEQ:
                        right = self.pop()
                        left = self.pop()
                        self.push(left != right)

                    elif op == OpCode.CMP_GT:
                        right = self.pop()
                        left = self.pop()
                        self.push(left > right)

                    elif op == OpCode.CMP_GTE:
                        right = self.pop()
                        left = self.pop()
                        self.push(left >= right)

                    elif op == OpCode.CMP_LT:
                        right = self.pop()
                        left = self.pop()
                        self.push(left < right)

                    elif op == OpCode.CMP_LTE:
                        right = self.pop()
                        left = self.pop()
                        self.push(left <= right)

                    # ── Logic ──
                    elif op == OpCode.AND:
                        right = self.pop()
                        left = self.pop()
                        self.push(is_truthy(left) and is_truthy(right))

                    elif op == OpCode.OR:
                        right = self.pop()
                        left = self.pop()
                        self.push(is_truthy(left) or is_truthy(right))

                    elif op == OpCode.NOT:
                        self.push(not is_truthy(self.pop()))

                    # ── Control Flow ──
                    elif op == OpCode.JUMP:
                        frame.ip = instr.operand

                    elif op == OpCode.JUMP_IF_FALSE:
                        if not is_truthy(self.peek()):
                            frame.ip = instr.operand

                    elif op == OpCode.JUMP_IF_TRUE:
                        if is_truthy(self.peek()):
                            frame.ip = instr.operand

                    elif op == OpCode.POP_JUMP_IF_FALSE:
                        val = self.pop()
                        if not is_truthy(val):
                            frame.ip = instr.operand

                    # ── Functions ──
                    elif op == OpCode.CALL:
                        arg_count = instr.operand
                        self._call_value(arg_count, instr.line)
                        # After a call, we're in the new frame
                        frame = self.frame
                        code = frame.code
                        instructions = code.instructions
                        continue

                    elif op == OpCode.RETURN:
                        return_value = self.pop()
                        old_frame = self.frames.pop()

                        if not self.frames:
                            return  # Top-level return

                        # Restore stack
                        self.stack = self.stack[:old_frame.stack_base]
                        
                        if old_frame.is_init:
                            # If returning from Init, return the instance (Self)
                            self.push(old_frame.locals[0])
                        else:
                            self.push(return_value)

                        frame = self.frame
                        code = frame.code
                        instructions = code.instructions
                        continue

                    elif op == OpCode.MAKE_FUNCTION:
                        func_code = code.constants[instr.operand]
                        closure = VeltrixClosure(func_code)
                        self.push(closure)

                    # ── Data Structures ──
                    elif op == OpCode.BUILD_LIST:
                        count = instr.operand
                        elements = []
                        for _ in range(count):
                            elements.append(self.pop())
                        elements.reverse()
                        self.push(elements)

                    elif op == OpCode.BUILD_MAP:
                        count = instr.operand
                        pairs = []
                        for _ in range(count):
                            val = self.pop()
                            key = self.pop()
                            pairs.append((key, val))
                        pairs.reverse()
                        self.push({k: v for k, v in pairs})

                    elif op == OpCode.BUILD_STYLE:
                        count = instr.operand
                        properties = {}
                        for _ in range(count):
                            val = self.pop()
                            name = self.pop()
                            properties[name] = val
                            
                        target = self.pop()
                        target_str = format_value(target)
                        
                        # Validate properties before applying them
                        StyleValidator.validate_properties(properties, self.filename, instr.line)
                        
                        self.push(VeltrixStyledText(target_str, properties))

                    elif op == OpCode.GET_INDEX:
                        index = self.pop()
                        obj = self.pop()
                        if isinstance(obj, list):
                            idx = int(index)
                            if idx < 0 or idx >= len(obj):
                                raise VeltrixIndexError(idx, len(obj), self.filename, instr.line)
                            self.push(obj[idx])
                        elif isinstance(obj, dict):
                            key = str(index)
                            if key not in obj:
                                raise VeltrixKeyError(key, self.filename, instr.line)
                            self.push(obj[key])
                        elif isinstance(obj, str):
                            idx = int(index)
                            if idx < 0 or idx >= len(obj):
                                raise VeltrixIndexError(idx, len(obj), self.filename, instr.line)
                            self.push(obj[idx])
                        elif isinstance(obj, VeltrixRange):
                            idx = int(index)
                            if idx < 0 or idx >= len(obj):
                                raise VeltrixIndexError(idx, len(obj), self.filename, instr.line)
                            self.push(obj[idx])
                        else:
                            self.error(f"Cannot index into {type_of(obj)}.")

                    elif op == OpCode.SET_INDEX:
                        value = self.pop()
                        index = self.pop()
                        obj = self.pop()
                        if isinstance(obj, list):
                            idx = int(index)
                            if idx < 0 or idx >= len(obj):
                                raise VeltrixIndexError(idx, len(obj), self.filename, instr.line)
                            obj[idx] = value
                        elif isinstance(obj, dict):
                            obj[str(index)] = value
                        else:
                            self.error(f"Cannot set index on {type_of(obj)}.")

                    elif op == OpCode.GET_ATTR:
                        name = code.constants[instr.operand]
                        obj = self.pop()
                        if obj is VeltrixNull:
                            raise VeltrixNullError(
                                f"Cannot access '{name}' on Null.",
                                self.filename, instr.line,
                                stack_trace=self.build_stack_trace()
                            )
                        if isinstance(obj, VeltrixInstance):
                            self.push(obj.get(name))
                        elif isinstance(obj, dict):
                            if name in obj:
                                self.push(obj[name])
                            else:
                                # Check for built-in dict methods
                                raise VeltrixKeyError(name, self.filename, instr.line)
                        elif isinstance(obj, list):
                            if name == "length":
                                self.push(len(obj))
                            else:
                                self.error(f"List does not have attribute '{name}'.")
                        elif isinstance(obj, str):
                            if name == "length":
                                self.push(len(obj))
                            else:
                                self.error(f"String does not have attribute '{name}'.")
                        elif isinstance(obj, VeltrixClass):
                            if name in obj.methods:
                                self.push(obj.methods[name])
                            else:
                                raise VeltrixAttributeError(obj.name, name, self.filename, instr.line)
                        else:
                            self.error(f"Cannot access attribute '{name}' on {type_of(obj)}.")

                    elif op == OpCode.SET_ATTR:
                        name = code.constants[instr.operand]
                        value = self.pop()
                        obj = self.pop()
                        if obj is VeltrixNull:
                            raise VeltrixNullError(
                                f"Cannot set '{name}' on Null.",
                                self.filename, instr.line,
                                stack_trace=self.build_stack_trace()
                            )
                        if isinstance(obj, VeltrixInstance):
                            obj.set(name, value)
                        elif isinstance(obj, dict):
                            obj[name] = value
                        else:
                            self.error(f"Cannot set attribute on {type_of(obj)}.")

                    elif op == OpCode.LIST_APPEND:
                        value = self.pop()
                        lst = self.pop()
                        if not isinstance(lst, list):
                            self.error("'Add' can only be used with lists.")
                        lst.append(value)

                    elif op == OpCode.LIST_REMOVE:
                        value = self.pop()
                        lst = self.pop()
                        if not isinstance(lst, list):
                            self.error("'Remove' can only be used with lists.")
                        if value in lst:
                            lst.remove(value)
                        else:
                            self.error(f"Value {format_value(value)} not found in list.")

                    # ── I/O ──
                    elif op == OpCode.PRINT:
                        value = self.pop()
                        print(format_value(value))

                    elif op == OpCode.INPUT:
                        prompt_value = self.pop()
                        prompt_str = format_value(prompt_value)
                        result = input(prompt_str)
                        # Try to convert to number
                        try:
                            result = int(result)
                        except ValueError:
                            try:
                                result = float(result)
                            except ValueError:
                                pass
                        self.push(result)

                    # ── Classes ──
                    elif op == OpCode.MAKE_CLASS:
                        name = code.constants[instr.operand]
                        method_count = self.pop()
                        if not isinstance(method_count, int):
                            method_count = int(method_count)
                        methods = {}
                        for _ in range(method_count):
                            method_fn = self.pop()
                            method_name = self.pop()
                            methods[method_name] = method_fn
                        klass = VeltrixClass(name, methods)
                        self.push(klass)

                    elif op == OpCode.MAKE_INSTANCE:
                        # Instance creation handled in CALL
                        pass

                    elif op == OpCode.GET_SELF:
                        # Push Self reference from current frame
                        if frame.self_ref is not None:
                            self.push(frame.self_ref)
                        else:
                            # Look for Self in locals
                            slot = frame.code.resolve_local("Self")
                            if slot >= 0:
                                self.push(frame.locals[slot])
                            else:
                                self.error("'Self' can only be used inside a class method.")

                    # ── Stack ──
                    elif op == OpCode.POP:
                        self.pop()

                    elif op == OpCode.DUP:
                        self.push(self.peek())

                    # ── Null checks ──
                    elif op == OpCode.IS_NULL:
                        val = self.pop()
                        self.push(val is VeltrixNull)

                    elif op == OpCode.IS_NOT_NULL:
                        val = self.pop()
                        self.push(val is not VeltrixNull)

                    # ── Range ──
                    elif op == OpCode.BUILD_RANGE:
                        end = self.pop()
                        start = self.pop()
                        self.push(VeltrixRange(start, end))

                    # ── Styling ──
                    elif op == OpCode.BUILD_STYLE:
                        prop_count = instr.operand
                        properties = {}
                        
                        for _ in range(prop_count):
                            val = self.pop()
                            key = self.pop()
                            if not isinstance(key, str):
                                self.error(f"Style property name must be a string, got {type_of(key)}", instr.line)
                            properties[key] = val
                            
                        target = self.pop()
                        target = str(target) if target is not VeltrixNull else "Null"
                        
                        StyleValidator.validate(properties)
                        
                        self.push(VeltrixStyledText(text=target, properties=properties))

                    elif op == OpCode.APPLY_STYLE:
                        style_obj = self.pop()
                        target = self.pop()
                        
                        if getattr(style_obj, 'properties', None) is None:
                            self.error(f"Cannot apply styling from non-style object of type '{type_of(style_obj)}'", instr.line)
                            
                        # Merge the styles with the target
                        # Currently VeltrixStyledText just copies it.
                        self.push(VeltrixStyledText(text=target, properties=style_obj.properties))

                    # ── GUI ──
                    elif op == OpCode.BUILD_WINDOW:
                        prop_count = instr.operand
                        properties = {}
                        for _ in range(prop_count):
                            val = self.pop()
                            key = self.pop()
                            if not isinstance(key, str):
                                self.error(f"Window property name must be a string, got {type_of(key)}", instr.line)
                            properties[key] = val
                            
                        title = self.pop()
                        title_str = format_value(title) if title is not VeltrixNull else "Veltrix Window"
                        
                        from veltrix.gui import WindowManager
                        WindowManager.create_window(title_str, properties, self.filename, instr.line)
                        
                    elif op == OpCode.BUILD_SHAPE:
                        prop_count = instr.operand
                        properties = {}
                        for _ in range(prop_count):
                            val = self.pop()
                            key = self.pop()
                            if not isinstance(key, str):
                                self.error(f"Shape property name must be a string, got {type_of(key)}", instr.line)
                            properties[key] = val
                            
                        shape_type = self.pop()
                        
                        from veltrix.gui import WindowManager
                        WindowManager.add_shape(shape_type, properties, self.filename, instr.line)
                        
                    elif op == OpCode.SETUP_LAYOUT:
                        prop_count = instr.operand
                        properties = {}
                        for _ in range(prop_count):
                            val = self.pop()
                            key = self.pop()
                            if not isinstance(key, str):
                                self.error(f"Layout property name must be a string, got {type_of(key)}", instr.line)
                            properties[key] = val
                            
                        layout_type = self.pop()
                        
                        from veltrix.gui import WindowManager
                        WindowManager.setup_layout(layout_type, properties, self.filename, instr.line)
                        
                    elif op == OpCode.END_LAYOUT:
                        from veltrix.gui import WindowManager
                        WindowManager.end_layout(self.filename, instr.line)
                        
                    elif op == OpCode.SETUP_COMPONENT:
                        prop_count = instr.operand
                        properties = {}
                        for _ in range(prop_count):
                            val = self.pop()
                            key = self.pop()
                            if not isinstance(key, str):
                                self.error(f"Component property name must be a string, got {type_of(key)}", instr.line)
                            properties[key] = val
                            
                        name = self.pop()
                        component_type = self.pop()
                        
                        from veltrix.gui import WindowManager
                        WindowManager.setup_component(component_type, name, properties, self.filename, instr.line)
                        
                    elif op == OpCode.END_COMPONENT:
                        from veltrix.gui import WindowManager
                        WindowManager.end_component(self.filename, instr.line)

                    elif op == OpCode.SHOW_WINDOW:
                        from veltrix.gui import WindowManager
                        WindowManager.show_window(self.filename, instr.line)

                    # ── Import ──
                    elif op == OpCode.IMPORT:
                        filepath = code.constants[instr.operand]
                        self._do_import(filepath, instr.line)

                    # ── Try/Catch ──
                    elif op == OpCode.SETUP_TRY:
                        self.try_stack.append(TryContext(
                            catch_target=instr.operand,
                            frame_index=len(self.frames) - 1,
                            stack_depth=len(self.stack)
                        ))

                    elif op == OpCode.END_TRY:
                        if self.try_stack:
                            self.try_stack.pop()

                    else:
                        self.error(f"Unknown opcode: {op}")

                except VeltrixError as e:
                    if self._handle_exception(e, instr.line):
                        frame = self.frame
                        code = frame.code
                        instructions = code.instructions
                        continue
                    raise

            # If we reach end of instructions and we're in a function frame
            if self.frames:
                old_frame = self.frames.pop()
                if self.frames:
                    self.push(VeltrixNull)
                    frame = self.frame
                    code = frame.code
                    instructions = code.instructions
                else:
                    return

    # ── Function Calls ────────────────────────────────────────────────────

    def _call_value(self, arg_count: int, line: int):
        """Call a value on the stack (function, class, native, etc.)."""
        callee = self.stack[-(arg_count + 1)]

        if isinstance(callee, VeltrixClosure):
            self._call_closure(callee, arg_count, line)

        elif isinstance(callee, NativeFunction):
            self._call_native(callee, arg_count, line)

        elif isinstance(callee, VeltrixClass):
            self._call_class(callee, arg_count, line)

        elif isinstance(callee, VeltrixBoundMethod):
            self._call_bound_method(callee, arg_count, line)

        elif callable(callee):
            # Python callable (e.g., lambda from old runtime)
            args = []
            for _ in range(arg_count):
                args.append(self.pop())
            args.reverse()
            self.pop()  # pop callee
            try:
                result = callee(*args)
            except Exception as e:
                self.error(str(e))
            self.push(result if result is not None else VeltrixNull)
            # Don't enter a new frame — result already pushed

        else:
            self.error(f"Cannot call {type_of(callee)}. Only functions and classes are callable.")

    def _call_class(self, klass: VeltrixClass, arg_count: int, line: int):
        """Instantiate a class and call its Init method if present."""
        instance = VeltrixInstance(klass)
        
        if "Init" in klass.methods:
            init_closure = klass.methods["Init"]
            func_code = init_closure.code
            
            # num_params includes Self
            if arg_count + 1 != func_code.num_params:
                self.error(
                    f"Constructor for '{klass.name}' expects {func_code.num_params - 1} "
                    f"argument(s), got {arg_count}.",
                    hint="Check the arguments passed to the class."
                )

            args = []
            for _ in range(arg_count):
                args.append(self.pop())
            args.reverse()
            self.pop()  # pop the class
            
            # Create new frame, marked as an init frame
            new_frame = CallFrame(func_code, len(self.stack), is_init=True)
            
            # Setup locals: Self is [0], args are [1:]
            new_frame.locals[0] = instance
            for i, arg in enumerate(args):
                new_frame.locals[i + 1] = arg
                
            if len(self.frames) >= self.MAX_FRAMES:
                self.error("Maximum call depth exceeded — possible infinite recursion.")
                
            self.frames.append(new_frame)
        else:
            if arg_count > 0:
                self.error(f"Class '{klass.name}' takes no arguments.")
            self.pop()  # pop the class
            self.push(instance)

    def _call_bound_method(self, bound: VeltrixBoundMethod, arg_count: int, line: int):
        """Call a bound method on an instance."""
        func_code = bound.method.code
        
        # num_params includes Self
        if arg_count + 1 != func_code.num_params:
            self.error(
                f"Method '{bound.name}' expects {func_code.num_params - 1} "
                f"argument(s), got {arg_count}.",
                hint="Check the arguments passed to the method."
            )

        args = []
        for _ in range(arg_count):
            args.append(self.pop())
        args.reverse()
        self.pop()  # pop the bound method object
        
        # Create new frame
        new_frame = CallFrame(func_code, len(self.stack))
        
        # Setup locals: Self is [0], args are [1:]
        new_frame.locals[0] = bound.instance
        for i, arg in enumerate(args):
            new_frame.locals[i + 1] = arg
            
        if len(self.frames) >= self.MAX_FRAMES:
            self.error("Maximum call depth exceeded — possible infinite recursion.")
            
        self.frames.append(new_frame)

    def _call_closure(self, closure: VeltrixClosure, arg_count: int, line: int):
        """Call a Veltrix closure (user-defined function)."""
        func_code = closure.code
        if arg_count != func_code.num_params:
            self.error(
                f"Function '{closure.name}' expects {func_code.num_params} "
                f"argument(s), got {arg_count}.",
                hint="Check the number of arguments in your function call."
            )

        # Gather args
        args = []
        for _ in range(arg_count):
            args.append(self.pop())
        args.reverse()
        self.pop()  # pop the closure itself

        # Create new frame
        new_frame = CallFrame(func_code, len(self.stack))
        for i, arg in enumerate(args):
            new_frame.locals[i] = arg

        if len(self.frames) >= self.MAX_FRAMES:
            self.error("Maximum call depth exceeded — possible infinite recursion.")

        self.frames.append(new_frame)

    def _call_native(self, native: NativeFunction, arg_count: int, line: int):
        """Call a native/built-in function."""
        args = []
        for _ in range(arg_count):
            args.append(self.pop())
        args.reverse()
        self.pop()  # pop the native function

        try:
            result = native.func(*args)
        except Exception as e:
            self.error(str(e))

        self.push(result if result is not None else VeltrixNull)

    def _call_class(self, klass: VeltrixClass, arg_count: int, line: int):
        """Instantiate a class."""
        instance = VeltrixInstance(klass)

        # Gather constructor args
        args = []
        for _ in range(arg_count):
            args.append(self.pop())
        args.reverse()
        self.pop()  # pop the class

        # Call Init method if it exists
        if "Init" in klass.methods:
            init_method = klass.methods["Init"]
            if isinstance(init_method, VeltrixClosure):
                func_code = init_method.code
                expected = func_code.num_params - 1  # minus Self
                if arg_count != expected:
                    self.error(
                        f"Constructor '{klass.name}.Init' expects {expected} "
                        f"argument(s), got {arg_count}."
                    )
                # Push instance (for return), then create frame
                self.push(instance)  # placeholder for return value

                new_frame = CallFrame(func_code, len(self.stack), self_ref=instance)
                # First param is Self
                new_frame.locals[0] = instance
                for i, arg in enumerate(args):
                    new_frame.locals[i + 1] = arg

                self.frames.append(new_frame)
                # Execute Init
                self.execute()
                # After Init returns, pop its return value (Null) and push instance
                if self.stack and self.stack[-1] is not instance:
                    self.pop()  # discard Init's return
                    self.push(instance)
                return

        self.push(instance)

    # ── Method Call Support ───────────────────────────────────────────────

    def _call_method_on_instance(self, instance: VeltrixInstance,
                                 method: VeltrixClosure, arg_count: int,
                                 line: int):
        """Call a method on an instance, binding Self."""
        func_code = method.code
        expected = func_code.num_params - 1  # minus Self
        if arg_count != expected:
            self.error(
                f"Method '{method.name}' expects {expected} "
                f"argument(s), got {arg_count}."
            )

        args = []
        for _ in range(arg_count):
            args.append(self.pop())
        args.reverse()
        self.pop()  # pop the method closure

        # We need to also find the instance on stack
        # Actually in the GET_ATTR flow, the instance was already consumed
        # We need a different approach for method calls

        new_frame = CallFrame(func_code, len(self.stack), self_ref=instance)
        new_frame.locals[0] = instance  # Self
        for i, arg in enumerate(args):
            new_frame.locals[i + 1] = arg

        self.frames.append(new_frame)

    # ── Exception Handling ────────────────────────────────────────────────

    def _handle_exception(self, error: VeltrixError, line: int) -> bool:
        """Try to handle an exception with a try/catch block. Returns True if handled."""
        while self.try_stack:
            ctx = self.try_stack.pop()
            # Unwind frames to the try frame
            while len(self.frames) > ctx.frame_index + 1:
                self.frames.pop()
            # Unwind stack
            while len(self.stack) > ctx.stack_depth:
                self.stack.pop()
            # Jump to catch
            self.frame.ip = ctx.catch_target
            return True
        return False

    # ── Import ────────────────────────────────────────────────────────────

    def _do_import(self, filepath: str, line: int):
        """Import and execute another .vlx file."""
        # Resolve relative to current file
        base_dir = os.path.dirname(self.filename)
        full_path = os.path.normpath(os.path.join(base_dir, filepath))

        if not full_path.endswith(".vlx"):
            full_path += ".vlx"

        if full_path in self.imported_files:
            return  # already imported

        if not os.path.exists(full_path):
            self.error(f"Import error: file '{filepath}' not found.")

        self.imported_files.add(full_path)

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                source = f.read()
        except Exception as e:
            self.error(f"Import error: could not read '{filepath}': {e}")

        from veltrix.lexer import Lexer
        from veltrix.parser import Parser
        from veltrix.compiler import Compiler

        lexer = Lexer(source, full_path)
        tokens = lexer.tokenize()
        parser = Parser(tokens, full_path)
        program = parser.parse()
        compiler = Compiler(full_path)
        code = compiler.compile(program)

        # Execute imported code in a new frame, sharing globals
        import_frame = CallFrame(code, len(self.stack))
        self.frames.append(import_frame)
        self.execute()
