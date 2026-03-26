#!/usr/bin/env python3
"""
register.py - 将文件记录写入 registry.json

用法：
  # 注册单个文件（元数据通过 stdin JSON 传入）
  echo '{"path":"/xxx/file.html","project":"AI研究","topic":"竞品分析","description":"xxx","tags":["竞品"]}' | python register.py

  # 批量注册（从 scan_result.json + 元数据列表）
  python register.py --batch /path/to/metadata_list.json

  # 移除记录
  python register.py --remove /path/to/file.html

  # 更新记录（通过 stdin 传入带 path 的元数据）
  echo '{"path":"/xxx/file.html","topic":"新主题"}' | python register.py --update
"""

import sys
import json
import uuid
import argparse
from datetime import datetime
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "html-to-center" / "config.json"

def load_config():
    if not CONFIG_PATH.exists():
        print(f"Error: config not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)

def load_registry(registry_path: Path) -> dict:
    if registry_path.exists():
        with open(registry_path, encoding="utf-8") as f:
            return json.load(f)
    return {
        "meta": {
            "version": "1.0",
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "total_files": 0
        },
        "summary": {
            "last_generated": None,
            "week": None,
            "content": None
        },
        "files": []
    }

def save_registry(registry: dict, registry_path: Path):
    registry["meta"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    registry["meta"]["total_files"] = len(registry["files"])
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)

def find_existing(registry: dict, path: str) -> int:
    """返回已存在记录的索引，不存在返回 -1"""
    for i, f in enumerate(registry["files"]):
        if f["path"] == path:
            return i
    return -1

def build_entry(data: dict) -> dict:
    """从元数据构建完整的 registry 条目"""
    path = Path(data["path"])
    stat = path.stat() if path.exists() else None

    created_at = data.get("created_at")
    if not created_at and stat:
        created_at = datetime.fromtimestamp(
            stat.st_birthtime if hasattr(stat, "st_birthtime") else stat.st_mtime
        ).strftime("%Y-%m-%d")

    return {
        "id": str(uuid.uuid4()),
        "path": data["path"],
        "filename": path.name,
        "type": "html",
        "project": data.get("project", ""),
        "topic": data.get("topic", ""),
        "description": data.get("description", ""),
        "tags": data.get("tags", []),
        "created_at": created_at or datetime.now().strftime("%Y-%m-%d"),
        "registered_at": datetime.now().strftime("%Y-%m-%d"),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", help="批量注册：传入元数据列表 JSON 文件路径")
    parser.add_argument("--remove", help="移除记录：传入文件路径")
    parser.add_argument("--update", action="store_true", help="更新已有记录（从 stdin 读取）")
    args = parser.parse_args()

    config = load_config()
    registry_path = Path(config["center_dir"]) / "registry.json"
    registry = load_registry(registry_path)

    if args.remove:
        idx = find_existing(registry, args.remove)
        if idx == -1:
            print(f"未找到记录：{args.remove}", file=sys.stderr)
            sys.exit(1)
        removed = registry["files"].pop(idx)
        save_registry(registry, registry_path)
        print(f"已移除：{removed['filename']}", file=sys.stderr)

    elif args.batch:
        with open(args.batch, encoding="utf-8") as f:
            metadata_list = json.load(f)
        added = 0
        skipped = 0
        for data in metadata_list:
            if find_existing(registry, data["path"]) != -1:
                skipped += 1
                continue
            registry["files"].append(build_entry(data))
            added += 1
        save_registry(registry, registry_path)
        print(f"批量注册完成：新增 {added} 条，跳过已有 {skipped} 条", file=sys.stderr)

    elif args.update:
        data = json.loads(sys.stdin.read())
        idx = find_existing(registry, data["path"])
        if idx == -1:
            print(f"未找到记录，改为新增：{data['path']}", file=sys.stderr)
            registry["files"].append(build_entry(data))
        else:
            # 只更新传入的字段，保留其他字段
            for key in ["project", "topic", "description", "tags"]:
                if key in data:
                    registry["files"][idx][key] = data[key]
        save_registry(registry, registry_path)
        print("更新成功", file=sys.stderr)

    else:
        # 默认：从 stdin 读取单条记录
        data = json.loads(sys.stdin.read())
        if find_existing(registry, data["path"]) != -1:
            print(f"文件已在 registry 中，使用 --update 来更新", file=sys.stderr)
            sys.exit(0)
        entry = build_entry(data)
        registry["files"].append(entry)
        save_registry(registry, registry_path)
        print(f"已收录：{entry['filename']}", file=sys.stderr)
        print(json.dumps(entry, ensure_ascii=False))

if __name__ == "__main__":
    main()
