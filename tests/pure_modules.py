from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

INTEGRATION_DIR = Path(__file__).resolve().parent.parent / "custom_components" / "kaddio"


def load_pure_modules(package_name: str, *module_names: str) -> types.SimpleNamespace:
    package = types.ModuleType(package_name)
    package.__path__ = [str(INTEGRATION_DIR)]
    sys.modules[package_name] = package

    loaded: dict[str, types.ModuleType] = {}
    for module_name in module_names:
        qualified_name = f"{package_name}.{module_name}"
        spec = importlib.util.spec_from_file_location(
            qualified_name, INTEGRATION_DIR / f"{module_name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[qualified_name] = module
        spec.loader.exec_module(module)
        loaded[module_name] = module
    return types.SimpleNamespace(**loaded)
