"""Package the final student-facing app under /js/ without changing the existing site."""

from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = (
    "index.html",
    "original.css",
    "style.css",
    "content.js",
    "common.js",
    "engine.js",
    "app.js",
)


def build(output):
    target = output / "js"
    target.mkdir(parents=True, exist_ok=True)
    hashes = {}
    sizes = {}
    for name in FILES:
        data = (HERE / name).read_bytes()
        (target / name).write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
        sizes[name] = len(data)
    manifest = {
        "title": "Stockroom to Statements",
        "public_directory": "js/",
        "runtime_dependencies": [],
        "files_sha256": hashes,
        "files_bytes": sizes,
        "application_bytes": sum(sizes.values()),
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "dist")
    build(parser.parse_args().output)
