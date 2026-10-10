"""Build a separate static pilot; no Node tooling or deployment changes needed."""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import io
import json
import shutil
import tarfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
BROWSER = ROOT / "browser"


def shared_source() -> str:
    source = (ROOT / "streamlit_app.py").read_text()
    tree = ast.parse(source)
    # Only declarations and the original page configuration are extracted.
    # Reject an unexpected driver structure rather than silently running it.
    calls = [
        n
        for n in tree.body
        if isinstance(n, ast.Expr)
        and isinstance(n.value, ast.Call)
        and isinstance(n.value.func, ast.Name)
        and n.value.func.id == "initialize_state"
    ]
    main_guard = [
        n
        for n in tree.body
        if isinstance(n, ast.If) and ast.unparse(n.test) == "__name__ == '__main__'"
    ]
    if len(calls) + len(main_guard) != 1:
        raise ValueError("Server driver changed; review browser extraction")
    stop = calls[0].lineno if calls else main_guard[0].lineno
    keep = []
    for node in tree.body:
        if node.lineno >= stop:
            break
        if isinstance(
            node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)
        ):
            keep.append(node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            # The server's layout-driver assignments are intentionally excluded.
            if not isinstance(getattr(node, "value", None), ast.Call):
                keep.append(node)
        elif isinstance(node, ast.Expr) and (
            isinstance(node.value, ast.Constant)
            or (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == "set_page_config"
            )
        ):
            keep.append(node)
    return "\n\n".join(ast.get_source_segment(source, node) for node in keep) + "\n"


def app_files() -> dict[str, str]:
    paths = [
        BROWSER / "__init__.py",
        BROWSER / "app.py",
        BROWSER / "navigation.py",
        BROWSER / "ui.py",
    ]
    paths.extend(sorted((ROOT / "stockroom_to_statements").glob("*.py")))
    files = {str(path.relative_to(ROOT)): path.read_text() for path in paths}
    files["browser/shared_app.py"] = shared_source()
    return files


def build(
    output: Path, archive: Path | None = None, asset_cache: Path | None = None
) -> dict:
    lock = json.loads((BROWSER / "runtime-lock.json").read_text())
    data = (
        archive.read_bytes()
        if archive
        else urllib.request.urlopen(lock["tarball"], timeout=60).read()
    )
    digest = "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode()
    if digest != lock["integrity"]:
        raise ValueError("Runtime archive integrity mismatch")
    output.mkdir(parents=True, exist_ok=True)
    vendor = output / "vendor"
    if vendor.exists():
        shutil.rmtree(vendor)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as bundle:
        for member in bundle.getmembers():
            path = PurePosixPath(member.name)
            if not member.isfile() or path.parts[:2] != ("package", "build"):
                continue
            relative = PurePosixPath(*path.parts[2:])
            if ".." in relative.parts or relative.is_absolute():
                raise ValueError("Unsafe archive path")
            if relative.suffix == ".map":
                continue  # Debug source maps are not needed to run the activity.
            target = vendor / str(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bundle.extractfile(member).read())
    wheel = vendor / "wheels" / f"streamlit-{lock['streamlit']}-cp313-none-any.whl"
    if not wheel.is_file():
        raise ValueError("Expected bundled Streamlit version missing")

    def download(asset):
        cached = (
            asset_cache / hashlib.sha256(asset["url"].encode()).hexdigest()
            if asset_cache
            else None
        )
        payload = (
            cached.read_bytes()
            if cached and cached.is_file()
            else urllib.request.urlopen(asset["url"], timeout=60).read()
        )
        if hashlib.sha256(payload).hexdigest() != asset["sha256"]:
            raise ValueError(f"Asset integrity mismatch: {asset['file']}")
        directory = (
            "pyodide"
            if asset["url"].startswith("https://cdn.jsdelivr.net/pyodide/")
            else "python"
        )
        target = vendor / directory / asset["file"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(download, lock["assets"]))
    requirements = [
        f"./vendor/python/{asset['file']}#sha256={asset['sha256']}"
        for asset in lock["assets"]
        if asset["url"].startswith("https://files.pythonhosted.org/")
    ]
    files = app_files()
    app = {
        "entrypoint": "browser/app.py",
        "files": files,
        "requirements": [],
        "pyodideUrl": "./pyodide-loader.mjs",
        "sharedWorker": False,
        "streamlitConfig": {
            "browser.gatherUsageStats": False,
            "client.toolbarMode": "viewer",
            "theme.primaryColor": "#CE0037",
        },
    }
    (output / "app.json").write_text(json.dumps(app, ensure_ascii=False))
    (output / "bootstrap-wheels.json").write_text(
        json.dumps(requirements, indent=2) + "\n"
    )
    shutil.copyfile(BROWSER / "index.html", output / "index.html")
    shutil.copyfile(BROWSER / "pyodide-loader.mjs", output / "pyodide-loader.mjs")
    for notice in ("THIRD_PARTY_NOTICES.md", "STLITE-LICENSE.txt"):
        shutil.copyfile(BROWSER / notice, output / notice)
    # Also materialize Python for the server AppTest regression harness.
    for name, content in files.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    manifest = {
        "runtime": lock,
        "source_sha256": {
            name: hashlib.sha256(content.encode()).hexdigest()
            for name, content in files.items()
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=BROWSER / "dist")
    parser.add_argument(
        "--runtime-archive",
        type=Path,
        help="Optional cached npm tarball; integrity is still checked",
    )
    parser.add_argument(
        "--asset-cache",
        type=Path,
        help="Optional verified test cache; all asset hashes are checked",
    )
    args = parser.parse_args()
    result = build(args.output, args.runtime_archive, args.asset_cache)
    print(
        f"Built {args.output}: stlite {result['runtime']['version']}, Streamlit {result['runtime']['streamlit']}, {len(result['source_sha256'])} Python files"
    )
