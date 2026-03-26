#!/usr/bin/env python3
"""
scan.py - 扫描根目录下所有 HTML 和 MD 文件

用法：
  python scan.py                    # 从 config.json 读取 root
  python scan.py --root /path/to   # 指定根目录
  python scan.py --output /path/to/result.json  # 指定输出文件

输出：scan_result.json，包含所有找到的文件路径和基础信息
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "html-to-center" / "config.json"

EXCLUDE_DIRS = {
    "node_modules", ".git", ".svn", "__pycache__",
    ".next", ".nuxt", "dist", "build", ".cache",
    "vendor", "venv", ".venv", "env"
}

def load_config():
    if not CONFIG_PATH.exists():
        print(f"Error: config not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)

def should_exclude(path: Path, center_dir: str) -> bool:
    center = Path(center_dir).resolve()
    # 排除 center 目录本身
    try:
        path.resolve().relative_to(center)
        return True
    except ValueError:
        pass
    # 排除常见无关目录
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return True
    return False

def scan(root: str, center_dir: str) -> list:
    root_path = Path(root).expanduser().resolve()
    results = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        current = Path(dirpath)

        # 跳过排除目录（就地修改 dirnames 阻止递归进入）
        dirnames[:] = [
            d for d in dirnames
            if not should_exclude(current / d, center_dir)
            and not d.startswith(".")
        ]

        for filename in filenames:
            if not (filename.endswith(".html") or filename.endswith(".md")):
                continue

            filepath = current / filename
            if should_exclude(filepath, center_dir):
                continue

            stat = filepath.stat()
            results.append({
                "path": str(filepath),
                "filename": filename,
                "type": "html" if filename.endswith(".html") else "md",
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_birthtime).strftime("%Y-%m-%d")
                    if hasattr(stat, "st_birthtime")
                    else datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
            })

    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", help="项目根目录")
    parser.add_argument("--output", help="输出 JSON 文件路径")
    args = parser.parse_args()

    config = load_config()
    root = args.root or config.get("root")
    center_dir = config.get("center_dir")

    if not root:
        print("Error: root not specified", file=sys.stderr)
        sys.exit(1)

    print(f"扫描目录：{root}", file=sys.stderr)
    files = scan(root, center_dir)
    print(f"找到 {len(files)} 个文件", file=sys.stderr)

    output = {
        "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "root": root,
        "total": len(files),
        "files": files
    }

    output_path = args.output or str(Path(center_dir) / "scan_result.json")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"结果已保存到：{output_path}", file=sys.stderr)
    # stdout 输出 JSON 供调用方读取
    print(json.dumps(output, ensure_ascii=False))

if __name__ == "__main__":
    main()
