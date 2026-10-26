"""CLI: `python -m datamesh demo` runs the end-to-end demo;
`python -m datamesh serve` starts the optional FastAPI service."""

from __future__ import annotations

import sys

from .config import load_settings


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] == "demo":
        import runpy
        from pathlib import Path
        demo_path = Path(__file__).resolve().parents[2] / "examples" / "run_demo.py"
        runpy.run_path(str(demo_path), run_name="__main__")
        return 0
    if argv[0] == "serve":
        try:
            import uvicorn
        except ImportError:
            print("uvicorn not installed; pip install -r requirements.txt", file=sys.stderr)
            return 1
        from .platform import MeshPlatform
        from .service import create_app
        settings = load_settings()
        uvicorn.run(create_app(MeshPlatform()), host=settings.host, port=settings.port)
        return 0
    print("usage: python -m datamesh [demo|serve]", file=sys.stderr)
    return 2
