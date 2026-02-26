"""
Veltrix Runtime Objects — Phase 2
====================================
Runtime value types for the Veltrix VM: classes, instances, closures,
null sentinel, built-in functions, and type utilities.
"""

import math
from veltrix.errors import (
    VeltrixNameError, VeltrixConstantError, VeltrixNullError,
    VeltrixAttributeError, VeltrixTypeError,
)
from veltrix.styling import TerminalRenderer


# ─── Null Sentinel ────────────────────────────────────────────────────────────

class _VeltrixNull:
    """Singleton null value."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "Null"

    def __str__(self):
        return "Null"

    def __bool__(self):
        return False

    def __eq__(self, other):
        return isinstance(other, _VeltrixNull)

    def __hash__(self):
        return hash(None)


VeltrixNull = _VeltrixNull()


# ─── Runtime Objects ──────────────────────────────────────────────────────────

class VeltrixObject:
    """Base class for all Veltrix runtime objects."""
    pass


class VeltrixClosure(VeltrixObject):
    def __init__(self, code):  # type: ignore (circular import)
        self.code = code
        self.name = code.name

    def __repr__(self):
        return f"<fn {self.name}>"


class VeltrixBoundMethod(VeltrixObject):
    def __init__(self, instance: 'VeltrixInstance', method: 'VeltrixClosure'):
        self.instance = instance
        self.method = method
        self.name = method.name

    def __repr__(self):
        return f"<bound method {self.instance.klass.name}.{self.name}>"

    def __call__(self, *args):
        # This method will be called by the VM when the bound method is invoked.
        # It needs to prepend 'self' (the instance) to the arguments.
        # The actual execution logic will be in the VM.
        raise NotImplementedError("VeltrixBoundMethod is not directly callable in Python.")


class VeltrixClass(VeltrixObject):
    """Runtime representation of a Veltrix class."""

    def __init__(self, name, methods=None):
        self.name = name
        self.methods = methods or {}  # name → VeltrixClosure

    def __repr__(self):
        return f"<class {self.name}>"


class VeltrixInstance(VeltrixObject):
    def __init__(self, klass: VeltrixClass):
        self.klass = klass
        self.properties = {}

    def get(self, name: str):
        if name in self.properties:
            return self.properties[name]
        if name in self.klass.methods:
            return VeltrixBoundMethod(self, self.klass.methods[name])
        raise VeltrixAttributeError(self.klass.name, name)

    def set(self, name: str, value):
        self.properties[name] = value

    def __repr__(self):
        return f"<{self.klass.name} instance>"


class VeltrixRange:
    """A range object representing start..end."""

    def __init__(self, start, end):
        self.start = int(start)
        self.end = int(end)

    def __iter__(self):
        return iter(range(self.start, self.end + 1))

    def __contains__(self, value):
        return self.start <= value <= self.end

    def __len__(self):
        return max(0, self.end - self.start + 1)

    def __getitem__(self, index):
        if index < 0 or index >= len(self):
            raise IndexError("Range index out of bounds")
        return self.start + index

    def __repr__(self):
        return f"{self.start}..{self.end}"

    def to_list(self):
        return list(range(self.start, self.end + 1))


class VeltrixStyledText(VeltrixObject):
    """A string with associated style properties."""

    def __init__(self, text: str, properties: dict):
        self.text = str(text)
        self.properties = properties  # e.g., {'color': '#ff0000', 'bold': True}

    def __repr__(self):
        # Unstyled raw repr
        return repr(self.text)

    def __str__(self):
        # Render the styled text for the terminal
        return TerminalRenderer.render(self.text, self.properties)

    def __eq__(self, other):
        if not isinstance(other, VeltrixStyledText):
            return False
        return self.text == other.text and self.properties == other.properties

    def __len__(self):
        return len(self.text)


class NativeFunction:
    """A built-in function callable by the VM."""

    def __init__(self, name, func, arity=-1):
        self.name = name
        self.func = func
        self.arity = arity  # -1 = variadic

    def __repr__(self):
        return f"<native fn {self.name}>"

    def __call__(self, *args):
        return self.func(*args)


# ─── Truthiness ───────────────────────────────────────────────────────────────

def is_truthy(value) -> bool:
    """Veltrix truthiness rules."""
    if value is VeltrixNull:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return len(value) > 0
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        return len(value) > 0
    if isinstance(value, VeltrixStyledText):
        return len(value.text) > 0
    return True


# ─── Type Checking ────────────────────────────────────────────────────────────

TYPE_MAP = {
    "Integer": (int,),
    "Number": (int, float),
    "Float": (float,),
    "String": (str,),
    "Boolean": (bool,),
    "List": (list,),
    "Map": (dict,),
    "Function": (VeltrixClosure, NativeFunction),
    "Null": (_VeltrixNull,),
}


def type_check(value, expected_type: str, filename=None, line=None):
    """Validate a value against a Veltrix type annotation. Raises on mismatch."""
    if expected_type is None:
        return  # no annotation = no check
    if expected_type not in TYPE_MAP:
        return  # unknown type = skip check (gradual typing)
    expected = TYPE_MAP[expected_type]
    if value is VeltrixNull:
        return  # Null is allowed everywhere (null safety checked separately)
    if not isinstance(value, expected):
        actual = type_of(value)
        raise VeltrixTypeError(
            f"Expected type '{expected_type}', got '{actual}'.",
            filename, line
        )


def type_of(value) -> str:
    """Return the Veltrix type name of a value."""
    if value is VeltrixNull:
        return "Null"
    if isinstance(value, bool):
        return "Boolean"
    if isinstance(value, int):
        return "Integer"
    if isinstance(value, float):
        return "Float"
    if isinstance(value, str):
        return "String"
    if isinstance(value, list):
        return "List"
    if isinstance(value, dict):
        return "Map"
    if isinstance(value, VeltrixClosure):
        return "Function"
    if isinstance(value, NativeFunction):
        return "Function"
    if isinstance(value, VeltrixClass):
        return "Class"
    if isinstance(value, VeltrixInstance):
        return value.klass.name
    if isinstance(value, VeltrixRange):
        return "Range"
    if callable(value):
        return "Function"
    if isinstance(value, VeltrixStyledText):
        return "StyledText"
    return "Unknown"


# ─── Value Formatting ────────────────────────────────────────────────────────

def format_value(value) -> str:
    """Format a Veltrix value for display."""
    if value is VeltrixNull:
        return "Null"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float):
        if value == int(value):
            return str(int(value))
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        items = ", ".join(format_value(v) for v in value)
        return f"[{items}]"
    if isinstance(value, dict):
        items = ", ".join(f"{k}: {format_value(v)}" for k, v in value.items())
        return f"{{{items}}}"
    if isinstance(value, VeltrixRange):
        return str(value)
    if isinstance(value, VeltrixStyledText):
        return str(value)
    return str(value)


# ─── Built-in Registry ───────────────────────────────────────────────────────

def _to_number(value):
    """Convert a value to a number."""
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return 0
    return 0


def create_builtins() -> dict:
    """Create the dictionary of all built-in globals for the VM."""
    builtins = {}

    # Math object
    math_obj = {
        "pi": math.pi,
        "e": math.e,
        "sqrt": NativeFunction("Math.sqrt", lambda x: math.sqrt(x), 1),
        "power": NativeFunction("Math.power", lambda x, y: math.pow(x, y), 2),
        "abs": NativeFunction("Math.abs", lambda x: abs(x), 1),
        "round": NativeFunction("Math.round", lambda x: round(x), 1),
        "floor": NativeFunction("Math.floor", lambda x: math.floor(x), 1),
        "ceil": NativeFunction("Math.ceil", lambda x: math.ceil(x), 1),
        "sin": NativeFunction("Math.sin", lambda x: math.sin(x), 1),
        "cos": NativeFunction("Math.cos", lambda x: math.cos(x), 1),
        "tan": NativeFunction("Math.tan", lambda x: math.tan(x), 1),
        "log": NativeFunction("Math.log", lambda x: math.log(x), 1),
        "max": NativeFunction("Math.max", lambda x, y: max(x, y), 2),
        "min": NativeFunction("Math.min", lambda x, y: min(x, y), 2),
    }
    builtins["Math"] = math_obj

    # Built-in utility functions
    builtins["length"] = NativeFunction("length", lambda x: len(x), 1)
    builtins["toString"] = NativeFunction("toString", lambda x: str(x), 1)
    builtins["toNumber"] = NativeFunction("toNumber", lambda x: _to_number(x), 1)
    builtins["typeOf"] = NativeFunction("typeOf", lambda x: type_of(x), 1)

    return builtins


# ─── Legacy Environment (kept for REPL compatibility) ────────────────────────

class Environment:
    """
    A scoped symbol table. Each scope has an optional parent,
    enabling lexical scoping for functions and blocks.
    """

    def __init__(self, parent=None):
        self.parent: Environment | None = parent
        self.variables: dict = {}
        self.constants: set = set()

    def define(self, name: str, value, is_constant: bool = False):
        self.variables[name] = value
        if is_constant:
            self.constants.add(name)

    def get(self, name: str, filename: str = None, line: int = None):
        if name in self.variables:
            return self.variables[name]
        if self.parent is not None:
            return self.parent.get(name, filename, line)
        raise VeltrixNameError(name, filename, line)

    def set(self, name: str, value, filename: str = None, line: int = None):
        if name in self.variables:
            if name in self.constants:
                raise VeltrixConstantError(name, filename, line)
            self.variables[name] = value
            return
        if self.parent is not None:
            self.parent.set(name, value, filename, line)
            return
        raise VeltrixNameError(name, filename, line)

    def has(self, name: str) -> bool:
        if name in self.variables:
            return True
        if self.parent is not None:
            return self.parent.has(name)
        return False

    def is_constant(self, name: str) -> bool:
        if name in self.constants:
            return True
        if self.parent is not None:
            return self.parent.is_constant(name)
        return False
