"""
Veltrix Styling Engine Validation and Rendering
=============================================
Provides validation for styled text properties and renders them
either to Terminal ANSI sequences or GUI metadata.
"""

import re
from veltrix.errors import VeltrixRuntimeError


class StyleValidator:
    """Validates styling properties for Veltrix components."""

    @staticmethod
    def validate_color(color: str, filename: str = None, line: int = None):
        """Validates a hex color string or known named colors."""
        if not isinstance(color, str):
            raise VeltrixRuntimeError(f"Color must be a string, got {type(color).__name__}", filename, line)
        if color.startswith('#'):
            if not re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color):
                raise VeltrixRuntimeError(f"Invalid hex color: {color}", filename, line)
        return True

    @staticmethod
    def validate_opacity(opacity, filename: str = None, line: int = None):
        """Validates opacity is a number between 0 and 1."""
        if not isinstance(opacity, (int, float)):
            raise VeltrixRuntimeError(f"Opacity must be a number, got {type(opacity).__name__}", filename, line)
        if not (0.0 <= opacity <= 1.0):
            raise VeltrixRuntimeError(f"Opacity must be between 0.0 and 1.0, got {opacity}", filename, line)
        return True

    @staticmethod
    def validate_properties(properties: dict, filename: str = None, line: int = None):
        """Validates a dictionary of style properties."""
        for name, value in properties.items():
            if name in ('color', 'bg', 'gradient_start', 'gradient_end'):
                StyleValidator.validate_color(value, filename, line)
            elif name == 'opacity':
                StyleValidator.validate_opacity(value, filename, line)


class TerminalRenderer:
    """Converts Veltrix styled text properties into ANSI terminal codes."""

    # Basic ANSI mapping
    FORMAT_CODES = {
        'bold': '\033[1m',
        'italic': '\033[3m',
        'underline': '\033[4m',
        'strike': '\033[9m'
    }
    RESET_CODE = '\033[0m'

    @staticmethod
    def hex_to_rgb(hex_color: str):
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join(c + c for c in hex_color)
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def rgb_color_code(r, g, b, is_bg=False):
        prefix = "48" if is_bg else "38"
        return f"\033[{prefix};2;{r};{g};{b}m"

    @staticmethod
    def render(text: str, properties: dict) -> str:
        """Applies styles to text via ANSI escape codes."""
        if not properties:
            return text

        prefix_codes = []
        
        # Formatting flags
        for fmt, code in TerminalRenderer.FORMAT_CODES.items():
            if properties.get(fmt):
                prefix_codes.append(code)

        # Gradients (override color)
        if 'gradient_start' in properties and 'gradient_end' in properties:
            # For gradients in terminal, we might color each character or just use the start color.
            # To keep it simple and robust, we'll map gradient to start color for now,
            # or you could implement actual per-character gradient printing.
            # Let's implement a simple start-to-end lerp across the text length.
            return TerminalRenderer.render_gradient_text(
                text, properties['gradient_start'], properties['gradient_end'], prefix_codes
            )

        # Regular color
        if 'color' in properties:
            color = properties['color']
            if color.startswith('#'):
                r, g, b = TerminalRenderer.hex_to_rgb(color)
                prefix_codes.append(TerminalRenderer.rgb_color_code(r, g, b))

        # Background color
        if 'bg' in properties:
            bg = properties['bg']
            if bg.startswith('#'):
                r, g, b = TerminalRenderer.hex_to_rgb(bg)
                prefix_codes.append(TerminalRenderer.rgb_color_code(r, g, b, is_bg=True))
                
        # Opacity we can't do in basic terminal easily, skip or map to a dim color

        prefix = "".join(prefix_codes)
        return f"{prefix}{text}{TerminalRenderer.RESET_CODE}"
        
    @staticmethod
    def render_gradient_text(text: str, start_hex: str, end_hex: str, base_codes: list) -> str:
        """Renders text with a smooth gradient across characters."""
        if not text:
            return ""
            
        try:
            r1, g1, b1 = TerminalRenderer.hex_to_rgb(start_hex)
            r2, g2, b2 = TerminalRenderer.hex_to_rgb(end_hex)
        except ValueError:
            # Fallback
            return f"{''.join(base_codes)}{text}{TerminalRenderer.RESET_CODE}"
            
        length = len(text)
        result = []
        
        for i, char in enumerate(text):
            # calculate ratio based on position
            ratio = i / max(1, length - 1)
            
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            
            color_code = TerminalRenderer.rgb_color_code(r, g, b)
            
            result.append(f"{''.join(base_codes)}{color_code}{char}")
            
        return "".join(result) + TerminalRenderer.RESET_CODE


# GUI Renderer stub for later UI integration
class GUIRenderer:
    """Prepares Veltrix styled text for GUI component rendering."""
    
    @staticmethod
    def extract_metadata(text: str, properties: dict) -> dict:
        """Returns the text and its attached style metadata dictionary."""
        return {
            "text": text,
            "style": properties
        }
