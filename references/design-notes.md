# 设计原则与坑点

> 被 SKILL.md 引用，记录架构决策和踩坑经验。

## 核心设计原则

1. **赛道知识库是底盘，不是用户的 skills**：即使全新智能体零 skills，也能基于知识库生成高质量流水线。用户 skills 只是「加速器」，降低启动成本，不是必需品。

2. **跨平台兼容是必须的**：不要假设用户用 Hermes。扫描 6 种平台路径，不报错跳过，优雅降级。

3. **动态推荐 > 预设推荐**：推荐必须基于扫描结果实时生成，不能硬编码。每个推荐附带匹配理由、启动成本、变现路径。

4. **输出路径跟随平台**：检测到哪个平台就输出到对应目录，混合环境可一键部署多平台。

## 坑点记录

- ❌ **坑 1：资产扫描只扫 Hermes** → 用户用 OpenClaw/Claude Desktop 时完全扫不到 → 改为多平台扫描
- ❌ **坑 2：分类映射绑定平台前缀** → `baoyu-*` 只在 baoyu 生态有效 → 改为关键词匹配，不依赖前缀
- ❌ **坑 3：推荐是预设的** → 不管用户装了什么都推荐同样的 3 个 → 改为动态匹配
- ❌ **坑 4：生成路径硬编码** → 只能生成到 `~/.hermes/skills/content/` → 改为平台检测 + 自适应输出
- ❌ **坑 5：扫描失败直接报错** → 新环境无 skills 目录时中断 → 改为交互式询问 + 通用推荐

## 模糊需求 3 问模型

当用户说「我想做自媒体但不知道做什么」时，用以下 3 问定位（最多 2 轮）：

1. 内容形式：文章/图文/视频/都行
2. 变现预期：快（1-3 月）/中（3-6 月）/慢（长期）
3. 兴趣领域：生活类/知识类/文化类/情感类/都没有

## 已有赛道速查

| 平台 | 垂类 | Skill 名 | 验证状态 |
|------|------|---------|---------| 
| 小红书 | 育儿 | xiaohongshu-parenting | ✅ 已验证 |
| 小红书 | AI 工具/变现 | xiaohongshu-ai-tools | ✅ 已验证 |
| 公众号 | 玄学命理 | wechat-metaphysics | ✅ 已验证 |
| 小红书 | 穿搭 | xiaohongshu-fashion | 🔶 知识库理论 |
| 小红书 | 美食 | xiaohongshu-food | 🔶 知识库理论 |
| 小红书 | 宠物 | xiaohongshu-pet | 🔶 知识库理论 |
| 小红书 | 健身 | xiaohongshu-fitness | 🔶 知识库理论 |
| 小红书 | 职场 | xiaohongshu-career | 🔶 知识库理论 |
| 小红书 | 旅行 | xiaohongshu-travel | 🔶 知识库理论 |
| 小红书 | 数码 | xiaohongshu-digital | 🔶 知识库理论 |
| 小红书 | 家居 | xiaohongshu-home | 🔶 知识库理论 |
| 公众号 | 商业/科技 | wechat-business-tech | 🔶 知识库理论 |
| 公众号 | 教育/成长 | wechat-education | 🔶 知识库理论 |
| 视频号 | 中老年情感 | shipinhao-emotional | 🔶 知识库理论 |
| 视频号 | 知识口播 | shipinhao-knowledge | 🔶 知识库理论 |
| 抖音 | 知识口播 | douyin-knowledge-talk | 🔶 知识库理论 |
| 抖音 | 宠物 | douyin-pet | 🔶 知识库理论 |
| 抖音 | 健身 | douyin-fitness | 🔶 知识库理论 |

> 当某赛道首次完整跑通 Phase 2.5 测试后，将 YAML 中 `verified` 改为 `true`，速查表更新为 ✅。

## 反馈记忆机制

用户反馈存入 `feedback-log.json`，格式：

```json
[
  {
    "date": "2026-04-16",
    "track": "xiaohongshu-fashion",
    "feedback": "文案太官方了",
    "adjustment": "style-guide 语气改为闺蜜口吻",
    "scope": "track",
    "applied": true
  }
]
```

**scope 字段**：
- `"track"` → 仅影响该赛道后续生成
- `"global"` → 影响所有赛道（用户说"这个调整不错"时标记）

**应用规则**：
1. 生成新流水线前，先读取 `feedback-log.json`
2. 同赛道有历史反馈 → 自动应用
3. `scope: "global"` 的反馈 → 应用到所有后续生成
