"""
Veltrix AST Node Definitions — Phase 2
========================================
Dataclass-based AST nodes representing every language construct.
Each node stores a `line` number for error reporting.
Includes new nodes for classes, arrow functions, types, null safety,
string interpolation, ranges, and inline conditions.
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple


# ─── Base ─────────────────────────────────────────────────────────────────────

@dataclass
class ASTNode:
    """Base class for all AST nodes."""
    line: int = 0
    has_terminator: bool = False


# ─── Literals ─────────────────────────────────────────────────────────────────

@dataclass
class NumberLiteral(ASTNode):
    value: float = 0

@dataclass
class ColorLiteral(ASTNode):
    value: str = ""

@dataclass
class StringLiteral(ASTNode):
    value: str = ""

@dataclass
class BoolLiteral(ASTNode):
    value: bool = False

@dataclass
class NullLiteral(ASTNode):
    """The Null keyword."""
    pass

@dataclass
class ListLiteral(ASTNode):
    elements: List[ASTNode] = field(default_factory=list)

@dataclass
class MapLiteral(ASTNode):
    pairs: List[tuple] = field(default_factory=list)  # list of (key_str, value_node)

@dataclass
class StringInterpolation(ASTNode):
    """A string with embedded expressions: "Hello {name}, you are {age}"."""
    parts: List[ASTNode] = field(default_factory=list)  # alternating StringLiteral / expr


# ─── Identifiers & Access ────────────────────────────────────────────────────

@dataclass
class Identifier(ASTNode):
    name: str = ""

@dataclass
class ListAccess(ASTNode):
    obj: ASTNode = None
    index: ASTNode = None

@dataclass
class MapAccess(ASTNode):
    obj: ASTNode = None
    key: str = ""

@dataclass
class SelfAccess(ASTNode):
    """Self.property — read instance property."""
    attribute: str = ""

@dataclass
class SelfAssignment(ASTNode):
    """Self.property = value — write instance property."""
    attribute: str = ""
    value: ASTNode = None


# ─── Operators ────────────────────────────────────────────────────────────────

@dataclass
class BinaryOp(ASTNode):
    left: ASTNode = None
    op: str = ""
    right: ASTNode = None

@dataclass
class UnaryOp(ASTNode):
    op: str = ""
    operand: ASTNode = None


# ─── Declarations & Assignment ────────────────────────────────────────────────

@dataclass
class LetDeclaration(ASTNode):
    name: str = ""
    value: ASTNode = None
    type_annotation: Optional[str] = None  # e.g. "Integer", "String"

@dataclass
class ConstantDeclaration(ASTNode):
    name: str = ""
    value: ASTNode = None

@dataclass
class Assignment(ASTNode):
    name: str = ""
    value: ASTNode = None

@dataclass
class ListAssignment(ASTNode):
    obj: ASTNode = None
    index: ASTNode = None
    value: ASTNode = None

@dataclass
class MapAssignment(ASTNode):
    obj: ASTNode = None
    key: str = ""
    value: ASTNode = None

# ─── Blocks ───────────────────────────────────────────────────────────────────

@dataclass
class Property(ASTNode):
    """A key-value property inside a block: name: value,"""
    name: str = ""
    value: ASTNode = None

@dataclass
class PropertyBlock(ASTNode):
    """window "App" { width: 800, }"""
    block_type: str = ""      # e.g., "window"
    name: ASTNode = None      # e.g., StringLiteral("App")
    properties: List[Property] = field(default_factory=list)

@dataclass
class LayoutBlock(ASTNode):
    """vstack { spacing: 10, button "Click"; }"""
    layout_type: str = ""     # "vstack", "hstack", "grid"
    properties: List[Property] = field(default_factory=list)
    children: List[ASTNode] = field(default_factory=list)

@dataclass
class ComponentBlock(ASTNode):
    """button "Click Me" { width: 150, onClick { ... } }"""
    component_type: str = ""  # "button", "input", "checkbox", "dropdown"
    name: ASTNode = None      # e.g., StringLiteral("Click Me")
    properties: List[Property] = field(default_factory=list)
    children: List[ASTNode] = field(default_factory=list)

@dataclass
class ShowWindowStmt(ASTNode):
    """show window;"""
    pass

# ─── Styling ──────────────────────────────────────────────────────────────────

@dataclass
class StyleProperty(ASTNode):
    """color red, or bg #111111"""
    name: str = ""
    value: ASTNode = None

@dataclass
class GradientProperty(ASTNode):
    """gradient red -> blue"""
    start_color: ASTNode = None
    end_color: ASTNode = None

@dataclass
class StyleApplication(ASTNode):
    """bold "Text"; or color red "Text";"""
    properties: List[StyleProperty] = field(default_factory=list)
    gradient: Optional[GradientProperty] = None
    target: ASTNode = None 
    style_name: str = ""

@dataclass
class StyleBlock(ASTNode):
    """style { color: red, bg: blue } "Text";"""
    properties: List[Property] = field(default_factory=list)
    gradient_property: Optional[GradientProperty] = None # Or gradient handled differently? We can just put it in properties or gradient. Let's just track properties for now and validate at runtime.
    target: ASTNode = None



# ─── I/O ──────────────────────────────────────────────────────────────────────

@dataclass
class WriteStatement(ASTNode):
    expression: ASTNode = None

@dataclass
class AskStatement(ASTNode):
    prompt: ASTNode = None
    variable: str = ""


# ─── Control Flow ─────────────────────────────────────────────────────────────

@dataclass
class IfStatement(ASTNode):
    condition: ASTNode = None
    body: List[ASTNode] = field(default_factory=list)
    else_body: List[ASTNode] = field(default_factory=list)

@dataclass
class ForLoop(ASTNode):
    variable: str = ""
    start: ASTNode = None
    end: ASTNode = None
    step: Optional[ASTNode] = None
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class ForEachLoop(ASTNode):
    """For x in collection / For x in start..end."""
    variable: str = ""
    iterable: ASTNode = None
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class WhileLoop(ASTNode):
    condition: ASTNode = None
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class InlineCondition(ASTNode):
    """value if condition else other_value."""
    true_value: ASTNode = None
    condition: ASTNode = None
    false_value: ASTNode = None


# ─── Functions ────────────────────────────────────────────────────────────────

@dataclass
class TypedParam:
    """A function parameter with an optional type annotation."""
    name: str = ""
    type_annotation: Optional[str] = None

@dataclass
class FunctionDef(ASTNode):
    name: str = ""
    params: List = field(default_factory=list)  # list of str or TypedParam
    body: List[ASTNode] = field(default_factory=list)
    return_type: Optional[str] = None  # e.g. "Integer"

@dataclass
class ArrowFunction(ASTNode):
    """(params) => expression."""
    params: List = field(default_factory=list)  # list of str
    body: ASTNode = None  # single expression

@dataclass
class FunctionCall(ASTNode):
    name: str = ""
    args: List[ASTNode] = field(default_factory=list)
    obj: Optional[ASTNode] = None  # for method calls like Math.sqrt(x)

@dataclass
class ReturnStatement(ASTNode):
    value: Optional[ASTNode] = None


# ─── Classes ──────────────────────────────────────────────────────────────────

@dataclass
class ClassDef(ASTNode):
    """Class Name ... End — defines a class."""
    name: str = ""
    methods: List[FunctionDef] = field(default_factory=list)

@dataclass
class MethodCall(ASTNode):
    """obj.method(args) — method invocation on an instance or class."""
    obj: ASTNode = None
    method_name: str = ""
    args: List[ASTNode] = field(default_factory=list)


# ─── List Operations ─────────────────────────────────────────────────────────

@dataclass
class AddToList(ASTNode):
    value: ASTNode = None
    list_name: str = ""

@dataclass
class RemoveFromList(ASTNode):
    value: ASTNode = None
    list_name: str = ""


# ─── Match ────────────────────────────────────────────────────────────────────

@dataclass
class MatchRange(ASTNode):
    """A range case in a match statement: 1 to 10."""
    start: ASTNode = None
    end: ASTNode = None

@dataclass
class MatchStatement(ASTNode):
    subject: ASTNode = None
    cases: List[tuple] = field(default_factory=list)  # list of (value_node_or_MatchRange_or_None, body_list)


# ─── Error Handling ──────────────────────────────────────────────────────────

@dataclass
class TryCatch(ASTNode):
    try_body: List[ASTNode] = field(default_factory=list)
    catch_body: List[ASTNode] = field(default_factory=list)


# ─── Null Safety ─────────────────────────────────────────────────────────────

@dataclass
class IsNullCheck(ASTNode):
    """expr is Null."""
    expression: ASTNode = None

@dataclass
class IsNotNullCheck(ASTNode):
    """expr is not Null."""
    expression: ASTNode = None


# ─── Range ────────────────────────────────────────────────────────────────────

@dataclass
class RangeExpression(ASTNode):
    """start..end — creates a range object."""
    start: ASTNode = None
    end: ASTNode = None


# ─── Modules ─────────────────────────────────────────────────────────────────

@dataclass
class ImportStatement(ASTNode):
    filepath: str = ""


# ─── Program ─────────────────────────────────────────────────────────────────

@dataclass
class Program(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)
