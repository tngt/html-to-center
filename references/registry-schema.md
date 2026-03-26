# Registry Schema

registry.json 是整个 center 的数据地基。

## 完整结构

```json
{
  "meta": {
    "version": "1.0",
    "root": "/Users/xxx/projects",
    "created_at": "2025-03-26",
    "last_updated": "2025-03-26",
    "total_files": 42
  },
  "summary": {
    "last_generated": "2025-03-24",
    "week": "2025-W12",
    "content": "最近两周主要在研究 AI 工具的竞品格局，同时在探索 RAG 的工程实现..."
  },
  "files": [
    {
      "id": "uuid-v4",
      "path": "/Users/xxx/projects/ai-research/competitive-analysis.html",
      "filename": "competitive-analysis.html",
      "type": "html",
      "project": "AI工具研究",
      "topic": "竞品分析",
      "description": "DeepSeek vs GPT-4 综合对比报告",
      "tags": ["竞品", "LLM", "DeepSeek", "GPT-4"],
      "created_at": "2025-03-20",
      "registered_at": "2025-03-20"
    }
  ]
}
```

## 字段说明

| 字段 | 来源 | 说明 |
|------|------|------|
| id | 自动生成 | UUID v4，唯一标识 |
| path | 文件系统 | 绝对路径，直接用于打开文件 |
| filename | 文件系统 | 不含路径的文件名 |
| type | 文件系统 | `html` 或 `md` |
| project | Claude 推断 | 从目录名推断，用户可修改 |
| topic | Claude 推断 | 从文件名+内容推断 |
| description | Claude 推断 | 一句话描述，20字以内 |
| tags | Claude 推断 | 2-4个关键词，用于搜索过滤 |
| created_at | 文件系统 | 文件的创建时间 |
| registered_at | 系统时间 | 收录到 center 的时间 |
