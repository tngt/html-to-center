#!/usr/bin/env python3
"""
deploy.py - 将 dashboard 推送到 GitHub Pages

用法：
  python deploy.py

前提：
  - dashboard/ 目录已初始化为 git repo，remote 指向 GitHub Pages 仓库
  - 或者 config.json 中配置了 github_pages_repo，由本脚本初始化
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

CONFIG_PATH = Path.home() / ".config" / "html-to-center" / "config.json"

def load_config():
    if not CONFIG_PATH.exists():
        print(f"Error: config not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)

def run(cmd: list, cwd: str = None, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"命令失败：{' '.join(cmd)}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return result

def ensure_git_repo(dashboard_dir: Path, remote_url: str):
    git_dir = dashboard_dir / ".git"
    if not git_dir.exists():
        print("初始化 git 仓库...", file=sys.stderr)
        run(["git", "init"], cwd=str(dashboard_dir))
        run(["git", "remote", "add", "origin", remote_url], cwd=str(dashboard_dir))
        # 创建 .nojekyll 避免 GitHub Pages 忽略下划线文件
        (dashboard_dir / ".nojekyll").touch()
        print("Git 仓库已初始化", file=sys.stderr)
    else:
        # 确认 remote 正确
        result = run(["git", "remote", "get-url", "origin"], cwd=str(dashboard_dir), check=False)
        if result.returncode != 0:
            run(["git", "remote", "add", "origin", remote_url], cwd=str(dashboard_dir))

def main():
    config = load_config()
    center_dir = Path(config["center_dir"])
    dashboard_dir = center_dir / "dashboard"
    remote_url = config.get("github_pages_repo")

    if not remote_url:
        print("Error: config.json 中未配置 github_pages_repo", file=sys.stderr)
        sys.exit(1)

    if not dashboard_dir.exists() or not (dashboard_dir / "index.html").exists():
        print("Error: dashboard/index.html 不存在，请先生成 dashboard", file=sys.stderr)
        sys.exit(1)

    ensure_git_repo(dashboard_dir, remote_url)

    commit_msg = f"update dashboard {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    print("提交变更...", file=sys.stderr)
    run(["git", "add", "-A"], cwd=str(dashboard_dir))

    # 检查是否有变更
    status = run(["git", "status", "--porcelain"], cwd=str(dashboard_dir))
    if not status.stdout.strip():
        print("没有变更，无需部署", file=sys.stderr)
        return

    run(["git", "commit", "-m", commit_msg], cwd=str(dashboard_dir))

    print("推送到 GitHub Pages...", file=sys.stderr)
    result = run(["git", "push", "-u", "origin", "HEAD:gh-pages"], cwd=str(dashboard_dir), check=False)
    if result.returncode != 0:
        # 首次推送可能需要强制
        run(["git", "push", "-u", "origin", "HEAD:gh-pages", "--force"], cwd=str(dashboard_dir))

    print("部署完成", file=sys.stderr)

    # 推断 GitHub Pages URL
    if "github.com" in remote_url:
        parts = remote_url.rstrip("/").rstrip(".git").split("/")
        if len(parts) >= 2:
            user, repo = parts[-2], parts[-1]
            pages_url = f"https://{user}.github.io/{repo}"
            print(f"Dashboard URL: {pages_url}")

if __name__ == "__main__":
    main()
