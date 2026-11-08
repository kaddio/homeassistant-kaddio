"""Validate the integration's GraphQL queries against Kaddio's published schema.

Kaddio serves its schema publicly at <kaddio address>/graphql/schema. If a field the integration uses is renamed or
removed, this fails, so we find out before customers do.

    pip install graphql-core
    python scripts/check_schema.py [schema URL]
"""

from __future__ import annotations

import importlib.util
import sys
import types
import urllib.request
from pathlib import Path

from graphql import build_schema, parse, validate

DEFAULT_SCHEMA_URL = "https://support.kaddio.com/graphql/schema"
ROOT = Path(__file__).resolve().parent.parent / "custom_components" / "kaddio"


def load_queries() -> dict[str, str]:
    """Import gql.py without Home Assistant (it only depends on models.py)."""
    pkg = types.ModuleType("kaddio_pkg")
    pkg.__path__ = [str(ROOT)]
    sys.modules["kaddio_pkg"] = pkg
    for name in ("models", "gql"):
        spec = importlib.util.spec_from_file_location(f"kaddio_pkg.{name}", ROOT / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"kaddio_pkg.{name}"] = module
        spec.loader.exec_module(module)
    gql = sys.modules["kaddio_pkg.gql"]
    return {"locations": gql.LOCATIONS_QUERY, "events": gql.EVENTS_QUERY}


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SCHEMA_URL
    with urllib.request.urlopen(url, timeout=30) as response:
        sdl = response.read().decode("utf-8")
    schema = build_schema(sdl)

    failed = False
    for name, query in load_queries().items():
        errors = validate(schema, parse(query))
        if errors:
            failed = True
            print(f"FAIL {name}:")
            for error in errors:
                print(f"  - {error.message}")
        else:
            print(f"ok   {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
