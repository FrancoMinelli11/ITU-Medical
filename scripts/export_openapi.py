from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_dir))

from app.main import app  # noqa: E402


def main():
    schema = app.openapi()
    out_path = Path(__file__).resolve().parents[1] / "frontend" / "src" / "api" / "openapi.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    print(f"OpenAPI schema exported to {out_path} ({len(schema['paths'])} endpoints)")


if __name__ == "__main__":
    main()
