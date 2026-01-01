# Pre-import to fix typing_extensions compatibility issues
# This must be imported before any other modules that use pydantic

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Force import of typing_extensions before pydantic
try:
    import typing_extensions
    print("[OK] typing_extensions imported successfully")
except ImportError as e:
    print(f"[ERROR] Error importing typing_extensions: {e}")
    raise

# Ensure proper typing_extensions version for Pydantic 2.x compatibility
if hasattr(typing_extensions, '__version__'):
    print(f"[OK] typing_extensions version: {typing_extensions.__version__}")
else:
    print("[OK] typing_extensions loaded (version not available)")
