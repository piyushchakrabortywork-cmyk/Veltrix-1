# Veltrix Programming Language

![Veltrix Badge](https://img.shields.io/badge/Veltrix-v2.0-blueviolet)

LOGO_ART = r"""
 ██╗   ██╗███████╗██╗  ████████╗██████╗ ██╗██╗  ██╗
 ██║   ██║██╔════╝██║  ╚══██╔══╝██╔══██╗██║╚██╗██╔╝
 ██║   ██║█████╗  ██║     ██║   ██████╔╝██║ ╚███╔╝
 ╚██╗ ██╔╝██╔══╝  ██║     ██║   ██╔══██╗██║ ██╔██╗
  ╚████╔╝ ███████╗███████╗██║   ██║  ██║██║██╔╝ ██╗
   ╚═══╝  ╚══════╝╚══════╝╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝
"""

LOGO_SMALL = r"""
 ╦  ╦╔═╗╦  ╔╦╗╦═╗╦═╗ ╦
 ╚╗╔╝║╣ ║   ║ ╠╦╝║╔╩╦╝
  ╚╝ ╚═╝╩═╝╩ ╩╚═╩╩ ╚
"""

## 1. Introduction

**Veltrix** is a modern, beautifully designed, beginner-friendly programming language. Built from scratch with its own bytecode compiler and stack-based Virtual Machine (VM), Veltrix focuses on readability, strict grammar, and an "English-like" syntax without heavy symbols like mandatory semicolons for every line or curly braces for blocks.

**Key Features:**
- **Clean Syntax:** No curly braces needed for structures—blocks close with `End`.
- **Powerful VM:** Compiles to custom `.vlb` bytecode for fast execution.
- **Rich Built-ins:** Classes, maps, lists, try/catch, and robust string utilities.
- **GUI Engine:** Built-in declarative GUI and layout engine with styling and event handling.
- **Null Safety:** Native `Null` type handling with strict type-checking modes.

Whether you're building simple scripts, complex logic, or desktop GUIs, Veltrix provides the tools you need in an intuitive, expressive package.

---

## 2. Installation / Setup

Veltrix is implemented in Python and requires no external heavy dependencies (it uses `tkinter` for GUI, which comes standard with Python).

### Prerequisites
- Python 3.10+ installed on your system.

### Installation
Clone or download the Veltrix project folder. That's it!

### Running Veltrix
To run Veltrix code, use the main CLI entry point:
```bash
# Run a source file
python main.py run your_program.vlx

# Run a pre-compiled bytecode file
python main.py run your_program.vlb

# Open the Interactive REPL
python main.py repl
```

**Other CLI Commands:**
- `python main.py compile <file.vlx>`: Compile to `.vlb` bytecode without running.
- `python main.py dev <file.vlx>`: Compile and run with bytecode disassembly output.
- `python main.py disassemble <file>`: Print readable opcodes for debugging.

---

## 3. Basic Usage

Veltrix scripts use the `.vlx` file extension. 
Here is a complete "Hello World" program:

```veltrix
Write "Hello, World!"
Write "Welcome to Veltrix!"

Let name = "Developer"
Write "Hello, " + name + "!"
```
Save it to `hello.vlx` and run `python main.py run hello.vlx`.

---

## 4. All Syntax & Keywords

### **Variables & Constants**
- **`Let`**: Defines a mutable variable.
  ```veltrix
  Let age = 22
  ```
- **`Constant`**: Defines an immutable constant. Reassigning it will throw an error.
  ```veltrix
  Constant PI = 3.1415
  ```

### **I/O**
- **`Write`**: Prints output to the console.
  ```veltrix
  Write "Result: " + (5 + 5)
  ```
- **`Ask`**: (Future implementation standard) Used for taking input from the user.

### **Control Flow**
- **`If` / `Else` / `End`**: Conditional branching.
  ```veltrix
  If score >= 90
      Write "Grade A"
  Else
      Write "Try again"
  End
  ```
- **`Match` / `Otherwise` / `End`**: Pattern matching (switch-case alternative).
  ```veltrix
  Match day
      "Monday"
          Write "Start of week"
      Otherwise
          Write "Regular day"
  End
  ```

### **Loops**
- **`For` ... `from` ... `to` ... `End`**: Iterate over a numeric range. You can use the `step` keyword for custom increments.
  ```veltrix
  For i from 1 to 5
      Write i
  End
  ```
- **`While` ... `End`**: Loops while a condition evaluates to `True`.
  ```veltrix
  While count > 0
      count = count - 1
  End
  ```

### **Functions**
- **`Function` / `Return` / `End`**: Declare a reusable block of code.
  ```veltrix
  Function Square(n)
      Return n * n
  End
  ```

### **Data Structures**
- **Lists**: Ordered collections.
  ```veltrix
  Let colors = ["red", "green"]
  Add "blue" to colors
  Remove "red" from colors
  ```
- **Maps**: Key-value dictionaries.
  ```veltrix
  Let car = { brand: "Tesla", year: 2024 }
  Write car.brand
  ```

### **Error Handling**
- **`Try` / `Catch` / `End`**: Catch runtime exceptions gracefully.
  ```veltrix
  Try
      Let bad = 1 / 0
  Catch
      Write "Caught division by zero!"
  End
  ```

### **Classes & Object-Oriented Programming**
- **`Class` / `Init` / `Self` / `End`**: Create object blueprints.
  ```veltrix
  Class Animal
      Function Init(name)
          Self.name = name
      End
  End
  ```

### **Logical Operators & Primitives**
- **Logic**: `And`, `Or`, `Not`
- **Equality/Relational**: `==`, `!=`, `<`, `>`, `<=`, `>=`
- **Math**: `+`, `-`, `*`, `/`, `%`
- **Range Operator**: `..` (e.g., `1..5`)
- **Booleans**: `True`, `False`
- **Null Type**: `Null`

---

## 5. Built-in Modules / Libraries

Veltrix provides several built-in functions natively available to the VM.

### **Global Utilities**
- `length(item)`: Get the number of elements in a string, list, or map.
- `toString(value)`: Convert any type to a string.
- `toNumber(value)`: Convert a string to a number.
- `typeOf(value)`: Returns the Veltrix type of the given variable as a string (e.g., "Integer", "String").

### **Math Module**
A standard math library available via the `Math` object:
- Properties: `Math.pi`, `Math.e`
- Functions: `Math.sqrt(x)`, `Math.power(base, exp)`, `Math.abs(x)`, `Math.round(x)`, `Math.floor(x)`, `Math.ceil(x)`, `Math.sin(x)`, `Math.cos(x)`, `Math.tan(x)`, `Math.log(x)`, `Math.max(x, y)`, `Math.min(x, y)`

### **GUI & Layout Engine (Veltrix UI)**
Veltrix Phase 2 features a robust GUI engine to build desktop applications declaratively.
- **Components**: `window`, `button`, `input`, `checkbox`, `dropdown`
- **Layouts**: `vstack` (vertical stack), `hstack` (horizontal stack), `grid`
- **Shapes**: `rectangle`, `circle`, `line`
- **Actions**: `show window`
- **Events**: `onClick`, `onHover`, `onChange`, `onKeyPress`

---

## 6. Examples

### Example 1: Basic Calculator
```veltrix
Function Calculate(a, b, op)
    Match op
        "+"
            Return a + b
        "*"
            Return a * b
        Otherwise
            Return Null
    End
End

Write "Result: " + Calculate(10, 5, "*")
```

### Example 2: Interactive GUI Application
```veltrix
window "My App" {
    width: 600,
    height: 400,
    bg: "#f0f0f0"
};

let counter = 0;

vstack {
    x: 200,
    y: 100,
    button "Click Me!" {
        color: "#4CAF50",
        onClick {
            counter = counter + 1;
            Write "Clicked " + counter + " times!";
        }
    };
};

show window;
```

---

## 7. Advanced Features

* **String Interpolation:** You can embed expressions directly into strings using `{}` blocks. 
  ```veltrix
  Let name = "Alice"
  Write "Hello, {name}!" 
  ```
* **Rich Styling Engine:** Veltrix includes a styling framework utilizing styling keywords: `bold`, `italic`, `underline`, `strike`, `color`, `bg`, `opacity`, `gradient`. 
* **Range Operator (`..`)**: Quickly define lists/ranges using the double-dot operator instead of manually writing out bounds.

---

## 8. Tips / Best Practices

- **Capitalization:** Core structured keywords block markers (`If`, `For`, `While`, `Function`, `Class`, `End`, `Try`, `Catch`) should be capitalized. 
- **Variable scoping:** Use `Let` for standard variables and always prefer `Constant` for values that should not mutate (like configuration, Math Pi representations, or static IDs) to let the VM safely optimise execution.
- **Indentation:** While Veltrix doesn't strictly enforce indent blocks like Python (it relies on `End` terminology), keeping code neatly indented is a massive readability boost.
- **Use `Match` over deep `If/Else`:** Long chains of if-else statements evaluating strings/integers should be replaced by a single `Match` block for cleaner and more performant VM execution.

---

## 9. Changelog / Version Info

**Current Release: Veltrix v2.0 (Phase 2)**

*   **v2.0 (Latest):** 
    *   Added stack-based Virtual Machine and Bytecode compiler.
    *   Introduced full object-oriented programming with `Class` and `Init`.
    *   Implemented full GUI subsystem, Shape components, and event listeners.
    *   Implemented `Try`/`Catch` error boundaries.
    *   Added `Math` built-ins and type-safety mechanisms.
*   **v1.0 (Legacy):**
    *   Initial Tree-walk Interpreter.
    *   Basic Math, Looping, and Control flows implemented.
