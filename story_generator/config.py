import os
import sys

PERIOD_ORDER = ["morning", "noon", "afternoon", "evening", "night"]

PERIOD_CN = {
    "morning": "早晨",
    "noon": "中午",
    "afternoon": "下午",
    "evening": "傍晚",
    "night": "夜晚"
}

DEFAULT_MODEL = "deepseek-ai/DeepSeek-V3"

API_BASE_URL = "https://api.siliconflow.cn/v1/chat/completions"

DEEPSEEK_API_KEY = ""

MAX_HISTORY_ENTRIES = 10

SUMMARY_MAX_HISTORY = 5

def get_app_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(__file__))

SAVES_BASE_DIR = os.path.join(get_app_dir(), "saves")

_current_save_dir = None

def get_current_save_dir() -> str:
    global _current_save_dir
    return _current_save_dir

def set_current_save_dir(save_dir: str) -> None:
    global _current_save_dir
    _current_save_dir = save_dir

def get_next_save_number() -> int:
    if not os.path.exists(SAVES_BASE_DIR):
        os.makedirs(SAVES_BASE_DIR, exist_ok=True)
        return 1
    
    existing = [d for d in os.listdir(SAVES_BASE_DIR) 
                if os.path.isdir(os.path.join(SAVES_BASE_DIR, d)) and d.startswith("save")]
    
    if not existing:
        return 1
    
    numbers = []
    for name in existing:
        try:
            num = int(name.replace("save", ""))
            numbers.append(num)
        except ValueError:
            continue
    
    return max(numbers) + 1 if numbers else 1

def get_save_dir(save_number: int) -> str:
    return os.path.join(SAVES_BASE_DIR, f"save{save_number}")

def get_save_files(save_dir: str) -> dict:
    return {
        "world_event": os.path.join(save_dir, "world_event.txt"),
        "summary_log": os.path.join(save_dir, "summary_log.txt"),
        "nodes_log": os.path.join(save_dir, "nodes_log.txt"),
        "story_log": os.path.join(save_dir, "story_log.txt"),
        "save": os.path.join(save_dir, "save.json")
    }

def list_all_saves() -> list[dict]:
    if not os.path.exists(SAVES_BASE_DIR):
        return []
    
    saves = []
    for name in sorted(os.listdir(SAVES_BASE_DIR)):
        save_path = os.path.join(SAVES_BASE_DIR, name)
        if os.path.isdir(save_path) and name.startswith("save"):
            save_json = os.path.join(save_path, "save.json")
            info = {"name": name, "path": save_path}
            
            if os.path.exists(save_json):
                try:
                    import json
                    with open(save_json, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    info["time"] = data.get("time", {})
                    info["player"] = data.get("player", {})
                    info["last_saved"] = data.get("last_saved", "")
                except:
                    pass
            
            saves.append(info)
    
    return saves

def get_api_key() -> str:
    if DEEPSEEK_API_KEY:
        return DEEPSEEK_API_KEY
    
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if api_key:
        return api_key
    
    env_path = os.path.join(get_app_dir(), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DEEPSEEK_API_KEY="):
                    return line.split("=", 1)[1].strip()
    
    return ""
