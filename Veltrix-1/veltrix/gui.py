"""
Veltrix GUI Subsystem
=======================
Handles the SceneGraph, RenderEngine, and WindowManager for
hardware-accelerated (or Tkinter) shape drawing.
"""

import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from veltrix.errors import VeltrixError

# ─── Event Dispatcher ────────────────────────────────────────────────────────

class EventDispatcher:
    _vm_callback = None
    
    @classmethod
    def set_vm_callback(cls, callback):
        cls._vm_callback = callback
        
    @classmethod
    def fire_event(cls, closure, *args):
        if cls._vm_callback and closure:
            cls._vm_callback(closure, *args)

# ─── Scene Graph & Nodes ──────────────────────────────────────────────────────

@dataclass
class RenderNode:
    """Base class for anything that can be rendered."""
    z_index: int = 0
    
    def get_width(self) -> int: return 0
    def get_height(self) -> int: return 0
    def add_node(self, node: 'RenderNode'): pass
    
    def render(self, engine: 'RenderEngine', offset_x: int = 0, offset_y: int = 0):
        pass

@dataclass
class ShapeNode(RenderNode):
    type_name: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)

    def get_width(self) -> int:
        return self.properties.get("width", self.properties.get("radius", 50) * 2)

    def get_height(self) -> int:
        return self.properties.get("height", self.properties.get("radius", 50) * 2)

    def render(self, engine: 'RenderEngine', offset_x: int = 0, offset_y: int = 0):
        props = self.properties.copy()
        props["x"] = offset_x + props.get("x", 0)
        props["y"] = offset_y + props.get("y", 0)
        if self.type_name == "rectangle":
            engine.draw_rect(props)
        elif self.type_name == "circle":
            engine.draw_circle(props)
        elif self.type_name == "line":
            engine.draw_line(props)

@dataclass
class ComponentNode(RenderNode):
    component_type: str = ""
    name: Any = None
    properties: Dict[str, Any] = field(default_factory=dict)
    children: List[RenderNode] = field(default_factory=list)
    
    def add_node(self, node: RenderNode):
        self.children.append(node)
        
    def get_width(self) -> int:
        return self.properties.get("width", 100)
    
    def get_height(self) -> int:
        return self.properties.get("height", 30)
        
    def render(self, engine: 'RenderEngine', offset_x: int = 0, offset_y: int = 0):
        props = self.properties.copy()
        props["x"] = offset_x + props.get("x", 0)
        props["y"] = offset_y + props.get("y", 0)
        props["width"] = self.get_width()
        props["height"] = self.get_height()
        
        if self.component_type == "button":
            engine.draw_button(self.name, props)
        elif self.component_type == "input":
            engine.draw_input(self.name, props)
        elif self.component_type == "checkbox":
            engine.draw_checkbox(self.name, props)
        elif self.component_type == "dropdown":
            engine.draw_dropdown(self.name, props)
            
        for child in self.children:
            child.render(engine, props["x"], props["y"])

@dataclass
class LayoutNode(RenderNode):
    layout_type: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    children: List[RenderNode] = field(default_factory=list)

    def add_node(self, node: RenderNode):
        self.children.append(node)
        
    def get_width(self) -> int:
        if self.layout_type == "vstack":
            return max((c.get_width() for c in self.children), default=0)
        elif self.layout_type == "hstack":
            spacing = self.properties.get("spacing", 10)
            return sum((c.get_width() for c in self.children), 0) + spacing * max(0, len(self.children) - 1)
        return self.properties.get("width", 0)

    def get_height(self) -> int:
        if self.layout_type == "hstack":
            return max((c.get_height() for c in self.children), default=0)
        elif self.layout_type == "vstack":
            spacing = self.properties.get("spacing", 10)
            return sum((c.get_height() for c in self.children), 0) + spacing * max(0, len(self.children) - 1)
        return self.properties.get("height", 0)
        
    def render(self, engine: 'RenderEngine', offset_x: int = 0, offset_y: int = 0):
        start_x = offset_x + self.properties.get("x", 0)
        start_y = offset_y + self.properties.get("y", 0)
        spacing = self.properties.get("spacing", 10)
        align = self.properties.get("align", "start")
        
        current_x, current_y = start_x, start_y
        
        if self.layout_type == "vstack":
            for child in self.children:
                cx = current_x
                if align == "center":
                    cx = current_x + (self.get_width() - child.get_width()) // 2
                elif align == "end":
                    cx = current_x + (self.get_width() - child.get_width())
                    
                child.render(engine, cx, current_y)
                current_y += child.get_height() + spacing
                
        elif self.layout_type == "hstack":
            for child in self.children:
                cy = current_y
                if align == "center":
                    cy = current_y + (self.get_height() - child.get_height()) // 2
                elif align == "end":
                    cy = current_y + (self.get_height() - child.get_height())
                
                child.render(engine, current_x, cy)
                current_x += child.get_width() + spacing
        
        elif self.layout_type == "grid":
            cols = self.properties.get("columns", 2)
            col_widths = [0] * cols
            row_heights = []
            
            for i, child in enumerate(self.children):
                c = i % cols
                r = i // cols
                if r >= len(row_heights):
                    row_heights.append(0)
                col_widths[c] = max(col_widths[c], child.get_width())
                row_heights[r] = max(row_heights[r], child.get_height())
                
            for i, child in enumerate(self.children):
                c = i % cols
                r = i // cols
                cx = start_x + sum(col_widths[:c]) + c * spacing
                cy = start_y + sum(row_heights[:r]) + r * spacing
                child.render(engine, cx, cy)

class SceneGraph:
    """Maintains a collection of render nodes to draw."""
    def __init__(self):
        self.nodes: List[RenderNode] = []

    def add_node(self, node: RenderNode):
        self.nodes.append(node)
        self.nodes.sort(key=lambda n: n.z_index)

    def render_all(self, engine: 'RenderEngine'):
        for node in self.nodes:
            node.render(engine, 0, 0)


# ─── Render Engine ────────────────────────────────────────────────────────────

class RenderEngine:
    """Abstract rendering engine interface."""
    def init_window(self, title: str, width: int, height: int, bg_color: str, resizable: bool):
        pass
        
    def draw_rect(self, props: Dict[str, Any]):
        pass
        
    def draw_circle(self, props: Dict[str, Any]):
        pass
        
    def draw_line(self, props: Dict[str, Any]): pass
    def draw_button(self, name: Any, props: Dict[str, Any]): pass
    def draw_input(self, name: Any, props: Dict[str, Any]): pass
    def draw_checkbox(self, name: Any, props: Dict[str, Any]): pass
    def draw_dropdown(self, name: Any, props: Dict[str, Any]): pass
        
    def start_loop(self, scene_graph: SceneGraph):
        pass

class TkinterRenderEngine(RenderEngine):
    """Tkinter-based implementation of RenderEngine."""
    def __init__(self):
        self.root = None
        self.canvas = None
        self.width = 800
        self.height = 600
        self.components = {} # Store built tkinter widgets by id to avoid recreation

    def init_window(self, title: str, width: int, height: int, bg_color: str, resizable: bool):
        self.width = width
        self.height = height
        
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry(f"{width}x{height}")
        self.root.resizable(resizable, resizable)
        self.root.configure(bg=bg_color)
        
        self.canvas = tk.Canvas(self.root, width=width, height=height, bg=bg_color, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

    def _parse_color(self, color_val: Any) -> str:
        # Veltrix colors might be strings like "red" or hex "#111111"
        if not color_val:
            return "black"
        return str(color_val)

    def draw_rect(self, props: Dict[str, Any]):
        x = props.get("x", 0)
        y = props.get("y", 0)
        w = props.get("width", 100)
        h = props.get("height", 100)
        color = self._parse_color(props.get("color", "black"))
        self.canvas.create_rectangle(x, y, x + w, y + h, fill=color, outline=color)

    def draw_circle(self, props: Dict[str, Any]):
        x = props.get("x", 0)
        y = props.get("y", 0)
        r = props.get("radius", 50)
        color = self._parse_color(props.get("color", "black"))
        self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, outline=color)

    def draw_line(self, props: Dict[str, Any]):
        x1 = props.get("x1", 0)
        y1 = props.get("y1", 0)
        x2 = props.get("x2", 100)
        y2 = props.get("y2", 100)
        color = self._parse_color(props.get("color", "black"))
        thickness = props.get("thickness", 1)
        self.canvas.create_line(x1, y1, x2, y2, fill=color, width=thickness)

    def draw_button(self, name: Any, props: Dict[str, Any]):
        cid = id(props)
        if cid not in self.components:
            btn = tk.Button(self.root, text=str(name) if name else "",
                            command=lambda: EventDispatcher.fire_event(props.get("onClick")))
            btn.config(bg=self._parse_color(props.get("color", "white")),
                       fg=self._parse_color(props.get("text_color", "black")))
            self.components[cid] = btn
        
        self.components[cid].place(x=props["x"], y=props["y"], width=props["width"], height=props["height"])
        
    def draw_input(self, name: Any, props: Dict[str, Any]):
        cid = id(props)
        if cid not in self.components:
            var = tk.StringVar(value=str(name) if name else "")
            
            def on_change(*args):
                EventDispatcher.fire_event(props.get("onChange"), var.get())
                
            var.trace_add("write", on_change)
            entry = tk.Entry(self.root, textvariable=var)
            self.components[cid] = (entry, var)
            
        self.components[cid][0].place(x=props["x"], y=props["y"], width=props["width"], height=props["height"])
        
    def draw_checkbox(self, name: Any, props: Dict[str, Any]):
        cid = id(props)
        if cid not in self.components:
            var = tk.BooleanVar(value=props.get("checked", False))
            
            def on_change():
                EventDispatcher.fire_event(props.get("onChange"), var.get())
                
            cb = tk.Checkbutton(self.root, text=str(name) if name else "", variable=var, command=on_change)
            cb.config(bg=self.root["bg"])
            self.components[cid] = (cb, var)
            
        self.components[cid][0].place(x=props["x"], y=props["y"], width=props["width"], height=props["height"])
        
    def draw_dropdown(self, name: Any, props: Dict[str, Any]):
        cid = id(props)
        if cid not in self.components:
            var = tk.StringVar(value=str(name) if name else "")
            options = props.get("options", [])
            cb = ttk.Combobox(self.root, textvariable=var, values=list(options))
            
            def on_change(event):
                EventDispatcher.fire_event(props.get("onChange"), var.get())
                
            cb.bind("<<ComboboxSelected>>", on_change)
            self.components[cid] = (cb, var)
            
        self.components[cid][0].place(x=props["x"], y=props["y"], width=props["width"], height=props["height"])

    def start_loop(self, scene_graph: SceneGraph):
        if not self.root:
            return
        
        def update_frame():
            self.canvas.delete("all")
            # We don't delete self.components, they are static and placed.
            scene_graph.render_all(self)
        
        update_frame()
        self.root.mainloop()


# ─── Shape Factory & Validation ───────────────────────────────────────────────

class ShapeFactory:
    """Validates properties and builds ShapeNodes."""
    @staticmethod
    def create_shape(shape_type: str, props: Dict[str, Any], filename: str, line: int) -> ShapeNode:
        # Generic validations
        for dim in ["width", "height", "radius", "thickness"]:
            if dim in props:
                val = props[dim]
                if not isinstance(val, (int, float)):
                    raise VeltrixError(f"'{dim}' must be a number.", filename, line)
                if val < 0:
                    raise VeltrixError(f"'{dim}' cannot be negative.", filename, line)
        
        z_index = props.get("z_index", 0)
        if not isinstance(z_index, int):
            try:
                z_index = int(z_index)
            except:
                z_index = 0

        return ShapeNode(z_index=z_index, type_name=shape_type, properties=props)


# ─── Window Manager ───────────────────────────────────────────────────────────

class _WindowManagerClass:
    """Singleton managing active windows and scenes."""
    def __init__(self):
        self.active_scene: Optional[SceneGraph] = None
        self.active_engine: Optional[RenderEngine] = None
        self.window_properties: Dict[str, Any] = {}
        self.window_title: str = "Veltrix App"
        self.node_stack: List[Any] = []

    def create_window(self, title: str, props: Dict[str, Any], filename: str, line: int):
        self.window_title = title
        self.window_properties = props
        self.active_scene = SceneGraph()
        self.node_stack = [self.active_scene]
        
        # Validation
        for dim in ["width", "height"]:
            if dim in props:
                val = props[dim]
                if not isinstance(val, (int, float)):
                    raise VeltrixError(f"Window '{dim}' must be a number.", filename, line)
                if val <= 0:
                    raise VeltrixError(f"Window '{dim}' must be greater than 0.", filename, line)

    def _add_to_stack(self, node: RenderNode, filename: str, line: int):
        if not self.node_stack:
            raise VeltrixError(f"Cannot add node without an active window.", filename, line)
        parent = self.node_stack[-1]
        parent.add_node(node)

    def add_shape(self, shape_type: str, props: Dict[str, Any], filename: str, line: int):
        node = ShapeFactory.create_shape(shape_type, props, filename, line)
        self._add_to_stack(node, filename, line)
        
    def setup_layout(self, layout_type: str, props: Dict[str, Any], filename: str, line: int):
        node = LayoutNode(layout_type=layout_type, properties=props)
        self._add_to_stack(node, filename, line)
        self.node_stack.append(node)
        
    def end_layout(self, filename: str, line: int):
        if len(self.node_stack) > 1:
            self.node_stack.pop()
            
    def setup_component(self, component_type: str, name: Any, props: Dict[str, Any], filename: str, line: int):
        node = ComponentNode(component_type=component_type, name=name, properties=props)
        self._add_to_stack(node, filename, line)
        self.node_stack.append(node)
        
    def end_component(self, filename: str, line: int):
        if len(self.node_stack) > 1:
            self.node_stack.pop()

    def show_window(self, filename: str, line: int):
        if self.active_scene is None:
            raise VeltrixError("Cannot show window: no window has been created.", filename, line)
            
        width = self.window_properties.get("width", 800)
        height = self.window_properties.get("height", 600)
        bg = self.window_properties.get("bg", "#ffffff")
        resizable = self.window_properties.get("resizable", True)
        
        self.active_engine = TkinterRenderEngine()
        self.active_engine.init_window(self.window_title, width, height, bg, resizable)
        
        # This blocks until window is closed
        self.active_engine.start_loop(self.active_scene)
        
        # Reset after close
        self.active_scene = None
        self.active_engine = None

WindowManager = _WindowManagerClass()
