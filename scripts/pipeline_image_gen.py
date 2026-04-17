#!/usr/bin/env python3
"""
内容流水线工厂 - 生图 Fallback 脚本 v2
优先级: Nano Banana 2 API → HTML+Puppeteer 渲染 → Pillow 保底排版

用法:
  python3 pipeline_image_gen.py --prompt "小红书穿搭封面" --image /tmp/output.png
  python3 pipeline_image_gen.py --prompt "育儿知识卡片" --image /tmp/out.png --width 1075 --height 1440
  python3 pipeline_image_gen.py --prompt "科技新闻" --image /tmp/out.png --style infographic
  python3 pipeline_image_gen.py --batchfile batch.json --jobs 3

batch.json 格式:
  {"tasks": [{"id": "1", "prompt": "...", "image": "/tmp/1.png"}, ...], "jobs": 3}

--style 选项:
  card         圆角卡片风格（默认）
  infographic  信息图风格，左侧色带+图标列表
  quote        语录/金句风格，大字居中+装饰线

环境变量:
  NANO_API_KEY - Nano Banana 2 API Key (默认使用内置 key)
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
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

# ── 配色方案 ──────────────────────────────────────
COLOR_SCHEMES = {
    "育儿": {
        "name": "暖阳",
        "gradient": ["#FFECD2", "#FCB69F"],
        "primary": "#5D4037",
        "accent": "#FF8A65",
        "card_bg": "rgba(255,255,255,0.85)",
        "tag_bg": "#FFF3E0",
        "tag_color": "#E65100",
        "icon": "🧒",
    },
    "科技": {
        "name": "冷蓝",
        "gradient": ["#0F2027", "#203A43", "#2C5364"],
        "primary": "#E0E0E0",
        "accent": "#00BCD4",
        "card_bg": "rgba(255,255,255,0.08)",
        "tag_bg": "#1A237E",
        "tag_color": "#82B1FF",
        "icon": "💡",
    },
    "玄学": {
        "name": "深紫金",
        "gradient": ["#1a0533", "#2d1b69", "#1a0533"],
        "primary": "#F5E6CC",
        "accent": "#FFD700",
        "card_bg": "rgba(255,215,0,0.06)",
        "tag_bg": "#4A148C",
        "tag_color": "#FFD54F",
        "icon": "🔮",
    },
    "美食": {
        "name": "暖橙",
        "gradient": ["#FFE0B2", "#FF9800"],
        "primary": "#3E2723",
        "accent": "#FF5722",
        "card_bg": "rgba(255,255,255,0.88)",
        "tag_bg": "#FBE9E7",
        "tag_color": "#BF360C",
        "icon": "🍜",
    },
    "健身": {
        "name": "活力绿",
        "gradient": ["#C6FFDD", "#FBD786", "#f7797d"],
        "primary": "#1B5E20",
        "accent": "#4CAF50",
        "card_bg": "rgba(255,255,255,0.88)",
        "tag_bg": "#E8F5E9",
        "tag_color": "#2E7D32",
        "icon": "💪",
    },
    "default": {
        "name": "默认",
        "gradient": ["#667eea", "#764ba2"],
        "primary": "#FFFFFF",
        "accent": "#FF6B6B",
        "card_bg": "rgba(255,255,255,0.12)",
        "tag_bg": "#EDE7F6",
        "tag_color": "#4527A0",
        "icon": "✨",
    },
}

# 扩展关键词映射
KEYWORD_MAP = {
    "育儿": ["育儿", "宝宝", "宝妈", "辅食", "早教", "亲子", "母婴", "带娃", "儿童"],
    "科技": ["科技", "AI", "人工智能", "编程", "数码", "手机", "电脑", "互联网", "技术", "代码"],
    "玄学": ["玄学", "星座", "运势", "塔罗", "风水", "星盘", "水逆", "八字", "占卜"],
    "美食": ["美食", "做饭", "烘焙", "食谱", "下厨", "菜谱", "火锅", "甜品", "料理"],
    "健身": ["健身", "减肥", "瑜伽", "运动", "跑步", "减脂", "增肌", "马甲线", "塑形"],
}


def _detect_theme(prompt):
    """根据 prompt 关键词检测主题配色"""
    for theme, keywords in KEYWORD_MAP.items():
        for kw in keywords:
            if kw in prompt:
                return COLOR_SCHEMES[theme]
    return COLOR_SCHEMES["default"]


def _parse_prompt_structure(prompt):
    """将 prompt 解析为标题+要点+slogan"""
    lines = re.split(r'[;\n；\r]+', prompt)
    lines = [l.strip() for l in lines if l.strip()]

    if len(lines) >= 3:
        title = lines[0]
        points = lines[1:-1]
        slogan = lines[-1]
    elif len(lines) == 2:
        title = lines[0]
        points = []
        slogan = lines[1]
    else:
        text = lines[0] if lines else prompt
        # 尝试按标点分割
        parts = re.split(r'[，,。!！?？]+', text)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) >= 3:
            title = parts[0]
            points = parts[1:-1]
            slogan = parts[-1]
        elif len(parts) == 2:
            title = parts[0]
            points = []
            slogan = parts[1]
        else:
            title = text[:20] + ("..." if len(text) > 20 else "")
            points = _wrap_text(text, 22) if len(text) > 20 else []
            slogan = "AI 生成 · 内容流水线工厂"

    return title, points[:6], slogan


# ── Nano Banana 2 API ────────────────────────────
def try_nano_api(prompt, output_path, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, **kw):
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

    except Exception as e:
        print(f"[Nano] 失败: {e}")
        return False


# ── HTML+Puppeteer 渲染 ──────────────────────────
def _check_puppeteer():
    """检测 npx/puppeteer 是否可用"""
    try:
        r = subprocess.run(["npx", "--version"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            print(f"[HTML] npx 版本: {r.stdout.strip()}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    try:
        r = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            print(f"[HTML] node 版本: {r.stdout.strip()}")
            # node 在但 npx 不在，也可以尝试
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    print("[HTML] node/npx 不可用，跳过 Puppeteer")
    return False


def _build_gradient_css(colors):
    """生成 CSS 渐变"""
    if len(colors) == 2:
        return f"linear-gradient(135deg, {colors[0]} 0%, {colors[1]} 100%)"
    elif len(colors) >= 3:
        stops = ", ".join(f"{c} {i * 100 // (len(colors)-1)}%" for i, c in enumerate(colors))
        return f"linear-gradient(135deg, {stops})"
    return f"linear-gradient(135deg, {colors[0]} 0%, {colors[0]} 100%)"


def _generate_card_html(prompt, width, height, theme):
    """生成 card 风格 HTML"""
    title, points, slogan = _parse_prompt_structure(prompt)
    gradient = _build_gradient_css(theme["gradient"])
    icon = theme["icon"]

    points_html = ""
    for i, pt in enumerate(points):
        points_html += f"""
        <div class="point">
            <span class="point-num">{i+1:02d}</span>
            <span class="point-text">{_html_escape(pt)}</span>
        </div>"""

    if not points_html:
        # 没有要点时显示 prompt 内容
        for line in _wrap_text(prompt, 24)[:6]:
            points_html += f'<div class="point"><span class="point-text">{_html_escape(line)}</span></div>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&display=swap');
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    width: {width}px; height: {height}px;
    background: {gradient};
    font-family: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    display: flex; align-items: center; justify-content: center;
    overflow: hidden;
}}
.container {{
    width: {int(width * 0.85)}px;
    background: {theme["card_bg"]};
    backdrop-filter: blur(20px);
    border-radius: 32px;
    padding: 60px 50px;
    border: 1px solid rgba(255,255,255,0.2);
    box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}}
.icon {{ font-size: 52px; margin-bottom: 20px; }}
.title {{
    font-size: 48px; font-weight: 900;
    color: {theme["primary"]};
    margin-bottom: 12px;
    line-height: 1.3;
    letter-spacing: 1px;
}}
.divider {{
    width: 60px; height: 4px;
    background: {theme["accent"]};
    border-radius: 2px;
    margin: 24px 0 32px;
}}
.points {{ margin-bottom: 40px; }}
.point {{
    display: flex; align-items: flex-start;
    margin-bottom: 20px;
    color: {theme["primary"]};
    font-size: 28px; line-height: 1.6;
    opacity: 0.9;
}}
.point-num {{
    display: inline-flex; align-items: center; justify-content: center;
    min-width: 40px; height: 40px;
    background: {theme["accent"]};
    color: #fff; border-radius: 10px;
    font-size: 18px; font-weight: 700;
    margin-right: 16px; margin-top: 4px;
    flex-shrink: 0;
}}
.point-text {{ flex: 1; }}
.slogan {{
    font-size: 22px;
    color: {theme["primary"]};
    opacity: 0.5;
    text-align: center;
    padding-top: 24px;
    border-top: 1px solid rgba(255,255,255,0.15);
    letter-spacing: 2px;
}}
</style></head>
<body>
<div class="container">
    <div class="icon">{icon}</div>
    <div class="title">{_html_escape(title)}</div>
    <div class="divider"></div>
    <div class="points">{points_html}</div>
    <div class="slogan">{_html_escape(slogan)}</div>
</div>
</body></html>"""


def _generate_infographic_html(prompt, width, height, theme):
    """生成 infographic 风格 HTML — 左侧色带+编号列表"""
    title, points, slogan = _parse_prompt_structure(prompt)
    gradient = _build_gradient_css(theme["gradient"])
    icon = theme["icon"]

    if not points:
        points = _wrap_text(prompt, 22)[:6]

    items_html = ""
    for i, pt in enumerate(points):
        items_html += f"""
        <div class="item">
            <div class="item-icon" style="background:{theme['accent']}">{i+1}</div>
            <div class="item-body">
                <div class="item-text">{_html_escape(pt)}</div>
            </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&display=swap');
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    width: {width}px; height: {height}px;
    background: #fafafa;
    font-family: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    overflow: hidden;
    display: flex;
}}
.sidebar {{
    width: 80px; height: 100%;
    background: {gradient};
    flex-shrink: 0;
}}
.main {{
    flex: 1; padding: 70px 55px;
    display: flex; flex-direction: column;
    justify-content: center;
}}
.tag {{
    display: inline-block;
    background: {theme["tag_bg"]};
    color: {theme["tag_color"]};
    padding: 8px 20px;
    border-radius: 20px;
    font-size: 20px; font-weight: 500;
    margin-bottom: 24px;
    letter-spacing: 1px;
}}
.title {{
    font-size: 52px; font-weight: 900;
    color: #1a1a1a; line-height: 1.3;
    margin-bottom: 48px;
}}
.items {{ margin-bottom: 48px; }}
.item {{
    display: flex; align-items: flex-start;
    margin-bottom: 28px;
}}
.item-icon {{
    width: 48px; height: 48px;
    border-radius: 14px;
    color: #fff; font-weight: 700; font-size: 22px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0; margin-right: 20px; margin-top: 2px;
}}
.item-text {{
    font-size: 28px; color: #333;
    line-height: 1.6;
}}
.footer {{
    display: flex; align-items: center; gap: 12px;
    padding-top: 32px;
    border-top: 2px solid #eee;
}}
.footer-icon {{ font-size: 28px; }}
.footer-text {{ font-size: 20px; color: #999; letter-spacing: 2px; }}
</style></head>
<body>
<div class="sidebar"></div>
<div class="main">
    <div class="tag">{icon} {_html_escape(title[:8])}</div>
    <div class="title">{_html_escape(title)}</div>
    <div class="items">{items_html}</div>
    <div class="footer">
        <span class="footer-icon">📌</span>
        <span class="footer-text">{_html_escape(slogan)}</span>
    </div>
</div>
</body></html>"""


def _generate_quote_html(prompt, width, height, theme):
    """生成 quote 语录风格 HTML — 大字居中+装饰"""
    title, points, slogan = _parse_prompt_structure(prompt)
    gradient = _build_gradient_css(theme["gradient"])
    # For quote style, use the full prompt as the quote text
    quote_text = prompt if len(prompt) <= 60 else title
    if points:
        quote_text = title

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&display=swap');
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    width: {width}px; height: {height}px;
    background: {gradient};
    font-family: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    display: flex; align-items: center; justify-content: center;
    overflow: hidden;
}}
.wrapper {{
    text-align: center;
    padding: 80px;
    max-width: {int(width * 0.88)}px;
}}
.quote-mark {{
    font-size: 120px;
    color: {theme["accent"]};
    opacity: 0.4;
    line-height: 0.6;
    margin-bottom: 30px;
    font-family: Georgia, serif;
}}
.quote {{
    font-size: 56px;
    font-weight: 900;
    color: {theme["primary"]};
    line-height: 1.5;
    margin-bottom: 48px;
    letter-spacing: 2px;
}}
.line {{
    width: 80px; height: 3px;
    background: {theme["accent"]};
    margin: 0 auto 40px;
    border-radius: 2px;
}}
.author {{
    font-size: 24px;
    color: {theme["primary"]};
    opacity: 0.5;
    letter-spacing: 4px;
}}
.deco-top, .deco-bot {{
    position: fixed;
    width: 200px; height: 200px;
    border: 3px solid {theme["accent"]};
    opacity: 0.15;
}}
.deco-top {{ top: 50px; right: 50px; border-radius: 0 30px 0 0; border-left: none; border-bottom: none; }}
.deco-bot {{ bottom: 50px; left: 50px; border-radius: 0 0 0 30px; border-right: none; border-top: none; }}
</style></head>
<body>
<div class="deco-top"></div>
<div class="deco-bot"></div>
<div class="wrapper">
    <div class="quote-mark">"</div>
    <div class="quote">{_html_escape(quote_text)}</div>
    <div class="line"></div>
    <div class="author">{_html_escape(slogan)}</div>
</div>
</body></html>"""


def _html_escape(text):
    """简单 HTML 转义"""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _puppeteer_screenshot(html_path, output_path, width, height):
    """用 puppeteer 对 HTML 文件截图"""
    js_code = f"""
const puppeteer = require('puppeteer');
(async () => {{
    const browser = await puppeteer.launch({{
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
               '--font-render-hinting=none']
    }});
    const page = await browser.newPage();
    await page.setViewport({{ width: {width}, height: {height}, deviceScaleFactor: 2 }});
    await page.goto('file://{html_path}', {{ waitUntil: 'networkidle0', timeout: 30000 }});
    await page.waitForTimeout(500);
    await page.screenshot({{
        path: '{output_path}',
        type: 'png',
        clip: {{ x: 0, y: 0, width: {width}, height: {height} }}
    }});
    await browser.close();
    console.log('SCREENSHOT_OK');
}})();
"""
    # 写入临时 JS 文件
    js_path = html_path.replace(".html", "_screenshot.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(js_code)

    try:
        # 先尝试 npx puppeteer
        r = subprocess.run(
            ["node", js_path],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, "NODE_PATH": _find_node_modules()}
        )
        if "SCREENSHOT_OK" in r.stdout:
            return True
        print(f"[HTML] node 输出: {r.stdout[-200:]}")
        print(f"[HTML] node 错误: {r.stderr[-300:]}")

        # 如果 puppeteer 不在全局，尝试 npx
        r2 = subprocess.run(
            ["npx", "-y", "puppeteer@latest", "--version"],
            capture_output=True, text=True, timeout=60
        )
        if r2.returncode != 0:
            # 尝试安装 puppeteer
            print("[HTML] 尝试 npx puppeteer 安装...")
            subprocess.run(
                ["npm", "install", "puppeteer", "--no-save"],
                capture_output=True, text=True, timeout=120,
                cwd=tempfile.gettempdir()
            )
            r = subprocess.run(
                ["node", js_path],
                capture_output=True, text=True, timeout=60,
                cwd=tempfile.gettempdir()
            )
            if "SCREENSHOT_OK" in r.stdout:
                return True

        return False
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"[HTML] Puppeteer 截图失败: {e}")
        return False
    finally:
        # 清理临时 JS
        try:
            os.unlink(js_path)
        except OSError:
            pass


def _find_node_modules():
    """查找 node_modules 路径"""
    candidates = [
        os.path.expanduser("~/node_modules"),
        "/usr/local/lib/node_modules",
        "/usr/lib/node_modules",
        os.path.join(os.getcwd(), "node_modules"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return ""


def try_html_puppeteer(prompt, output_path, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, style="card"):
    """
    HTML+Puppeteer 方案 — 生成精美信息卡片/信息图。
    需要 node + puppeteer。
    """
    print(f"[HTML] 检测 Puppeteer 环境...")

    if not _check_puppeteer():
        return False

    theme = _detect_theme(prompt)
    print(f"[HTML] 配色方案: {theme['name']} | 风格: {style}")

    # 根据 style 选择 HTML 生成器
    generators = {
        "card": _generate_card_html,
        "infographic": _generate_infographic_html,
        "quote": _generate_quote_html,
    }
    gen_func = generators.get(style, _generate_card_html)
    html_content = gen_func(prompt, width, height, theme)

    # 写入临时 HTML
    tmp_dir = tempfile.mkdtemp(prefix="pipeline_img_")
    html_path = os.path.join(tmp_dir, "card.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"[HTML] 临时 HTML: {html_path}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    ok = _puppeteer_screenshot(html_path, output_path, width, height)

    if ok and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        print(f"[HTML] ✅ Puppeteer 截图成功: {output_path} ({os.path.getsize(output_path)} bytes)")
        # 清理
        try:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass
        return True
    else:
        print("[HTML] Puppeteer 截图失败或文件异常，降级...")
        try:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass
        return False


# ── Pillow 保底 ──────────────────────────────────
def try_pillow(prompt, output_path, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, **kw):
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
        theme = _detect_theme(prompt)
        title, points, slogan = _parse_prompt_structure(prompt)

        # 渐变背景
        grad_colors = theme["gradient"]
        c1 = _hex_to_rgb(grad_colors[0])
        c2 = _hex_to_rgb(grad_colors[-1])

        img = Image.new('RGB', (width, height), color=c1)
        draw = ImageDraw.Draw(img)

        # 绘制渐变
        for y in range(height):
            r = int(c1[0] + (c2[0] - c1[0]) * y / height)
            g = int(c1[1] + (c2[1] - c1[1]) * y / height)
            b = int(c1[2] + (c2[2] - c1[2]) * y / height)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # 字体
        font_large = _get_font(46)
        font_medium = _get_font(30)
        font_small = _get_font(22)

        # 半透明卡片区域（用浅色矩形模拟）
        card_margin = int(width * 0.08)
        card_top = int(height * 0.12)
        card_bottom = int(height * 0.88)
        overlay_color = (255, 255, 255, 30) if "冷" in theme["name"] or "深" in theme["name"] else (255, 255, 255, 200)

        # 用 RGBA 绘制半透明卡片
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rounded_rectangle(
            [card_margin, card_top, width - card_margin, card_bottom],
            radius=32, fill=overlay_color
        )
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img)

        # 文字颜色
        is_dark_bg = any(k in theme["name"] for k in ["冷", "深"])
        text_primary = (255, 255, 255) if is_dark_bg else (40, 40, 40)
        text_secondary = (200, 200, 200) if is_dark_bg else (120, 120, 120)
        accent_rgb = _hex_to_rgb(theme["accent"])

        # 图标
        y_cursor = card_top + 50
        try:
            draw.text((card_margin + 40, y_cursor), theme["icon"],
                      fill=text_primary, font=_get_font(52))
        except Exception:
            pass
        y_cursor += 80

        # 标题
        draw.text((card_margin + 40, y_cursor), title,
                  fill=text_primary, font=font_large)
        y_cursor += 70

        # 分隔线
        draw.rounded_rectangle(
            [card_margin + 40, y_cursor, card_margin + 100, y_cursor + 4],
            radius=2, fill=accent_rgb
        )
        y_cursor += 30

        # 要点
        display_points = points if points else _wrap_text(prompt, 20)[:6]
        for i, pt in enumerate(display_points):
            # 编号圆角方块
            num_x = card_margin + 40
            draw.rounded_rectangle(
                [num_x, y_cursor, num_x + 40, y_cursor + 40],
                radius=10, fill=accent_rgb
            )
            draw.text((num_x + 20, y_cursor + 20), f"{i+1}",
                      fill=(255, 255, 255), font=_get_font(18), anchor="mm")
            # 文字
            draw.text((num_x + 56, y_cursor + 5), pt,
                      fill=text_primary, font=font_medium)
            y_cursor += 60

        # 底部 slogan
        slogan_y = card_bottom - 50
        draw.text((width // 2, slogan_y), f"📌 {slogan}",
                  fill=text_secondary, font=font_small, anchor="mm")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        img.save(output_path, quality=95)
        print(f"[Pillow] ✅ 保底卡片已生成: {output_path}")
        return True

    except Exception as e:
        print(f"[Pillow] 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ── 工具函数 ──────────────────────────────────────
def _hex_to_rgb(hex_color):
    """#RRGGBB → (R, G, B)"""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


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
def generate_image(prompt, output_path, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, style="card"):
    """完整降级链: Nano API → HTML+Puppeteer → Pillow 保底"""
    print(f"=== 内容流水线工厂 - 生图 v2 ===")
    print(f"Prompt: {prompt[:100]}")
    print(f"尺寸: {width}x{height} | 风格: {style}")
    print(f"输出: {output_path}")
    print()

    # 1. Nano API
    print("[1/3] 尝试 Nano Banana 2 API...")
    if try_nano_api(prompt, output_path, width, height):
        return True
    print()

    # 2. HTML+Puppeteer
    print("[2/3] 尝试 HTML+Puppeteer 渲染...")
    if try_html_puppeteer(prompt, output_path, width, height, style):
        return True
    print()

    # 3. Pillow 保底
    print("[3/3] 降级到 Pillow 保底排版...")
    if try_pillow(prompt, output_path, width, height):
        return True

    print("❌ 所有生图方案均失败")
    return False


def _update_timeout(val):
    global REQUEST_TIMEOUT
    REQUEST_TIMEOUT = val


def main():
    import argparse
    parser = argparse.ArgumentParser(description="内容流水线工厂 - 生图 Fallback v2")
    parser.add_argument("--prompt", help="生图提示词")
    parser.add_argument("--image", help="输出路径")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument("--timeout", type=int, default=REQUEST_TIMEOUT)
    parser.add_argument("--style", choices=["card", "infographic", "quote"],
                        default="card", help="渲染风格: card/infographic/quote")
    parser.add_argument("--batchfile", help="JSON 批量任务文件")
    parser.add_argument("--jobs", type=int, default=3, help="并发数")
    args = parser.parse_args()

    _update_timeout(args.timeout)

    if args.batchfile:
        with open(args.batchfile) as f:
            batch = json.load(f)

        tasks = batch.get("tasks", [])
        max_jobs = batch.get("jobs", args.jobs)
        print(f"批量模式: {len(tasks)} 个任务, {max_jobs} 并发")

        from concurrent.futures import ThreadPoolExecutor

        def run_task(task):
            w = task.get("width", args.width)
            h = task.get("height", args.height)
            s = task.get("style", args.style)
            ok = generate_image(task["prompt"], task["image"], w, h, s)
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
        ok = generate_image(args.prompt, args.image, args.width, args.height, args.style)
        sys.exit(0 if ok else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
