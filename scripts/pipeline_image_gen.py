#!/usr/bin/env python3
"""
内容流水线工厂 - 生图 Fallback 脚本
优先级: image_generate (Agent调用) → Nano Banana 2 API → Pillow 保底排版

用法:
  python3 pipeline_image_gen.py --prompt "小红书穿搭封面" --image /tmp/output.png
  python3 pipeline_image_gen.py --prompt "育儿知识卡片" --image /tmp/out.png --width 1075 --height 1440
  python3 pipeline_image_gen.py --batchfile batch.json --jobs 3

batch.json 格式:
  {"tasks": [{"id": "1", "prompt": "...", "image": "/tmp/1.png"}, ...], "jobs": 3}

环境变量:
  NANO_API_KEY - Nano Banana 2 API Key (默认使用内置 key)

注意:
  - image_generate (FLUX 2 Pro) 由 Agent 工具直接调用，本脚本不处理
  - 本脚本处理 Nano API + Pillow 两级降级
  - macOS 用 sips 缩放，Linux 用 Pillow 缩放
"""
import base64
import json
import os
import re
import subprocess
import sys
import time

# ── 配置 ──────────────────────────────────────────
NANO_API_URL = "https://new.apipudding.com/v1/chat/completions"
NANO_API_KEY = os.environ.get(
    "NANO_API_KEY",
    "sk-TV3U1k0yb1dnG6451gNmvQkoJkLcy3TegCRC4I1q2YNKirzX"
)
NANO_MODEL = "[官逆C]Nano banana 2"
DEFAULT_WIDTH = 1075
DEFAULT_HEIGHT = 1440
REQUEST_TIMEOUT = 180


# ── Nano Banana 2 API ────────────────────────────
def try_nano_api(prompt, output_path, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    """
    通过 Nano Banana 2 中转 API 生图。
    返回格式: choices[0].message.content 包含 base64 data URI
    """
    try:
        import requests
    except ImportError:
        print("[Nano] requests 未安装，尝试安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "requests", "-q"],
                       capture_output=True)
        import requests

    print(f"[Nano] 请求生图: {prompt[:80]}...")

    try:
        resp = requests.post(
            NANO_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {NANO_API_KEY}"
            },
            json={
                "model": NANO_MODEL,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=REQUEST_TIMEOUT
        )

        data = resp.json()

        if "error" in data:
            print(f"[Nano] API 错误: {data['error']}")
            return False

        content = data["choices"][0]["message"]["content"]

        # 提取 base64 图片数据
        match = re.search(r'data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)', content)
        if not match:
            print(f"[Nano] 未找到图片数据，返回内容预览: {content[:200]}")
            return False

        image_data = base64.b64decode(match.group(2))
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        with open(output_path, "wb") as f:
            f.write(image_data)

        print(f"[Nano] ✅ 保存成功: {output_path} ({len(image_data)} bytes)")

        # 缩放到目标尺寸
        _resize_image(output_path, width, height)
        return True

    except requests.exceptions.Timeout:
        print(f"[Nano] 超时 ({REQUEST_TIMEOUT}s)")
        return False
    except Exception as e:
        print(f"[Nano] 失败: {e}")
        return False


# ── Pillow 保底 ──────────────────────────────────
def try_pillow(prompt, output_path, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    """
    Pillow 保底方案 — 生成简洁排版的信息卡片。
    不是真正的 AI 生图，但能保证有图可用。
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("[Pillow] 未安装，尝试安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "Pillow", "-q"],
                       capture_output=True)
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            print("[Pillow] 安装失败")
            return False

    try:
        # 配色方案 — 温暖渐变底色
        bg_color = "#FDF6EC"
        primary_color = "#2C2C2C"
        accent_color = "#E8A87C"
        subtitle_color = "#888888"

        img = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)

        # 尝试加载系统字体（按优先级）
        font_large = _get_font(42)
        font_medium = _get_font(28)
        font_small = _get_font(20)

        # ── 顶部装饰条 ──
        draw.rectangle([0, 0, width, 8], fill=accent_color)

        # ── 标题区域 ──
        title_y = height * 0.15
        draw.rounded_rectangle(
            [80, title_y, width - 80, title_y + 120],
            radius=20, fill=primary_color
        )

        # 标题文字（取 prompt 前 20 字）
        title = prompt[:20] + ("..." if len(prompt) > 20 else "")
        draw.text((width // 2, title_y + 60), title,
                  fill="white", font=font_large, anchor="mm")

        # ── 内容区域 — 将 prompt 分行显示 ──
        content_y = title_y + 180
        lines = _wrap_text(prompt, 18)  # 每行约 18 字
        for i, line in enumerate(lines[:8]):  # 最多 8 行
            draw.text((width // 2, content_y + i * 55), line,
                      fill=primary_color, font=font_medium, anchor="mm")

        # ── 底部标注 ──
        draw.text((width // 2, height - 80), "📌 AI 生成 · 内容流水线工厂",
                  fill=subtitle_color, font=font_small, anchor="mm")

        # ── 底部装饰条 ──
        draw.rectangle([0, height - 8, width, height], fill=accent_color)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        img.save(output_path, quality=95)
        print(f"[Pillow] ✅ 保底卡片已生成: {output_path}")
        return True

    except Exception as e:
        print(f"[Pillow] 失败: {e}")
        return False


# ── 工具函数 ──────────────────────────────────────
def _resize_image(path, target_width, target_height):
    """跨平台图片缩放: macOS 用 sips, 其他用 Pillow"""
    import platform

    if platform.system() == "Darwin":
        try:
            r = subprocess.run(["sips", "-g", "pixelHeight", path],
                               capture_output=True, text=True)
            h = int(r.stdout.strip().split()[-1])
            if h != target_height:
                subprocess.run(["sips", "-Z", str(target_height), path],
                               capture_output=True)
                print(f"[Resize] sips 缩放到 {target_height}px 高")
        except Exception as e:
            print(f"[Resize] sips 跳过: {e}")
    else:
        try:
            from PIL import Image
            img = Image.open(path)
            if img.height != target_height:
                ratio = target_height / img.height
                new_w = int(img.width * ratio)
                img = img.resize((new_w, target_height), Image.LANCZOS)
                img.save(path)
                print(f"[Resize] Pillow 缩放到 {new_w}x{target_height}")
        except Exception as e:
            print(f"[Resize] Pillow 跳过: {e}")


def _get_font(size):
    """尝试加载可用字体，找不到就用默认"""
    try:
        from PIL import ImageFont
    except ImportError:
        return None

    # 按优先级尝试字体路径
    font_paths = [
        # macOS
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        # Linux
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue

    # 兜底: 默认字体
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def _wrap_text(text, chars_per_line=18):
    """中文文本自动换行"""
    lines = []
    while text:
        if len(text) <= chars_per_line:
            lines.append(text)
            break
        # 在标点处优先断行
        cut = chars_per_line
        for punct in "，。！？、；：":
            idx = text[:chars_per_line + 2].rfind(punct)
            if idx > chars_per_line // 2:
                cut = idx + 1
                break
        lines.append(text[:cut])
        text = text[cut:]
    return lines


# ── 主流程 ────────────────────────────────────────
def generate_image(prompt, output_path, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    """完整降级链: Nano API → Pillow 保底"""
    print(f"=== 内容流水线工厂 - 生图 ===")
    print(f"Prompt: {prompt[:100]}")
    print(f"尺寸: {width}x{height}")
    print(f"输出: {output_path}")
    print()

    # 1. Nano API
    print("[1/2] 尝试 Nano Banana 2 API...")
    if try_nano_api(prompt, output_path, width, height):
        return True

    print()

    # 2. Pillow 保底
    print("[2/2] 降级到 Pillow 保底排版...")
    if try_pillow(prompt, output_path, width, height):
        return True

    print("❌ 所有生图方案均失败")
    return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="内容流水线工厂 - 生图 Fallback")
    parser.add_argument("--prompt", help="生图提示词")
    parser.add_argument("--image", help="输出路径")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument("--timeout", type=int, default=REQUEST_TIMEOUT)
    parser.add_argument("--batchfile", help="JSON 批量任务文件")
    parser.add_argument("--jobs", type=int, default=3, help="并发数")
    args = parser.parse_args()

    global REQUEST_TIMEOUT
    REQUEST_TIMEOUT = args.timeout

    if args.batchfile:
        # 批量模式
        with open(args.batchfile) as f:
            batch = json.load(f)

        tasks = batch.get("tasks", [])
        max_jobs = batch.get("jobs", args.jobs)
        print(f"批量模式: {len(tasks)} 个任务, {max_jobs} 并发")

        from concurrent.futures import ThreadPoolExecutor

        def run_task(task):
            w = task.get("width", args.width)
            h = task.get("height", args.height)
            ok = generate_image(task["prompt"], task["image"], w, h)
            return task["id"], ok

        results = []
        for i in range(0, len(tasks), max_jobs):
            batch_tasks = tasks[i:i + max_jobs]
            with ThreadPoolExecutor(max_workers=max_jobs) as executor:
                for tid, ok in executor.map(run_task, batch_tasks):
                    results.append((tid, ok))
            if i + max_jobs < len(tasks):
                print("等待 20s (rate limit)...")
                time.sleep(20)

        success = sum(1 for _, ok in results if ok)
        print(f"\n完成: {success}/{len(tasks)} 成功")
        sys.exit(0 if success == len(tasks) else 1)

    elif args.prompt and args.image:
        ok = generate_image(args.prompt, args.image, args.width, args.height)
        sys.exit(0 if ok else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
