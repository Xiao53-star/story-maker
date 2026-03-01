import os
import sys
from story_generator.config import get_api_key
from story_generator import settings

def multiline_input(prompt: str) -> str:
    print(prompt)
    lines = []
    while True:
        try:
            line = input()
            if line == "":
                break
            lines.append(line)
        except EOFError:
            break
    return "\n".join(lines)

def load_api_key() -> str:
    api_key = settings.get_api_key()
    
    if api_key:
        return api_key
    
    print("未找到 API Key 配置")
    print("请在设置界面配置 API Key，或设置环境变量 DEEPSEEK_API_KEY，或创建 .env 文件")
    api_key = input().strip()
    if not api_key:
        print("API Key 不能为空")
        sys.exit(1)
    return api_key
