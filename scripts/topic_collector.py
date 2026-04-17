#!/usr/bin/env python3
"""
内容流水线工厂 - 选题采集脚本
从多个数据源采集热点话题，按赛道过滤和排序，输出候选选题列表。

数据源（按优先级）:
  1. 6551 API - Twitter/X 热门推文 (需 TWITTER_TOKEN)
  2. 6551 API - OpenNews 新闻聚合 (需 OPENNEWS_TOKEN)
  3. Tavily Search API - 网络搜索 (需 TAVILY_API_KEY, 免费 1000次/月)
  如果 1+2 全部失败且 TAVILY_API_KEY 已配置，自动降级到 Tavily 兜底。

用法:
  # 按赛道采集选题
  python3 topic_collector.py --track xiaohongshu-parenting --limit 10

  # 按关键词采集
  python3 topic_collector.py --keywords "AI工具,ChatGPT,效率" --limit 10

  # 指定数据源
  python3 topic_collector.py --track wechat-metaphysics --source twitter,news

  # 只用 Tavily
  python3 topic_collector.py --track xiaohongshu-ai-tools --source tavily

  # 输出 JSON 格式（方便流水线串联）
  python3 topic_collector.py --track xiaohongshu-ai-tools --format json

环境变量:
  TWITTER_TOKEN   - 6551 Twitter API token
  OPENNEWS_TOKEN  - 6551 News API token
  TAVILY_API_KEY  - Tavily Search API key (申请: https://tavily.com)
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

# ── 配置 ──────────────────────────────────────────
API_BASE = "https://ai.6551.io"
TWITTER_TOKEN = os.environ.get("TWITTER_TOKEN", "")
OPENNEWS_TOKEN = os.environ.get("OPENNEWS_TOKEN", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

# 赛道 → 搜索关键词映射
TRACK_KEYWORDS = {
    # 小红书
    "xiaohongshu-parenting": ["育儿", "早教", "辅食", "宝宝发育", "母婴"],
    "xiaohongshu-ai-tools": ["AI工具", "ChatGPT", "Claude", "AI变现", "AI效率", "AI agent"],
    "xiaohongshu-fashion": ["穿搭", "显瘦", "OOTD", "平替", "时尚趋势"],
    "xiaohongshu-food": ["美食", "食谱", "烘焙", "减脂餐", "快手菜"],
    "xiaohongshu-pet": ["宠物", "猫咪", "狗狗", "萌宠", "养宠"],
    "xiaohongshu-fitness": ["健身", "减脂", "增肌", "体态矫正", "居家训练"],
    "xiaohongshu-career": ["职场", "面试", "升职加薪", "副业", "时间管理"],
    "xiaohongshu-travel": ["旅行", "攻略", "小众目的地", "穷游", "拍照"],
    "xiaohongshu-digital": ["数码测评", "手机推荐", "耳机", "智能家居"],
    "xiaohongshu-home": ["家居", "装修", "收纳", "改造", "软装"],
    # 公众号
    "wechat-metaphysics": ["八字", "风水", "命理", "运势", "生肖", "紫微斗数"],
    "wechat-business-tech": ["AI", "科技", "商业", "创业", "融资", "IPO"],
    "wechat-education": ["教育", "学习方法", "个人成长", "心理学"],
    # 视频号
    "shipinhao-emotional": ["人生感悟", "亲情", "退休生活", "中老年"],
    "shipinhao-knowledge": ["商业思维", "历史", "文化", "人生哲理"],
    # 抖音
    "douyin-knowledge-talk": ["认知升级", "思维模型", "行业揭秘", "干货"],
    "douyin-pet": ["萌宠", "猫猫狗狗", "宠物搞笑"],
    "douyin-fitness": ["跟练", "减脂操", "健身打卡"],
}


# ── Twitter/X 搜索 ───────────────────────────────
def search_twitter(keywords, limit=10):
    """通过 6551 API 搜索 Twitter 热门推文"""
    if not TWITTER_TOKEN:
        print("[Twitter] ⚠️ TWITTER_TOKEN 未设置，跳过")
        return []

    results = []
    query = " OR ".join(keywords[:3])  # API 限制，取前 3 个关键词

    try:
        payload = json.dumps({
            "keywords": query,
            "maxResults": limit,
            "product": "Top"
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{API_BASE}/open/twitter_search",
            data=payload,
            headers={
                "Authorization": f"Bearer {TWITTER_TOKEN}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        tweets = data.get("data", data.get("tweets", []))
        if isinstance(tweets, list):
            for tw in tweets[:limit]:
                text = tw.get("text", tw.get("content", ""))
                likes = tw.get("likes", tw.get("favorite_count", 0))
                user = tw.get("user", tw.get("author", {"screen_name": "unknown"}))
                username = user if isinstance(user, str) else user.get("screen_name", "unknown")

                results.append({
                    "source": "twitter",
                    "title": text[:80] + ("..." if len(text) > 80 else ""),
                    "content": text,
                    "author": username,
                    "engagement": likes,
                    "url": tw.get("url", ""),
                    "collected_at": datetime.now().isoformat()
                })

        print(f"[Twitter] ✅ 采集到 {len(results)} 条")

    except Exception as e:
        print(f"[Twitter] ❌ 失败: {e}")

    return results


# ── OpenNews 搜索 ────────────────────────────────
def search_news(keywords, limit=10):
    """通过 6551 API 搜索新闻"""
    if not OPENNEWS_TOKEN:
        print("[News] ⚠️ OPENNEWS_TOKEN 未设置，跳过")
        return []

    results = []
    query = " OR ".join(keywords[:3])

    try:
        payload = json.dumps({
            "q": query,
            "limit": limit,
            "page": 1
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{API_BASE}/open/news_search",
            data=payload,
            headers={
                "Authorization": f"Bearer {OPENNEWS_TOKEN}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        articles = data.get("data", [])
        if isinstance(articles, list):
            for art in articles[:limit]:
                # 6551 API 字段: text(正文), link(链接), source(来源),
                # aiRating.summary(中文摘要), aiRating.score(评分)
                text = art.get("text", "")
                ai_rating = art.get("aiRating", {})
                cn_summary = ai_rating.get("summary", "")
                en_summary = ai_rating.get("enSummary", "")
                score = ai_rating.get("score", 0)
                source_name = art.get("source", "unknown")
                news_type = art.get("newsType", "")

                # 标题优先用中文摘要，其次英文摘要，最后截取正文
                title = cn_summary or en_summary or text[:80]
                if len(title) > 80:
                    title = title[:80] + "..."

                results.append({
                    "source": f"news/{source_name}",
                    "title": title,
                    "content": text[:500] if text else cn_summary,
                    "author": source_name,
                    "news_type": news_type,
                    "engagement": score,
                    "url": art.get("link", ""),
                    "collected_at": datetime.now().isoformat()
                })

        print(f"[News] ✅ 采集到 {len(results)} 条")

    except Exception as e:
        print(f"[News] ❌ 失败: {e}")

    return results


# ── Tavily 搜索（第三级 fallback）─────────────────
def search_tavily(keywords, limit=10):
    """
    通过 Tavily Search API 搜索热点内容。
    需要用户自行申请 API Key: https://tavily.com
    设置环境变量 TAVILY_API_KEY 即可使用。
    """
    if not TAVILY_API_KEY:
        print("[Tavily] ⚠️ TAVILY_API_KEY 未设置，跳过")
        print("[Tavily] 💡 申请地址: https://tavily.com (免费额度 1000次/月)")
        return []

    results = []
    query = " ".join(keywords[:5])

    try:
        payload = json.dumps({
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic",
            "max_results": limit,
            "include_answer": False
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        for item in data.get("results", [])[:limit]:
            title = item.get("title", "")
            content = item.get("content", "")
            url = item.get("url", "")
            score = item.get("score", 0)

            results.append({
                "source": "tavily",
                "title": title[:80] + ("..." if len(title) > 80 else ""),
                "content": content[:500] if content else title,
                "author": urllib.parse.urlparse(url).netloc if url else "unknown",
                "engagement": int(score * 100),  # 归一化为 0-100
                "url": url,
                "collected_at": datetime.now().isoformat()
            })

        print(f"[Tavily] ✅ 采集到 {len(results)} 条")

    except Exception as e:
        print(f"[Tavily] ❌ 失败: {e}")

    return results


# ── 选题排序与去重 ────────────────────────────────
def deduplicate(topics):
    """基于标题相似度去重"""
    seen = set()
    unique = []
    for t in topics:
        # 简单去重：标题前 20 字
        key = t["title"][:20]
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique


def rank_topics(topics):
    """按互动量排序"""
    return sorted(topics, key=lambda x: x.get("engagement", 0), reverse=True)


# ── 输出格式化 ────────────────────────────────────
def format_text(topics, track=""):
    """人类可读的文本格式"""
    lines = []
    lines.append(f"📋 选题采集结果 | 赛道: {track or '通用'} | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"   共 {len(topics)} 条候选")
    lines.append("=" * 60)

    for i, t in enumerate(topics, 1):
        lines.append(f"\n#{i} [{t['source']}] 互动: {t.get('engagement', '-')}")
        lines.append(f"   标题: {t['title']}")
        if t.get("url"):
            lines.append(f"   链接: {t['url']}")

    return "\n".join(lines)


# ── 主流程 ────────────────────────────────────────
def collect(track=None, keywords=None, sources=None, limit=10):
    """
    主采集函数。

    Args:
        track: 赛道名（如 xiaohongshu-parenting），自动匹配关键词
        keywords: 自定义关键词列表
        sources: 数据源列表 ["twitter", "news"]，默认全部
        limit: 每个源的采集数量

    Returns:
        去重排序后的选题列表
    """
    # 确定关键词
    if keywords:
        kw = keywords if isinstance(keywords, list) else keywords.split(",")
    elif track and track in TRACK_KEYWORDS:
        kw = TRACK_KEYWORDS[track]
    else:
        print(f"⚠️ 未知赛道 '{track}'，请用 --keywords 指定关键词")
        print(f"已知赛道: {', '.join(TRACK_KEYWORDS.keys())}")
        return []

    if sources is None:
        sources = ["twitter", "news", "tavily"]

    print(f"🔍 采集关键词: {', '.join(kw)}")
    print(f"📡 数据源: {', '.join(sources)}")
    print()

    all_topics = []

    if "twitter" in sources:
        all_topics.extend(search_twitter(kw, limit))

    if "news" in sources:
        all_topics.extend(search_news(kw, limit))

    if "tavily" in sources:
        all_topics.extend(search_tavily(kw, limit))

    # 如果主数据源全部失败，自动尝试 Tavily 兜底
    if not all_topics and "tavily" not in sources and TAVILY_API_KEY:
        print("\n⚠️ 主数据源全部为空，自动降级到 Tavily 搜索...")
        all_topics.extend(search_tavily(kw, limit))

    # 去重 + 排序
    all_topics = deduplicate(all_topics)
    all_topics = rank_topics(all_topics)

    return all_topics[:limit]


def main():
    parser = argparse.ArgumentParser(description="内容流水线工厂 - 选题采集")
    parser.add_argument("--track", help="赛道名 (如 xiaohongshu-parenting)")
    parser.add_argument("--keywords", help="自定义关键词，逗号分隔")
    parser.add_argument("--source", default="twitter,news,tavily",
                        help="数据源，逗号分隔 (默认: twitter,news,tavily)")
    parser.add_argument("--limit", type=int, default=10, help="采集数量 (默认: 10)")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="输出格式 (默认: text)")
    parser.add_argument("--output", help="输出文件路径（不指定则打印到 stdout）")
    args = parser.parse_args()

    sources = [s.strip() for s in args.source.split(",")]
    keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else None

    topics = collect(
        track=args.track,
        keywords=keywords,
        sources=sources,
        limit=args.limit
    )

    if not topics:
        print("\n❌ 未采集到任何选题")
        sys.exit(1)

    # 格式化输出
    if args.format == "json":
        output = json.dumps(topics, ensure_ascii=False, indent=2)
    else:
        output = format_text(topics, args.track or "")

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"\n📁 已保存到: {args.output}")
    else:
        print(f"\n{output}")


if __name__ == "__main__":
    main()
