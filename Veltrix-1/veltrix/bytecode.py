"""
Veltrix Bytecode Definitions
==============================
Defines the instruction set (OpCode enum), Instruction tuple,
CodeObject container, and a human-readable disassembler.
"""

from enum import IntEnum, auto


# ─── Instruction Set ──────────────────────────────────────────────────────────

class OpCode(IntEnum):
    """All Veltrix VM opcodes."""

    # ── Constants & Literals ──
    LOAD_CONST      = 0    # operand = constant pool index
    LOAD_NULL       = 1    # push Null

    # ── Variables ──
    STORE_VAR       = 2    # operand = local slot index
    LOAD_VAR        = 3    # operand = local slot index
    STORE_GLOBAL    = 4    # operand = name constant index
    LOAD_GLOBAL     = 5    # operand = name constant index

    # ── Arithmetic ──
    ADD             = 10
    SUB             = 11
    MUL             = 12
    DIV             = 13
    MOD             = 14
    NEGATE          = 15

    # ── Comparison ──
    CMP_EQ          = 20
    CMP_NEQ         = 21
    CMP_GT          = 22
    CMP_GTE         = 23
    CMP_LT          = 24
    CMP_LTE         = 25

    # ── Logic ──
    AND             = 30
    OR              = 31
    NOT             = 32

    # ── Control Flow ──
    JUMP            = 40   # operand = absolute target
    JUMP_IF_FALSE   = 41   # operand = absolute target
    JUMP_IF_TRUE    = 42   # operand = absolute target
    POP_JUMP_IF_FALSE = 43 # pop + jump

    # ── Functions ──
    CALL            = 50   # operand = arg count
    RETURN          = 51
    MAKE_FUNCTION   = 52   # operand = const index of CodeObject

    # ── Data Structures ──
    BUILD_LIST      = 60   # operand = element count
    BUILD_MAP       = 61   # operand = pair count
    GET_INDEX       = 62   # stack: [obj, index] → value
    SET_INDEX       = 63   # stack: [obj, index, value] →
    GET_ATTR        = 64   # operand = name constant index
    SET_ATTR        = 65   # operand = name constant index
    LIST_APPEND     = 66   # stack: [list, value] →
    LIST_REMOVE     = 67   # stack: [list, value] →

    # ── I/O ──
    PRINT           = 70
    INPUT           = 71   # operand = prompt const index

    # ── Classes ──
    MAKE_CLASS      = 80   # operand = name const index; stack has method pairs
    MAKE_INSTANCE   = 81   # operand = arg count; stack: [class, args...]
    GET_SELF        = 82

    # ── Stack ──
    POP             = 90
    DUP             = 91

    # ── Special ──
    IS_NULL         = 95
    IS_NOT_NULL     = 96
    IMPORT          = 97   # operand = filepath const index
    BUILD_RANGE     = 98   # stack: [start, end] → range object
    SETUP_TRY       = 99   # operand = catch target address
    END_TRY         = 100
    STORE_CONST_VAR = 101  # operand = local slot index (constant variable)
    
    # ── Styling ──
    BUILD_STYLE     = 102  # operand = property count; stack: [target_str, prop_1_val, prop_1_name, ...]
    APPLY_STYLE     = 103  # stack: [target_str, style_obj] -> merged_style_obj

    # ── GUI ──
    BUILD_WINDOW    = 104  # operand = prop count; stack: [title_str, val1, key1, val2, key2...]
    SHOW_WINDOW     = 105  # no operand; triggers main loop
    BUILD_SHAPE     = 106  # operand = prop count; stack: [shape_type_str, val1, key1...]
    SETUP_LAYOUT    = 107  # operand = prop count; stack: [layout_type, val1, key1...]
    END_LAYOUT      = 108
    SETUP_COMPONENT = 109  # operand = prop count; stack: [comp_type, name, val1, key1...]
    END_COMPONENT   = 110


# ─── Instruction ──────────────────────────────────────────────────────────────

class Instruction:
    """A single bytecode instruction."""
    __slots__ = ("opcode", "operand", "line")

    def __init__(self, opcode: OpCode, operand: int = 0, line: int = 0):
        self.opcode = opcode
        self.operand = operand
        self.line = line

    def __repr__(self):
        name = OpCode(self.opcode).name
        if self.operand != 0:
            return f"{name}({self.operand}) @line {self.line}"
        return f"{name} @line {self.line}"


# ─── Code Object ──────────────────────────────────────────────────────────────

class CodeObject:
    """
    A compiled unit of Veltrix bytecode — represents one function or the
    top-level module.
    """

    def __init__(self, name: str = "<module>", source_file: str = "<unknown>"):
        self.name = name
        self.source_file = source_file
        self.instructions: list[Instruction] = []
        self.constants: list = []          # constant pool
        self.local_names: list[str] = []   # local variable name table
        self.num_params: int = 0
        self.num_locals: int = 0

    def add_instruction(self, opcode: OpCode, operand: int = 0,
                        line: int = 0) -> int:
        """Emit an instruction and return its index."""
        idx = len(self.instructions)
        self.instructions.append(Instruction(opcode, operand, line))
        return idx

    def add_constant(self, value) -> int:
        """Add a value to the constant pool and return its index."""
        # Re-use existing constants for simple types
        for i, existing in enumerate(self.constants):
            if type(existing) is type(value) and existing == value:
                # Don't deduplicate CodeObjects or mutable types
                if not isinstance(value, (CodeObject, list, dict)):
                    return i
        idx = len(self.constants)
        self.constants.append(value)
        return idx

    def add_local(self, name: str) -> int:
        """Register a local variable name and return its slot index."""
        if name in self.local_names:
            return self.local_names.index(name)
        idx = len(self.local_names)
        self.local_names.append(name)
        self.num_locals = len(self.local_names)
        return idx

    def resolve_local(self, name: str) -> int:
        """Find the slot index for a local variable, or -1 if not found."""
        try:
            return self.local_names.index(name)
        except ValueError:
            return -1

    def patch_jump(self, instr_index: int, target: int):
        """Patch a previously emitted jump instruction with its target."""
        self.instructions[instr_index].operand = target

    @property
    def size(self):
        return len(self.instructions)

    def __repr__(self):
        return f"<CodeObject '{self.name}' {len(self.instructions)} instructions>"


# ─── Disassembler ─────────────────────────────────────────────────────────────

def disassemble(code_obj: CodeObject, indent: int = 0) -> str:
    """
    Return a human-readable representation of a CodeObject's bytecode.
    Recursively disassembles nested CodeObjects (functions).
    """
    prefix = "  " * indent
    lines = []
    lines.append(f"{prefix}═══ {code_obj.name} ═══")
    lines.append(f"{prefix}  Source: {code_obj.source_file}")
    lines.append(f"{prefix}  Params: {code_obj.num_params}  "
                 f"Locals: {code_obj.num_locals}")

    # Constants
    if code_obj.constants:
        lines.append(f"{prefix}  Constants:")
        for i, c in enumerate(code_obj.constants):
            if isinstance(c, CodeObject):
                lines.append(f"{prefix}    [{i}] <CodeObject '{c.name}'>")
            else:
                lines.append(f"{prefix}    [{i}] {_format_const(c)}")

    # Locals
    if code_obj.local_names:
        lines.append(f"{prefix}  Locals: {code_obj.local_names}")

    # Instructions
    lines.append(f"{prefix}  Instructions:")
    last_line = -1
    for i, instr in enumerate(code_obj.instructions):
        op_name = OpCode(instr.opcode).name.ljust(22)
        operand_str = ""

        # Format operand nicely
        if instr.opcode in (OpCode.LOAD_CONST, OpCode.MAKE_FUNCTION):
            val = code_obj.constants[instr.operand] if instr.operand < len(code_obj.constants) else "?"
            if isinstance(val, CodeObject):
                operand_str = f"{instr.operand} (<fn {val.name}>)"
            else:
                operand_str = f"{instr.operand} ({_format_const(val)})"
        elif instr.opcode in (OpCode.STORE_VAR, OpCode.LOAD_VAR, OpCode.STORE_CONST_VAR):
            name = code_obj.local_names[instr.operand] if instr.operand < len(code_obj.local_names) else "?"
            operand_str = f"{instr.operand} ({name})"
        elif instr.opcode in (OpCode.STORE_GLOBAL, OpCode.LOAD_GLOBAL, OpCode.GET_ATTR,
                              OpCode.SET_ATTR, OpCode.MAKE_CLASS, OpCode.INPUT,
                              OpCode.IMPORT):
            val = code_obj.constants[instr.operand] if instr.operand < len(code_obj.constants) else "?"
            operand_str = f"{instr.operand} ({val})"
        elif instr.opcode in (OpCode.JUMP, OpCode.JUMP_IF_FALSE, OpCode.JUMP_IF_TRUE,
                              OpCode.POP_JUMP_IF_FALSE, OpCode.SETUP_TRY):
            operand_str = f"→ {instr.operand}"
        elif instr.opcode in (OpCode.CALL, OpCode.MAKE_INSTANCE, OpCode.BUILD_LIST,
                              OpCode.BUILD_MAP, OpCode.BUILD_STYLE,
                              OpCode.BUILD_WINDOW, OpCode.BUILD_SHAPE,
                              OpCode.SETUP_LAYOUT, OpCode.SETUP_COMPONENT):
            operand_str = str(instr.operand)
        elif instr.operand != 0:
            operand_str = str(instr.operand)

        # Line number gutter
        if instr.line != last_line:
            line_str = f"L{instr.line:<4}"
            last_line = instr.line
        else:
            line_str = "     "

        lines.append(f"{prefix}    {i:>4}  {line_str}  {op_name} {operand_str}")

    # Recurse into nested CodeObjects
    for c in code_obj.constants:
        if isinstance(c, CodeObject):
            lines.append("")
            lines.append(disassemble(c, indent + 1))

    return "\n".join(lines)


def _format_const(value) -> str:
    """Format a constant value for display."""
    if isinstance(value, str):
        return f'"{value}"'
    if value is None:
        return "Null"
    return repr(value)
