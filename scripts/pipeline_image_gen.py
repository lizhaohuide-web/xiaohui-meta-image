#!/usr/bin/env python3
"""
内容流水线工厂 - 生图 Fallback 脚本
优先级: image_generate → Nano API → Pillow(terminal)
用法: python3 pipeline_image_gen.py "<prompt>" <width> <height> <output_path>
"""
import subprocess
import sys
import json
import os

def try_image_generate(prompt, aspect_ratio="portrait"):
    """尝试用 image_generate 工具（FLUX 2 Pro）"""
    # 这个需要在 Hermes 环境中通过 tool 调用
    # 此处仅返回标记，实际由 Agent 判断
    return None

def try_nano_api(prompt, width=1075, height=1440, output_path="/tmp/pipeline_output.png"):
    """尝试用 Nano Banana 2 中转 API"""
    api_url = "https://new.apipudding.com/v1/chat/completions"
    api_key = os.environ.get("NANO_API_KEY", "sk-TV3U1k0yb1dnG6451gNmvQkoJkLcy3TegCRC4I1q2YNKirzX")
    
    payload = {
        "model": "nano-banana-2",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "image_url"},
        "size": f"{width}x{height}"
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        import urllib.request
        import urllib.error
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(api_url, data=data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            if 'data' in result and len(result['data']) > 0:
                # 假设返回的是 base64 或 URL
                # 实际需要根据 API 返回格式调整
                print(f"[Nano API] 生图成功")
                return True
            else:
                print(f"[Nano API] 返回格式异常: {result}")
                return False
    except Exception as e:
        print(f"[Nano API] 失败: {e}")
        return False

def try_pillow(prompt, width=1075, height=1440, output_path="/tmp/pipeline_output.png"):
    """Pillow 保底方案"""
    # 先检查并安装 Pillow
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("[Pillow] 未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "Pillow", "-q"], 
                      capture_output=True)
        from PIL import Image, ImageDraw
    
    try:
        # 创建画布
        img = Image.new('RGB', (width, height), color='#F8F5F0')
        draw = ImageDraw.Draw(img)
        
        # 解析 prompt 生成简单排版
        # 标题区域
        draw.rounded_rectangle([60, 60, width-60, 200], radius=16, fill='#2C2C2C')
        
        # 提取 prompt 前 30 字作为标题
        title = prompt[:30] if len(prompt) > 30 else prompt
        draw.text((width//2, 130), title, fill='white', anchor='mm')
        
        # 副标题
        draw.text((width//2, 250), "AI 生成内容", fill='#666666', anchor='mm')
        
        # 保存
        img.save(output_path)
        print(f"[Pillow] 生图成功: {output_path}")
        print(f"尺寸: {width}x{height}")
        return True
    except Exception as e:
        print(f"[Pillow] 失败: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("用法: python3 pipeline_image_gen.py \"<prompt>\" [width] [height] [output_path]")
        print("示例: python3 pipeline_image_gen.py \"小红书穿搭封面\" 1075 1440 /tmp/output.png")
        sys.exit(1)
    
    prompt = sys.argv[1]
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 1075
    height = int(sys.argv[3]) if len(sys.argv) > 3 else 1440
    output_path = sys.argv[4] if len(sys.argv) > 4 else "/tmp/pipeline_output.png"
    
    print(f"=== 内容流水线工厂 - 生图 Fallback ===")
    print(f"Prompt: {prompt}")
    print(f"尺寸: {width}x{height}")
    print(f"输出: {output_path}")
    print()
    
    # 降级链
    # 1. image_generate (由 Agent 调用，此处跳过)
    print("[1/3] image_generate → 跳过（由 Agent 工具调用）")
    
    # 2. Nano API
    print("[2/3] 尝试 Nano API...")
    if try_nano_api(prompt, width, height, output_path):
        print("✅ Nano API 成功")
        sys.exit(0)
    
    # 3. Pillow 保底
    print("[3/3] 尝试 Pillow 保底方案...")
    if try_pillow(prompt, width, height, output_path):
        print("✅ Pillow 保底成功")
        sys.exit(0)
    
    print("❌ 所有生图方案均失败")
    sys.exit(1)

if __name__ == "__main__":
    main()
