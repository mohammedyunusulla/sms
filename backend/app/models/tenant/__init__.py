import pkgutil
import importlib
import inspect
import sys
from pathlib import Path

# Reference to current package
package_dir = Path(__file__).resolve().parent
package_name = __name__

__all__ = []

# Dynamically import all classes from all modules in this package
for (_, module_name, _) in pkgutil.iter_modules([str(package_dir)]):
    module = importlib.import_module(f"{package_name}.{module_name}")
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj):
            setattr(sys.modules[__name__], name, obj)
            __all__.append(name)
