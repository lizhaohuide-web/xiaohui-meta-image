# 流水线 Skill 生成模板

> 被 SKILL.md Phase 2 Step 2.2-2.4 引用
> 生成新赛道 Skill 时，按以下模板填充知识库提取的最佳实践。

## SKILL.md 模板

```markdown
---
name: {赛道英文名}
description: {一句话描述，包含平台、垂类、频率}
version: 1.0.0
category: content
triggers:
  - {中文赛道名}
  - {相关触发词}
---

# {赛道中文名} 全自动流水线

> 「{一句 slogan}」

## 流程概览

1. 选题推送（Cron 触发 / 手动）
2. 文案生成（{文案风格}）
3. 配图生成（{配图规范}）
4. 人工审核
5. 发布 + 数据回填

## Step 1: 选题

{从知识库提取的选题方向，生成 10 个候选}

**实际采集方式**（优先使用脚本，不要空想）：
```bash
python3 scripts/topic_collector.py --track {赛道英文名} --limit 10
python3 scripts/topic_collector.py --track {赛道英文名} --format json --output /tmp/topics.json
```

## Step 2: 文案生成

**风格规则：** {从知识库提取的文案风格}
**结构模板：** {从知识库提取的爆款公式}
**禁忌清单：** {从知识库提取的文案禁忌}

## Step 3: 配图生成

**规格：** {配图规范}
**策略：** {生图策略}

## Step 4: 质量检查

- [ ] 标题是否吸引目标用户？
- [ ] 文案是否符合风格规则？
- [ ] 图片规格是否达标？
- [ ] 标签是否匹配？
{从知识库提取的禁忌清单}

## Step 5: 发布 + 变现

**发布方式：** {平台对应的发布方式}
**变现路径：** {变现路径}
```

## style-guide.md 模板

```markdown
# {赛道名} 文案风格指南

## 核心原则
- {原则 1}
- {原则 2}

## 正确示例 vs 反面示例
| 正确 | 反面 |
|------|------|
| {示例} | {示例} |

## 句式模板
- 开头钩子：{模板}
- 干货主体：{模板}
- 结尾引导：{模板}
```

## tag-library.md 模板

```markdown
# 标签库

## 高流量标签
{从知识库提取的标签}

## 长尾标签
{按内容类型细分}
```

## content-calendar.md 模板

```markdown
# 选题日历模板

| 日期 | 选题方向 | 类型 | 关键词 | 封面建议 |
|------|---------|------|--------|---------| 
```

## copywriting-template.md 模板

```markdown
# 封面标题：{爆款公式}

## 正文
{开头钩子}
{核心信息点 1-5}
{行动指引}

#️⃣ 标签：{自动匹配}
```

## image-prompt-template.md 模板

```markdown
# 生图提示词模板

{配图规范}
{生图策略}
```

## 按需生成附加目录

根据赛道特征和用户资产，按需生成：

| 目录 | 触发条件 | 内容 |
|------|---------|------|
| `scripts/` | 需要自动化采集/处理 | 爬虫脚本、数据处理脚本、发布脚本 |
| `data/` | 需要结构化数据 | 标签库 CSV、选题数据库、竞品数据 |
| `config/` | 需要 API 凭证 | 发布平台配置、生图 API 配置 |

示例：
- 公众号玄学 → `scripts/browser_publish.py`（浏览器模拟登录发布脚本）
- 小红书 AI → `scripts/ai_collector.py`（AI 资讯采集脚本）
- 旅行赛道 → `data/destinations.csv`（目的地数据库）

## 输出路径规则

| 检测到的平台 | Skill 输出路径 |
|------------|--------------| 
| **Hermes** | `~/.hermes/skills/content/{赛道英文名}/` |
| **OpenClaw** | `~/.openclaw/skills/content/{赛道英文名}/` |
| **Claude Desktop** | `~/.claude/skills/{赛道英文名}/` |
| **Cursor** | `.cursor/rules/{赛道英文名}.md` |
| **混合环境** | 优先输出到主平台，同时生成兼容版本 |
| **无法检测** | `~/content-pipelines/{赛道英文名}/`，用户自行部署 |

## 命名规则

- 小红书育儿 → `xiaohongshu-parenting`
- 公众号玄学 → `wechat-metaphysics`
- 抖音知识口播 → `douyin-knowledge-talk`
