from __future__ import annotations

import importlib.util
import sys
import types
import urllib.request
from pathlib import Path

from graphql import build_schema, parse, validate

DEFAULT_SCHEMA_URL = "https://support.kaddio.com/graphql/schema"
INTEGRATION_DIR = Path(__file__).resolve().parent.parent / "custom_components" / "kaddio"
PACKAGE_NAME = "kaddio_schema_check"
HOME_ASSISTANT_FREE_MODULES = ("models", "graphql_api")


def load_integration_queries() -> dict[str, str]:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(INTEGRATION_DIR)]
    sys.modules[PACKAGE_NAME] = package
    for module_name in HOME_ASSISTANT_FREE_MODULES:
        qualified_name = f"{PACKAGE_NAME}.{module_name}"
        spec = importlib.util.spec_from_file_location(
            qualified_name, INTEGRATION_DIR / f"{module_name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[qualified_name] = module
        spec.loader.exec_module(module)
    api = sys.modules[f"{PACKAGE_NAME}.graphql_api"]
    return {"locations": api.LOCATIONS_QUERY, "events": api.EVENTS_QUERY}


def download_schema(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8")


def main() -> int:
    schema_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SCHEMA_URL
    schema = build_schema(download_schema(schema_url))

    has_failures = False
    for name, query in load_integration_queries().items():
        errors = validate(schema, parse(query))
        if not errors:
            print(f"ok   {name}")
            continue
        has_failures = True
        print(f"FAIL {name}:")
        for error in errors:
            print(f"  - {error.message}")
    return 1 if has_failures else 0


if __name__ == "__main__":
    sys.exit(main())
