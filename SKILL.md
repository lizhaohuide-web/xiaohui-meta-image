---
name: xiaohui-meta-image
version: 1.3.0
category: content
description: 内容流水线工厂（小辉专属）。用户描述赛道（平台+垂类）→ 交互式诊断 → 匹配赛道知识库 → 生成完整可执行的流水线 Skill → Phase 2.5 实际生图测试通过 → 可选 Cron。
triggers:
  - 内容流水线
  - 赛道匹配
  - 生成流水线
  - 内容工厂
  - 小辉流水线
  - xiaohui-meta-image
---

# 内容流水线工厂

> 「告诉我你的赛道，我还你一条全自动流水线。」

## 核心能力

用户描述内容赛道（如"小红书育儿"、"公众号玄学"），本 Skill 自动完成：
1. **赛道诊断**：交互式追问，确认平台、垂类、受众、变现路径
2. **知识库匹配**：提取该赛道的最佳实践（内容策略、文案风格、配图规范）
3. **流水线生成**：输出完整可执行的 Skill（SKILL.md + references + scripts）
4. **可选 Cron 部署**：一键创建定时任务

## 引用文件索引

| 文件 | 用途 | 何时读取 |
|------|------|---------|
| `references/track-knowledge-base.md` | 赛道知识库（18 个平台×垂类组合） | Phase 1 |
| `references/asset-scan-mapping.md` | 资产扫描路径 + 分类映射表 + 推荐展示格式 | Phase 0 Step 0.1.5 |
| `references/personalized-questions.md` | 按垂类个性化追问表 | Phase 0 Step 0.2.5 |
| `references/skill-templates.md` | 生成 Skill 的所有模板 + 输出路径规则 | Phase 2 |
| `references/design-notes.md` | 设计原则 + 坑点 + 赛道速查 + 反馈记忆机制 | 随时参考 |
| `scripts/pipeline_image_gen.py` | 生图 Fallback 脚本（Nano API → Pillow） | Phase 2.5 |
| `scripts/topic_collector.py` | 选题采集脚本（Twitter + News） | Phase 2 Step 1 |

---

## Phase 0: 赛道诊断（交互式）

### Step 0.1: 接收用户输入

支持三种入口：
- **文字描述**：如"我想做小红书育儿内容"
- **截图/竞品**：上传竞品账号截图，AI 分析赛道特征
- **模糊需求**：如"我想做自媒体但不知道做什么" → 进入推荐模式

### Step 0.1.5: 资产扫描（仅模糊需求时触发）

→ 读取 `references/asset-scan-mapping.md` 执行扫描、分类、推荐。

用户明确说了平台+垂类时，跳过此步。

### Step 0.2: 诊断追问

收集 6 个维度（用户已明确的跳过，缺几个问几个，一次问完）：

| 维度 | 追问示例 |
|------|---------| 
| **平台** | "主要在哪个平台发？小红书/公众号/视频号/抖音？" |
| **垂类** | "什么内容方向？育儿/AI/美食/穿搭/玄学/情感？" |
| **受众** | "目标用户是谁？年龄段？痛点是什么？" |
| **变现** | "打算怎么变现？带货/知识付费/广告/私域？" |
| **频率** | "打算多久发一次？日更/周更？" |
| **风格** | "想要什么风格？专业/接地气/闺蜜口吻/严肃？" |

追问原则：缺几个问几个，不要变成问卷调查。用户说"你帮我定"，直接用知识库默认值。

### Step 0.2.5: 个性化追问

→ 读取 `references/personalized-questions.md`，按垂类追问个性化信息。

### Step 0.3: 输出赛道画像

```
📋 赛道画像确认

平台：{平台}
垂类：{垂类}
受众：{受众}
变现：{变现}
频率：{频率}
风格：{风格}

个性化信息：
- {维度 1}：{值}
- {维度 2}：{值}

→ 匹配知识库：「{平台} × {垂类}」✅
```

用户确认 OK → Phase 1。用户要调整 → 返回 Step 0.2。

---

## Phase 1: 知识库匹配

### Step 1.1: 加载赛道知识库

读取 `references/track-knowledge-base.md`，匹配 `平台 × 垂类` 组合。

匹配逻辑：
1. 精确匹配 → 直接使用
2. 平台匹配 + 垂类近似 → 使用平台默认值 + 提示用户调整
3. 完全未匹配 → 基于已有赛道推理 + 标注「⚠️ 新赛道，未经验证」

### Step 1.2: 提取最佳实践

从匹配结果中提取：爆款公式、文案风格、配图规范、生图策略、发布频率、选题方向、变现路径、标签库、文案禁忌。

---

## Phase 2: 流水线生成

### Step 2.1-2.4: 创建 Skill 目录 + 生成文件

→ 读取 `references/skill-templates.md`，按模板生成完整 Skill 目录结构。

包含：SKILL.md、style-guide.md、tag-library.md、content-calendar.md、copywriting-template.md、image-prompt-template.md + 按需附加目录。

### Step 2.5: 质量自检

- [ ] SKILL.md 包含完整 5 步流程
- [ ] 文案风格已从知识库提取并写入
- [ ] 配图规范已配置
- [ ] 标签库已生成
- [ ] 禁忌清单已包含
- [ ] 目录结构完整（references + templates）
- [ ] 命名符合规范（kebab-case，语义明确）
- [ ] 个性化信息已写入 style-guide.md

---

## Phase 2.5: 用户测试验证（关键步骤）

**生成完成后，不要直接进入 Cron 部署。先跑一遍完整流程。**

### Step 2.5.1: 触发首次测试

用生成的流水线产出一篇完整示例内容（含实际配图），让用户审核。

**测试标准——每步必须真实完成，不能跳过：**

| 步骤 | 必须完成 | 不能只做 |
|------|---------|---------| 
| 选题 | ✅ 生成 1 个具体选题 | ❌ 不能只说"选这个方向" |
| 文案 | ✅ 生成完整文案（含标题、正文、标签） | ❌ 不能只给模板 |
| 配图 | ✅ 实际生图并展示真实图片 | ❌ 不能只给 Prompt |
| 发布 | ✅ 模拟发布流程（或保存到草稿箱） | ❌ 不能跳过 |

**只有用户看到真实产出（文案+实际图片）后说"OK"，才算测试通过。**

### ⚠️ 生图 Fallback 链

```
优先级 1: image_generate 工具（FLUX 2 Pro）
  → 失败不超过 2 次，直接降级
优先级 2: scripts/pipeline_image_gen.py（封装了 Nano + Pillow 完整降级链）
  → terminal: python3 scripts/pipeline_image_gen.py --prompt "..." --image /tmp/out.png
  → 支持批量: --batchfile batch.json --jobs 3
  → 支持自定义尺寸: --width 1080 --height 1920
```

关键经验：
- 用 terminal 执行脚本，不要用 execute_code
- image_generate 失败不超过 2 次就降级
- Nano API 模型名必须是 `[官逆C]Nano banana 2`

### Step 2.5.2: 用户审核 + 迭代

| 用户反馈 | 处理方式 |
|---------|---------| 
| "OK，可以" | → Phase 3 |
| "文案太官方了" | 调整 style-guide.md 语气规则，重新生成 |
| "配图风格不对" | 调整 image-prompt-template.md，重新生图 |
| "选题方向不感兴趣" | 调整 content-calendar.md，重新选题 |

迭代规则：最多 3 轮，每轮只调一个维度。

### Step 2.5.3: 反馈记忆

用户反馈自动记录到 `feedback-log.json`，下次生成同赛道时自动应用。
→ 详见 `references/design-notes.md` 反馈记忆机制。

---

## Phase 3: 可选 Cron 部署

**仅在 Phase 2.5 测试通过后触发。**

```
测试通过，流水线效果确认 OK ✅

是否需要设置定时自动执行？
- [A] 每日 {时间} 自动推送选题
- [B] 每周 {星期} {时间} 自动推送选题
- [C] 不需要，手动触发即可
```

用户选择后创建 Cron：
```
cronjob action=create
  name: "{赛道名} 每日选题推送"
  schedule: "{用户选择的时间}"
  prompt: "请使用 {赛道英文名} 流水线，采集并推送今日选题"
  deliver: origin
```

---

## 执行指令

```
帮我生成{平台}{垂类}的内容流水线          → 进入 Phase 0
上传竞品截图 + "帮我分析这个账号的赛道"    → 截图诊断模式
"我想做自媒体，不知道做什么赛道好"         → 模糊需求推荐模式（触发资产扫描）
```

---

## 赛道知识库扩展规则

遇到知识库中没有的 `平台 × 垂类` 组合时：
1. 基于已有赛道推理最佳实践
2. 生成时标注"新赛道，需手动校准"
3. 用户确认后，追加到 `references/track-knowledge-base.md`
