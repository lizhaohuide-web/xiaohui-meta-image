#!/usr/bin/env python3
"""
feedback-log.json 归档脚本
- 超过 90 天的 track-scope 反馈 → 移入 feedback-archive.json
- global-scope 反馈永久保留（不归档）
- 可通过 --days 参数自定义归档阈值

用法:
  python3 feedback_archive.py                    # 默认归档 90 天前的 track 反馈
  python3 feedback_archive.py --days 60          # 归档 60 天前的
  python3 feedback_archive.py --dry-run          # 预览，不实际写入
"""
import argparse
import json
import os
from datetime import datetime, timedelta

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(SKILL_DIR, "feedback-log.json")
ARCHIVE_PATH = os.path.join(SKILL_DIR, "feedback-archive.json")


def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="归档过期的 feedback-log 条目")
    parser.add_argument("--days", type=int, default=90, help="归档阈值天数 (默认: 90)")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写入文件")
    args = parser.parse_args()

    cutoff = datetime.now() - timedelta(days=args.days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    log = load_json(LOG_PATH)
    archive = load_json(ARCHIVE_PATH)

    if not log:
        print("📭 feedback-log.json 为空，无需归档")
        return

    keep = []
    to_archive = []

    for entry in log:
        entry_date = entry.get("date", "9999-99-99")
        scope = entry.get("scope", "track")

        # global scope 永不归档
        if scope == "global":
            keep.append(entry)
            continue

        # track scope 超过阈值 → 归档
        if entry_date < cutoff_str:
            entry["archived_at"] = datetime.now().strftime("%Y-%m-%d")
            to_archive.append(entry)
        else:
            keep.append(entry)

    print(f"📊 feedback-log 统计:")
    print(f"   总条目: {len(log)}")
    print(f"   保留: {len(keep)} (global: {sum(1 for e in keep if e.get('scope') == 'global')}, "
          f"近期 track: {sum(1 for e in keep if e.get('scope') != 'global')})")
    print(f"   归档: {len(to_archive)} (超过 {args.days} 天的 track-scope)")
    print(f"   截止日期: {cutoff_str}")

    if not to_archive:
        print("\n✅ 没有需要归档的条目")
        return

    if args.dry_run:
        print("\n🔍 [DRY RUN] 以下条目将被归档:")
        for entry in to_archive:
            print(f"   - [{entry['date']}] {entry.get('track', '?')}: {entry.get('feedback', '?')}")
        return

    archive.extend(to_archive)
    save_json(LOG_PATH, keep)
    save_json(ARCHIVE_PATH, archive)

    print(f"\n✅ 已归档 {len(to_archive)} 条到 feedback-archive.json")
    print(f"   feedback-log.json: {len(log)} → {len(keep)} 条")
    print(f"   feedback-archive.json: {len(archive)} 条")


if __name__ == "__main__":
    main()
