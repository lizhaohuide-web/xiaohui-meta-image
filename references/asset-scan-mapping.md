# 资产扫描 — 分类映射与扫描路径

> 被 SKILL.md Phase 0 Step 0.1.5 引用

## 多平台扫描路径

依次尝试，不报错跳过：

```bash
# 1. Hermes Agent
ls ~/.hermes/skills/ 2>/dev/null

# 2. OpenClaw
ls ~/.openclaw/skills/ 2>/dev/null
ls ~/.openclaw/plugins/ 2>/dev/null
cat ~/.openclaw/config.yaml 2>/dev/null | grep -i skill

# 3. Claude Desktop
ls ~/.claude/skills/ 2>/dev/null
ls ~/.claude/commands/ 2>/dev/null

# 4. Cursor
ls .cursorrules 2>/dev/null
ls .cursor/rules/ 2>/dev/null

# 5. Codex CLI
ls ~/.codex/skills/ 2>/dev/null

# 6. 通用目录
find ~ -maxdepth 3 -type d -name "skills" -o -name "plugins" -o -name "agents" 2>/dev/null | head -20
```

## 语义理解扫描

不只扫目录名做关键词匹配，对每个 skill 目录快速读取 `SKILL.md` 前 5 行，提取 `description` 字段，基于 description 做语义理解判断实际功能。

```bash
for dir in ~/.hermes/skills/*/; do
  head -5 "$dir/SKILL.md" 2>/dev/null | grep -i "description:" | head -1
done
```

## 分类映射表（语义理解 + 关键词）

| 能力类型 | 关键词匹配 + 语义识别 | 对应赛道推荐 |
|---------|----------------------|-------------|
| **玄学命理** | bazi, qimen, ziwei, yinyuan, 八字, 奇门, 紫微, fortune, 命理, 运势 | 公众号玄学、视频号命理 |
| **新媒体工具** | xiaohongshu, wechat, douyin, parenting, content, pipeline, post-to, 发布 | 小红书、公众号、育儿 |
| **AI 工具** | claude, codex, gpt, ai-tool, chatbot, llm, agent, 智能体 | 小红书 AI 工具/变现 |
| **佛教文化** | buddhist, master, monk, 佛教, 高僧, zen, dharma, 禅宗, 净土 | 公众号佛教文化 |
| **知识管理** | obsidian, knowledge, brain, wiki, note, second-brain, 知识库 | 知识付费、读书笔记 |
| **编程开发** | github, python, docker, coding, dev, code-review, git, 编程 | 编程教程、技术博客 |
| **美食生活** | food, recipe, cooking, meal, kitchen, chef, 美食, 食谱 | 小红书美食 |
| **时尚穿搭** | fashion, outfit, style, clothing, wardrobe, 穿搭, 时尚 | 小红书穿搭 |
| **宠物相关** | pet, cat, dog, animal, 宠物, 猫咪, 狗狗 | 小红书宠物、抖音宠物 |
| **健身运动** | fitness, gym, workout, exercise, 健身, 运动, 训练 | 小红书健身、抖音健身 |
| **教育内容** | teach, course, lesson, exam, study, education, 教育, 学习 | 知识付费、在线教育 |
| **医疗健康** | health, medical, wellness, fitness, diet, 健康, 养生 | 健康科普、养生号 |
| **旅行户外** | travel, trip, tourism, journey, 旅行, 旅游, 攻略 | 小红书旅行 |
| **数码科技** | tech, digital, gadget, phone, 数码, 手机, 测评 | 小红书数码 |
| **家居装修** | home, furniture, decor, renovation, 家居, 装修, 改造 | 小红书家居 |

## 资产加成规则

- 用户有 ≥3 个相关 skills → 推荐优先级 +1（工具现成，启动成本低）
- 用户有完整流水线 skill（任何平台的）→ 直接推荐对应赛道
- 用户没有任何内容相关 skills → 推荐门槛最低的赛道（公众号/小红书图文）

## 扫描结果展示格式

```
🔍 已检测到你的资产（跨平台语义扫描）：
  平台：OpenClaw + Hermes（混合环境）
  ✅ 玄学命理（4 个：bazi-skill, qimen-dunjia, ziwei-doushu, yinyuan）
  ✅ 新媒体工具（2 个：baoyu-image-cards, baoyu-format-markdown）
  ⚪ 编程开发（0 个）

💡 推荐已基于你的实际资产加权排序
```

## 推荐展示格式（模糊需求模式）

```
🔍 已检测到你的资产：
  ✅ 玄学命理（4 个 skill：bazi, qimen-dunjia, ziwei-doushu, yinyuan）
  ✅ 新媒体工具（2 个 skill）

💡 为你推荐 3 个赛道（按匹配度排序）：

### 推荐 1：公众号 × 玄学命理 ⭐⭐⭐⭐⭐ 最匹配

**匹配理由**：你已有 4 个玄学 skill，工具现成，零额外配置
**启动成本**：低（直接生成文案 + AI 配图）
**变现路径**：付费测算、私域咨询、课程
**冷启动策略**：前 30 天日更「十二生肖每月运势」

### 推荐 2：小红书 × AI 工具/变现 ⭐⭐⭐

**匹配理由**：你有新媒体工具 skill，但需要额外跟踪 AI 动态
**启动成本**：中（需要持续输入新内容）
**变现路径**：私域引流、知识付费

### 推荐 3：小红书 × 育儿 ⭐⭐

**匹配理由**：你有 parenting-content-pipeline，但需要真实育儿素材
**启动成本**：低（有现成流水线）
**变现路径**：母婴带货、品牌合作
```

## 扫描失败兜底

如果扫描全部失败（用户环境无 skills 目录）：
- 不报错，标注"未检测到已有资产（可能使用了非标准目录）"
- 改为交互式询问："你平时用什么工具或平台？有没有装过什么插件？"
- 仍然基于赛道知识库给出通用推荐
