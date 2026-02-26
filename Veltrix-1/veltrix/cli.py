"""
Veltrix CLI — Phase 2
=======================
Command-line interface for compiling and running .vlx/.vlb files,
interactive REPL, disassembler, and dev mode.
"""

import sys
import os
import pickle

# Fix Windows encoding — force UTF-8 output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from veltrix.lexer import Lexer
from veltrix.parser import Parser
from veltrix.compiler import Compiler
from veltrix.vm import VeltrixVM
from veltrix.bytecode import disassemble, CodeObject
from veltrix.errors import VeltrixError


BANNER = r"""
 ██╗   ██╗███████╗██╗     ████████╗██████╗ ██╗██╗  ██╗
 ██║   ██║██╔════╝██║     ╚══██╔══╝██╔══██╗██║╚██╗██╔╝
 ██║   ██║█████╗  ██║        ██║   ██████╔╝██║ ╚███╔╝
 ╚██╗ ██╔╝██╔══╝  ██║        ██║   ██╔══██╗██║ ██╔██╗
  ╚████╔╝ ███████╗███████╗   ██║   ██║  ██║██║██╔╝ ██╗
   ╚═══╝  ╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝

  Veltrix Programming Language v2.0
  Bytecode-compiled • Stack-based VM
"""


def print_banner():
    """Print the Veltrix ASCII logo and version info."""
    print(BANNER)


# ─── Compile + Run ────────────────────────────────────────────────────────────

def compile_source(source: str, filepath: str, legacy_mode: bool = False) -> CodeObject:
    """Lex → Parse → Compile a source string into a CodeObject."""
    lexer = Lexer(source, filepath)
    tokens = lexer.tokenize()
    parser = Parser(tokens, filepath, legacy_mode=legacy_mode)
    program = parser.parse()
    compiler = Compiler(filepath)
    code = compiler.compile(program)
    return code


def run_file(filepath: str, verbose: bool = False, legacy_mode: bool = False):
    """Read, compile, and execute a .vlx or .vlb file."""
    filepath = os.path.abspath(filepath)

    if not os.path.exists(filepath):
        print(f"\nVeltrix Error:\n  File '{filepath}' not found.\n")
        sys.exit(1)

    if filepath.endswith(".vlb"):
        # Load precompiled bytecode
        try:
            with open(filepath, "rb") as f:
                code = pickle.load(f)
        except Exception as e:
            print(f"\nVeltrix Error:\n  Could not load bytecode file: {e}\n")
            sys.exit(1)

        if verbose:
            print("  ─── Disassembly ───")
            print(disassemble(code))
            print("  ─── Execution ───\n")

        try:
            vm = VeltrixVM(filepath)
            vm.run(code)
        except VeltrixError as e:
            print(str(e))
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n\nExecution interrupted.")
            sys.exit(0)
        return

    if not filepath.endswith(".vlx"):
        print(f"\nVeltrix Error:\n  Expected a .vlx or .vlb file, got '{filepath}'.\n")
        sys.exit(1)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        print(f"\nVeltrix Error:\n  Could not read file: {e}\n")
        sys.exit(1)

    try:
        code = compile_source(source, filepath, legacy_mode=legacy_mode)

        if verbose:
            print("  ─── Disassembly ───")
            print(disassemble(code))
            print("  ─── Execution ───\n")

        vm = VeltrixVM(filepath)
        vm.run(code)
    except VeltrixError as e:
        print(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nExecution interrupted.")
        sys.exit(0)


# ─── Compile to file ─────────────────────────────────────────────────────────

def compile_file(filepath: str, legacy_mode: bool = False):
    """Compile a .vlx file to a .vlb bytecode file."""
    filepath = os.path.abspath(filepath)

    if not os.path.exists(filepath):
        print(f"\nVeltrix Error:\n  File '{filepath}' not found.\n")
        sys.exit(1)

    if not filepath.endswith(".vlx"):
        print(f"\nVeltrix Error:\n  Expected a .vlx file to compile.\n")
        sys.exit(1)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        print(f"\nVeltrix Error:\n  Could not read file: {e}\n")
        sys.exit(1)

    try:
        code = compile_source(source, filepath, legacy_mode=legacy_mode)
    except VeltrixError as e:
        print(str(e))
        sys.exit(1)

    output_path = filepath.replace(".vlx", ".vlb")
    try:
        with open(output_path, "wb") as f:
            pickle.dump(code, f)
    except Exception as e:
        print(f"\nVeltrix Error:\n  Could not write bytecode file: {e}\n")
        sys.exit(1)

    print(f"  ✓ Compiled: {os.path.basename(filepath)} → {os.path.basename(output_path)}")
    print(f"  Instructions: {len(code.instructions)}")
    print(f"  Constants: {len(code.constants)}")


# ─── Disassemble ──────────────────────────────────────────────────────────────

def disassemble_file(filepath: str, legacy_mode: bool = False):
    """Disassemble a .vlb or .vlx file and print readable opcodes."""
    filepath = os.path.abspath(filepath)

    if not os.path.exists(filepath):
        print(f"\nVeltrix Error:\n  File '{filepath}' not found.\n")
        sys.exit(1)

    if filepath.endswith(".vlb"):
        try:
            with open(filepath, "rb") as f:
                code = pickle.load(f)
        except Exception as e:
            print(f"\nVeltrix Error:\n  Could not load bytecode file: {e}\n")
            sys.exit(1)
    elif filepath.endswith(".vlx"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            code = compile_source(source, filepath, legacy_mode=legacy_mode)
        except VeltrixError as e:
            print(str(e))
            sys.exit(1)
    else:
        print(f"\nVeltrix Error:\n  Expected a .vlx or .vlb file.\n")
        sys.exit(1)

    print(disassemble(code))


# ─── REPL ─────────────────────────────────────────────────────────────────────

def run_repl():
    """Start an interactive REPL session using compile + VM."""
    print_banner()
    print("  Type 'exit' or 'quit' to leave the REPL.\n")

    # Shared VM state across REPL inputs
    vm = VeltrixVM("<repl>")

    while True:
        try:
            line = input("vlx> ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        line = line.strip()
        if not line:
            continue
        if line.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        # Accumulate multi-line input for blocks
        block_keywords = {"If", "For", "While", "Function", "Match", "Try", "Class"}
        first_word = line.split()[0] if line.split() else ""

        if first_word in block_keywords:
            lines = [line]
            end_count_needed = 1
            while end_count_needed > 0:
                try:
                    continuation = input("...  ")
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
                lines.append(continuation)
                stripped = continuation.strip()
                first = stripped.split()[0] if stripped.split() else ""
                if first in block_keywords:
                    end_count_needed += 1
                if stripped == "End":
                    end_count_needed -= 1
            line = "\n".join(lines)

        try:
            code = compile_source(line + "\n", "<repl>")
            # Execute in shared VM
            from veltrix.vm import CallFrame
            frame = CallFrame(code, len(vm.stack))
            vm.frames.append(frame)
            vm.execute()
        except VeltrixError as e:
            print(str(e))
        except KeyboardInterrupt:
            print("\nInterrupted.")


# ─── Usage ────────────────────────────────────────────────────────────────────

def print_usage():
    """Print usage instructions."""
    print_banner()
    print("  Usage:")
    print("    python main.py run <file.vlx>        Run a Veltrix program")
    print("    python main.py run <file.vlb>        Execute compiled bytecode")
    print("    python main.py compile <file.vlx>    Compile to .vlb bytecode")
    print("    python main.py dev <file.vlx>        Compile + run with disassembly")
    print("    python main.py disassemble <file>    Print readable opcodes")
    print("    python main.py repl                  Start interactive REPL")
    print("    python main.py help                  Show this help message")
    print("\n  Options:")
    print("    --legacy                             Allow implicit newlines (no required semicolons)")
    print()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    """Entry point for the Veltrix CLI."""
    args = sys.argv[1:]

    if not args:
        print_usage()
        return

    legacy_mode = "--legacy" in args
    if legacy_mode:
        args.remove("--legacy")

    if not args:
        print_usage()
        return

    command = args[0].lower()

    if command == "run":
        if len(args) < 2:
            print("\nVeltrix Error:\n  Please provide a .vlx or .vlb file to run.")
            print("  Usage: python main.py run <file.vlx>\n")
            sys.exit(1)
        print_banner()
        run_file(args[1], legacy_mode=legacy_mode)

    elif command == "compile":
        if len(args) < 2:
            print("\nVeltrix Error:\n  Please provide a .vlx file to compile.")
            print("  Usage: python main.py compile <file.vlx>\n")
            sys.exit(1)
        print_banner()
        compile_file(args[1], legacy_mode=legacy_mode)

    elif command == "dev":
        if len(args) < 2:
            print("\nVeltrix Error:\n  Please provide a .vlx file.")
            print("  Usage: python main.py dev <file.vlx>\n")
            sys.exit(1)
        print_banner()
        run_file(args[1], verbose=True, legacy_mode=legacy_mode)

    elif command == "disassemble":
        if len(args) < 2:
            print("\nVeltrix Error:\n  Please provide a .vlx or .vlb file.")
            print("  Usage: python main.py disassemble <file>\n")
            sys.exit(1)
        print_banner()
        disassemble_file(args[1], legacy_mode=legacy_mode)

    elif command == "repl":
        run_repl()

    elif command == "help":
        print_usage()

    else:
        print(f"\nVeltrix Error:\n  Unknown command: '{command}'")
        print("  Use 'run', 'compile', 'dev', 'disassemble', 'repl', or 'help'.\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
