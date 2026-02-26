"""
Veltrix Error System — Phase 2
================================
Custom exception classes with beginner-friendly error messages.
Includes stack trace support for the bytecode VM.
"""


# ─── Stack Trace ──────────────────────────────────────────────────────────────

class StackTraceEntry:
    """One frame in a Veltrix stack trace."""
    __slots__ = ("function_name", "filename", "line")

    def __init__(self, function_name, filename, line):
        self.function_name = function_name
        self.filename = filename
        self.line = line

    def __repr__(self):
        return f"  in {self.function_name}() at {self.filename}:{self.line}"


class StackTrace:
    """Collects and formats a chain of call frames for error display."""

    def __init__(self):
        self.entries: list[StackTraceEntry] = []

    def push(self, function_name, filename, line):
        self.entries.append(StackTraceEntry(function_name, filename, line))

    def format(self):
        if not self.entries:
            return ""
        lines = ["  Stack trace (most recent call last):"]
        for entry in self.entries:
            fn = entry.function_name or "<module>"
            lines.append(f"    → {fn}()  [{entry.filename}, line {entry.line}]")
        return "\n".join(lines)


# ─── Base Error ───────────────────────────────────────────────────────────────

class VeltrixError(Exception):
    """Base class for all Veltrix errors."""

    def __init__(self, message, filename=None, line=None, hint=None,
                 function_name=None, stack_trace=None):
        self.message = message
        self.filename = filename or "<unknown>"
        self.line = line
        self.hint = hint
        self.function_name = function_name
        self.stack_trace = stack_trace
        super().__init__(self.format())

    def format(self):
        parts = [
            "",
            "╔══════════════════════════════════════════════╗",
            "║         Veltrix Runtime Error                ║",
            "╚══════════════════════════════════════════════╝",
        ]
        parts.append(f"  File: {self.filename}")
        if self.line is not None:
            parts.append(f"  Line: {self.line}")
        if self.function_name:
            parts.append(f"  Function: {self.function_name}")
        parts.append("")
        parts.append(f"  {self.message}")
        if self.hint:
            parts.append(f"  💡 {self.hint}")
        if self.stack_trace:
            parts.append("")
            parts.append(self.stack_trace.format())
        parts.append("")
        return "\n".join(parts)


# ─── Syntax & Compile Errors ─────────────────────────────────────────────────

class VeltrixSyntaxError(VeltrixError):
    """Raised when the parser encounters invalid syntax."""

    def __init__(self, message, filename=None, line=None, hint=None):
        if hint is None:
            hint = "Check your syntax and make sure all blocks are closed with 'End'."
        super().__init__(message, filename, line, hint)

    def format(self):
        parts = [
            "",
            "╔══════════════════════════════════════════════╗",
            "║         Veltrix Syntax Error                 ║",
            "╚══════════════════════════════════════════════╝",
        ]
        parts.append(f"  File: {self.filename}")
        if self.line is not None:
            parts.append(f"  Line: {self.line}")
        parts.append("")
        parts.append(f"  {self.message}")
        if self.hint:
            parts.append(f"  💡 {self.hint}")
        parts.append("")
        return "\n".join(parts)


class VeltrixCompileError(VeltrixError):
    """Raised during bytecode compilation."""

    def __init__(self, message, filename=None, line=None, hint=None):
        if hint is None:
            hint = "There is a problem compiling your program."
        super().__init__(message, filename, line, hint)

    def format(self):
        parts = [
            "",
            "╔══════════════════════════════════════════════╗",
            "║         Veltrix Compile Error                ║",
            "╚══════════════════════════════════════════════╝",
        ]
        parts.append(f"  File: {self.filename}")
        if self.line is not None:
            parts.append(f"  Line: {self.line}")
        parts.append("")
        parts.append(f"  {self.message}")
        if self.hint:
            parts.append(f"  💡 {self.hint}")
        parts.append("")
        return "\n".join(parts)


# ─── Runtime Errors ───────────────────────────────────────────────────────────

class VeltrixRuntimeError(VeltrixError):
    """Raised for general runtime errors during execution."""

    def __init__(self, message, filename=None, line=None, hint=None,
                 function_name=None, stack_trace=None):
        super().__init__(message, filename, line, hint, function_name, stack_trace)


class VeltrixVMError(VeltrixError):
    """Raised during VM execution."""

    def __init__(self, message, filename=None, line=None, hint=None,
                 function_name=None, stack_trace=None):
        super().__init__(message, filename, line, hint, function_name, stack_trace)


class VeltrixNameError(VeltrixError):
    """Raised when an undefined variable is referenced."""

    def __init__(self, name, filename=None, line=None, function_name=None,
                 stack_trace=None):
        message = f"Variable '{name}' is not defined."
        hint = "Make sure you declared this variable with 'Let' before using it."
        super().__init__(message, filename, line, hint, function_name, stack_trace)


class VeltrixConstantError(VeltrixError):
    """Raised when trying to reassign a constant."""

    def __init__(self, name, filename=None, line=None, stack_trace=None):
        message = f"Cannot reassign constant '{name}'."
        hint = "Constants declared with 'Constant' cannot be changed after creation."
        super().__init__(message, filename, line, hint, stack_trace=stack_trace)


class VeltrixDivisionError(VeltrixError):
    """Raised on division by zero."""

    def __init__(self, filename=None, line=None, function_name=None,
                 stack_trace=None):
        message = "You tried to divide by zero."
        hint = "A number cannot be divided by zero."
        super().__init__(message, filename, line, hint, function_name, stack_trace)


class VeltrixTypeError(VeltrixError):
    """Raised on type mismatch."""

    def __init__(self, message, filename=None, line=None, function_name=None,
                 stack_trace=None):
        hint = "Check the types of your values."
        super().__init__(message, filename, line, hint, function_name, stack_trace)


class VeltrixIndexError(VeltrixError):
    """Raised when a list index is out of range."""

    def __init__(self, index, length, filename=None, line=None):
        message = f"Index {index} is out of range for a list of length {length}."
        hint = "List indices start at 0. Make sure your index is within bounds."
        super().__init__(message, filename, line, hint)


class VeltrixKeyError(VeltrixError):
    """Raised when a map key is not found."""

    def __init__(self, key, filename=None, line=None):
        message = f"Key '{key}' was not found in the map."
        hint = "Make sure the key exists before accessing it."
        super().__init__(message, filename, line, hint)


class VeltrixNullError(VeltrixError):
    """Raised on null pointer access."""

    def __init__(self, message=None, filename=None, line=None, function_name=None,
                 stack_trace=None):
        if message is None:
            message = "Attempted to access a property or method on a Null value."
        hint = "Check if the value is Null before accessing its properties."
        super().__init__(message, filename, line, hint, function_name, stack_trace)


class VeltrixAttributeError(VeltrixError):
    """Raised when accessing an undefined attribute on an object."""

    def __init__(self, obj_name, attr_name, filename=None, line=None):
        message = f"'{obj_name}' does not have attribute '{attr_name}'."
        hint = "Check that the property or method exists on this object."
        super().__init__(message, filename, line, hint)


# ─── Internal Signals ────────────────────────────────────────────────────────

class ReturnSignal(Exception):
    """Internal signal used to propagate return values from functions."""

    def __init__(self, value):
        self.value = value
        super().__init__()
