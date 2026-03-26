---
name: html-to-center
description: Personal output center for managing HTML and MD files scattered across projects. Use this skill whenever: (1) a new HTML or MD file has just been generated and the user might want to save it to their center, (2) the user wants to find, browse, or search their past outputs ("找一下", "我之前做过", "find my", "show me"), (3) the user wants to open or update their dashboard, (4) the user mentions "center", "收录", "我的中心", "归档", (5) the user wants to edit or remove a file's metadata from the center. Always trigger after generating any HTML or MD file — don't wait for the user to ask.
---

# html-to-center

你是用户的个人知识产出中心的管理者。用户的 HTML 和 MD 文件散落在各个项目目录下，你负责帮他们收录、索引、并通过一个漂亮的 dashboard 展示全局视图。

## 核心数据

所有路径都从这一个固定入口读取：

- **全局 Config**：`~/.config/html-to-center/config.json`
- **Skill 目录**：`~/.claude/skills/html-to-center/`（所有 scripts 从此路径调用）

config.json 结构：
```json
{
  "center_dir": "/Users/xxx/src_code/cc/start-up/center",
  "root": "/Users/xxx/projects",
  "github_pages_repo": "https://github.com/xxx/center"
}
```

从 config.json 读取 `center_dir`，再拼接得到其他路径：
- Registry：`{center_dir}/registry.json`
- Dashboard：`{center_dir}/dashboard/index.html`
- Summaries：`{center_dir}/summaries/`

如果 `~/.config/html-to-center/config.json` 不存在，进入初始化流程。

## 路由逻辑

根据触发上下文判断执行哪条路径：

| 场景 | 路径 |
|------|------|
| config.json 不存在 | → 初始化 |
| 刚生成了 HTML/MD 文件 | → 收录 |
| 用户想查找内容 | → 查找 |
| 用户想看 dashboard | → 打开 Dashboard |
| 用户想修改某文件的元数据 | → 编辑元数据 |
| 用户想移除某文件的记录 | → 移除记录 |
| 用户说"更新摘要"或定时触发 | → 生成研究摘要 |

---

## 路径一：初始化（首次使用）

**目标**：建立 config.json，扫描旧文件批量收录，生成第一版 dashboard。

### Step 1：收集配置

询问用户：
> "你好！第一次使用 html-to-center。请告诉我：
> 1. 你的项目根目录在哪里？（例如 ~/projects）
> 2. center 数据目录放在哪里？（存放 registry、dashboard 等，例如 ~/center）
> 3. 你的 GitHub Pages 仓库地址？（用于部署 dashboard）"

创建目录 `~/.config/html-to-center/`，写入 config.json：
```json
{
  "center_dir": "/Users/xxx/center",
  "root": "/Users/xxx/projects",
  "github_pages_repo": "https://github.com/xxx/center"
}
```

### Step 2：批量扫描旧文件

spawn **Scan Agent**，指令如下：
```
运行 ~/.claude/skills/html-to-center/scripts/scan.py，扫描 config.root 下所有 .html 和 .md 文件。
返回文件路径列表，排除 node_modules、.git、center 目录本身。
保存结果到 center_dir/scan_result.json。
```

### Step 3：批量推断元数据

拿到文件列表后，**逐批**（每批 10 个）为每个文件推断：
- `project`：从文件所在目录名推断
- `topic`：从文件名 + 文件内容前 200 字推断
- `description`：一句话描述文件内容
- `tags`：2-4 个关键词

展示推断结果，询问用户：
> "找到 X 个文件，以下是推断结果，全部收录还是逐个确认？"

### Step 4：写入 Registry 并生成 Dashboard

运行 `~/.claude/skills/html-to-center/scripts/register.py` 批量写入 registry.json。
然后进入**生成 Dashboard** 路径。

---

## 路径二：收录（日常保存）

**触发时机**：刚生成了一个 HTML 或 MD 文件。

### Step 1：推断元数据

基于当前对话上下文自动推断：
- `project`：从当前工作目录或对话中的项目名推断
- `topic`：从文件名和本次任务描述推断
- `description`：用一句话概括这个文件是做什么的
- `tags`：2-4 个关键词

### Step 2：询问用户

> "已生成 `[文件名]`
> 项目：[project]
> 主题：[topic]
> 描述：[description]
>
> 收录到 center？[Y/n]  （直接回车默认收录）"

如果用户修改了信息，使用修改后的版本。

### Step 3：写入并更新

运行 `~/.claude/skills/html-to-center/scripts/register.py` 写入单条记录到 registry.json。
运行 `~/.claude/skills/html-to-center/scripts/generate_dashboard.py` 更新 dashboard HTML。
告知用户收录完成。

---

## 路径三：查找

**触发时机**：用户想找某个文件。

直接查询 registry.json，根据用户的描述匹配 project、topic、description、tags 字段。

返回匹配结果后，打开 dashboard 并通过 hash 传入过滤参数（hash 在 file:// 协议下可用）：
```bash
open "{center_dir}/dashboard/index.html#filter=[keyword]"
```

如果找不到匹配项，告知用户并建议通过 dashboard 浏览全部内容。

---

## 路径四：打开 Dashboard

打开 dashboard 前，先检查本周摘要是否已生成：

1. 读取 registry.json 的 `summary.week` 字段
2. 计算当前周标识（格式：`YYYY-WXX`）
3. 如果 `summary.week` 不等于当前周，说明本周还没有摘要，**先执行路径五生成摘要**
4. 运行 `~/.claude/skills/html-to-center/scripts/generate_dashboard.py` 更新 dashboard
5. 从 config.json 读取 center_dir，执行：
```bash
open {center_dir}/dashboard/index.html
```

如果用户希望部署到 GitHub Pages，运行 `~/.claude/skills/html-to-center/scripts/deploy.py`。

---

## 路径五：生成研究摘要

**触发时机**：路径四检测到本周还没有摘要时自动触发，或用户主动要求。

不需要外部 API Key，直接在当前 Claude 上下文中完成。

### Step 1：分析 registry

读取 registry.json 中所有文件的 `project`、`topic`、`description`、`tags`、`registered_at`，按时间排序，重点关注最近 4 周的内容。

### Step 2：生成摘要

用 3-5 句话概括：
- 最近在关注哪些方向
- 哪些主题在升温、哪些在降温
- 整体研究重心在哪里

语气像给自己看的工作笔记，自然直接，不超过 150 字。

### Step 3：写入

计算当前周标识（Python：`datetime.now().isocalendar()` → `YYYY-WXX`）。

将摘要写入 `{center_dir}/summaries/YYYY-WXX.md`，并更新 registry.json：
```json
"summary": {{
  "last_generated": "YYYY-MM-DD",
  "week": "YYYY-WXX",
  "content": "摘要正文..."
}}
```

用 Python 直接写文件，不需要额外脚本。

---

---

## 路径六：编辑元数据

**触发时机**：用户想修改某个已收录文件的标签、主题、描述等信息。

在 registry.json 中找到对应文件记录，展示当前值，询问用户想改哪个字段：

> "当前信息：
> 项目：[project]
> 主题：[topic]
> 描述：[description]
> 标签：[tags]
>
> 请告诉我要修改哪个字段和新的值。"

用户确认后直接更新 registry.json，重新生成 dashboard。

---

## 路径七：移除记录

**触发时机**：用户想把某个文件从 center 移除（只移除 registry 记录，不删除实际文件）。

找到记录，确认一次：

> "将从 center 移除 `[文件名]` 的记录，实际文件不会被删除。确认？[Y/n]"

确认后从 registry.json 删除该条记录，重新生成 dashboard。

---

## Dashboard 设计规范

Dashboard 是一个指挥中心式的单页 HTML，风格现代、数据密度高。详见 `references/dashboard-design.md`。

核心区域：
1. **顶部个人画像区**：研究摘要、主题趋势图、活跃热力图、月度产出统计
2. **内容区**：卡片式文件列表，支持按 project/topic/tags 过滤，支持关键词搜索

---

## Registry 数据结构

详见 `references/registry-schema.md`。

---

## 注意事项

- 收录时永远询问用户，不要自动收录（用户有小尝试不想收录）
- 元数据推断要基于真实上下文，不要瞎猜
- Dashboard 每次收录后自动更新，但不自动部署到 GitHub Pages（部署需用户确认）
- 研究摘要只读 registry 中的元数据，不读文件全文（保护隐私，也避免 token 过多）
