from enum import Enum


class ColorScheme(Enum):
    VIRIDIS = "viridis"
    ROCKET = "rocket"
    MAKOTO = "makoto"
    SPECTRAL = "spectral"

class ColorPalette:
    """Color schemes for matrix visualization"""
    SCHEMES = {
        ColorScheme.VIRIDIS: {
            "strong": "\033[38;5;114m",  # Lime Green
            "medium": "\033[38;5;37m",     # Teal
            "weak": "\033[38;5;31m",   # Deep Blue
            "minimal": "\033[38;5;55m",   # Dark Purple 
            "highlight": "\033[38;5;227m" # Bright Yellow
        },
        ColorScheme.ROCKET: {
            "strong": "\033[38;5;89m",    # Deep Plum
            "medium": "\033[38;5;161m",   # Reddish Purple
            "weak": "\033[38;5;196m",     # Warm Red
            "minimal": "\033[38;5;209m",   # Coral
            "highlight": "\033[38;5;223m"  # Light Peach
        },
        ColorScheme.MAKOTO: {
            "strong": "\033[38;5;232m",   # Near Black
            "medium": "\033[38;5;24m",    # Dark Blue
            "weak": "\033[38;5;67m",      # Steel Blue
            "minimal": "\033[38;5;117m",  # Light Sky Blue
            "highlight": "\033[38;5;195m" # Pale Blue
        },
        ColorScheme.SPECTRAL: {
            "strong": "\033[38;5;160m",   # Red
            "medium": "\033[38;5;215m",   # Orange
            "weak": "\033[38;5;229m",     # Soft Yellow
            "minimal": "\033[38;5;151m",  # Mint Green
            "highlight": "\033[38;5;32m"  # Cool Blue
        }
    }

