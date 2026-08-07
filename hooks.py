import os
import sys

# 1. Force Python to see your root workspace folder and "extensions/" directory
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 2. Safely import your local extension module now that the path is active
from extensions.tooltip import DeadLinkTooltipExtension

def on_config(config):
    """
    This native MkDocs event runs during initialization.
    We inject our extension instance straight into the markdown parser.
    """
    print("Loading custom module")
    # Instantiate your custom extension class
    custom_tooltip_ext = DeadLinkTooltipExtension()
    
    # Append it to the active configuration list programmatically
    config['markdown_extensions'].append(custom_tooltip_ext)
    
    return config