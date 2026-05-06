"""
build_assets.py - Cache-busting asset pipeline for Docker builds.

Hashes static JS and CSS files, rewrites import references inside JS modules,
and updates index.html to reference the hashed filenames.
Original unhashed files are removed so they cannot be accidentally served.

Intended to run once during `docker build`, after source files are copied.
Not needed for local development.

Usage:
    python build_assets.py [--static-dir path/to/static]
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

HASH_LENGTH = 8


def file_hash(path: Path) -> str:
    """Return the first HASH_LENGTH hex chars of the MD5 digest of a file."""
    h = hashlib.md5()
    h.update(path.read_bytes())
    return h.hexdigest()[:HASH_LENGTH]


def content_hash(content: str) -> str:
    """Return the first HASH_LENGTH hex chars of the MD5 digest of a string."""
    h = hashlib.md5()
    h.update(content.encode())
    return h.hexdigest()[:HASH_LENGTH]


def hashed_name(original: Path, digest: str) -> Path:
    """Return a sibling path with the hash inserted before the extension."""
    return original.with_name(f"{original.stem}.{digest}{original.suffix}")


def main(static_dir: Path) -> None:
    scripts_dir = static_dir / "scripts"
    style_dir = static_dir / "style"
    index_html = static_dir / "index.html"

    # --- 1. Hash leaf files (no internal asset references) ---

    leaf_files = {
        "auth.js": scripts_dir / "auth.js",
        "cv-client.js": scripts_dir / "cv-client.js",
        "main.css": style_dir / "main.css",
    }

    hashed: dict[str, Path] = {}  # original filename -> new hashed Path

    for name, path in leaf_files.items():
        digest = file_hash(path)
        new_path = hashed_name(path, digest)
        path.rename(new_path)
        hashed[name] = new_path
        print(f"  {path.name} -> {new_path.name}")

    # --- 2. Rewrite main.js import references, then hash it ---

    main_js = scripts_dir / "main.js"
    js_content = main_js.read_text(encoding="utf-8")

    # Replace bare relative import references for the hashed leaf files.
    # Matches: "./cv-client.js" or "./auth.js" (with or without leading ./)
    for original_name, new_path in hashed.items():
        js_content = re.sub(
            r'(["\'])(\./)?{}(["\'])'.format(re.escape(original_name)),
            lambda m, n=new_path.name: f"{m.group(1)}./{n}{m.group(3)}",
            js_content,
        )

    digest = content_hash(js_content)
    new_main_js = hashed_name(main_js, digest)
    new_main_js.write_text(js_content, encoding="utf-8")
    main_js.unlink()
    hashed["main.js"] = new_main_js
    print(f"  {main_js.name} -> {new_main_js.name}")

    # --- 3. Rewrite index.html ---

    html = index_html.read_text(encoding="utf-8")

    # main.css
    html = html.replace("./style/main.css", f"./style/{hashed['main.css'].name}")
    # main.js
    html = html.replace("./scripts/main.js", f"./scripts/{hashed['main.js'].name}")

    index_html.write_text(html, encoding="utf-8")
    print(f"  index.html updated")

    print("Asset hashing complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hash static assets for cache-busting.")
    parser.add_argument(
        "--static-dir",
        type=Path,
        default=Path("app/static"),
        help="Path to the static files directory (default: app/static)",
    )
    args = parser.parse_args()

    static_dir = args.static_dir.resolve()
    if not static_dir.is_dir():
        print(f"ERROR: Static directory not found: {static_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Hashing assets in: {static_dir}")
    main(static_dir)
