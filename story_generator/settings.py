import json
import os
from typing import Any, Optional
from story_generator.config import get_app_dir

SETTINGS_FILE = os.path.join(get_app_dir(), "settings.json")

DEFAULT_SETTINGS = {
    "api": {
        "api_key": "",
        "api_url": "https://api.siliconflow.cn/v1/chat/completions",
        "model": "deepseek-ai/DeepSeek-V3"
    },
    "narrative": {
        "temperature": 0.8,
        "max_tokens": 800,
        "system_prompt": "你是一个交互式故事生成器，擅长创造引人入胜的叙事体验。"
    },
    "node_parser": {
        "temperature": 0.3,
        "max_tokens": 2000,
        "system_prompt": "你是一个故事大纲解析器，擅长将故事大纲分解为结构化的事件节点。"
    },
    "event_recorder": {
        "temperature": 0.1,
        "max_tokens": 300,
        "system_prompt": "你是一个事件记录员，擅长从故事中提取关键事件并精简记录。"
    },
    "world_outline": {
        "temperature": 0.9,
        "max_tokens": 2000,
        "system_prompt": "你是一个世界大纲生成器，擅长创造完整、引人入胜的故事大纲。"
    },
    "continue_outline": {
        "temperature": 0.9,
        "max_tokens": 2000,
        "system_prompt": "你是一个故事续写专家，擅长基于现有故事内容进行连贯、精彩的续写扩展。"
    }
}

_settings: dict = {}

def load_settings() -> dict:
    global _settings
    
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            _settings = _deep_merge(DEFAULT_SETTINGS.copy(), loaded)
        except (json.JSONDecodeError, IOError):
            _settings = DEFAULT_SETTINGS.copy()
    else:
        _settings = DEFAULT_SETTINGS.copy()
    
    return _settings

def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def save_settings(settings: dict = None) -> None:
    global _settings
    
    if settings is not None:
        _settings = settings
    
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(_settings, f, ensure_ascii=False, indent=2)

def get_settings() -> dict:
    global _settings
    if not _settings:
        load_settings()
    return _settings

def get_api_key() -> str:
    settings = get_settings()
    api_key = settings.get("api", {}).get("api_key", "")
    if api_key:
        return api_key
    
    from story_generator.config import get_api_key as get_default_key
    return get_default_key()

def get_api_url() -> str:
    settings = get_settings()
    return settings.get("api", {}).get("api_url", DEFAULT_SETTINGS["api"]["api_url"])

def get_model() -> str:
    settings = get_settings()
    return settings.get("api", {}).get("model", DEFAULT_SETTINGS["api"]["model"])

def get_narrative_config() -> dict:
    settings = get_settings()
    return settings.get("narrative", DEFAULT_SETTINGS["narrative"])

def get_node_parser_config() -> dict:
    settings = get_settings()
    return settings.get("node_parser", DEFAULT_SETTINGS["node_parser"])

def get_event_recorder_config() -> dict:
    settings = get_settings()
    return settings.get("event_recorder", DEFAULT_SETTINGS["event_recorder"])

def get_world_outline_config() -> dict:
    settings = get_settings()
    return settings.get("world_outline", DEFAULT_SETTINGS["world_outline"])

def get_continue_outline_config() -> dict:
    settings = get_settings()
    return settings.get("continue_outline", DEFAULT_SETTINGS["continue_outline"])

def update_api_settings(api_key: str = None, api_url: str = None, model: str = None) -> None:
    settings = get_settings()
    # 始终更新所有字段，包括空字符串
    settings.setdefault("api", {})["api_key"] = api_key if api_key is not None else ""
    settings.setdefault("api", {})["api_url"] = api_url if api_url is not None else ""
    settings.setdefault("api", {})["model"] = model if model is not None else ""
    save_settings()

def update_narrative_config(temperature: float = None, max_tokens: int = None, 
                            system_prompt: str = None) -> None:
    settings = get_settings()
    if temperature is not None:
        settings.setdefault("narrative", {})["temperature"] = temperature
    if max_tokens is not None:
        settings.setdefault("narrative", {})["max_tokens"] = max_tokens
    if system_prompt is not None:
        settings.setdefault("narrative", {})["system_prompt"] = system_prompt
    save_settings()

def update_node_parser_config(temperature: float = None, max_tokens: int = None,
                              system_prompt: str = None) -> None:
    settings = get_settings()
    if temperature is not None:
        settings.setdefault("node_parser", {})["temperature"] = temperature
    if max_tokens is not None:
        settings.setdefault("node_parser", {})["max_tokens"] = max_tokens
    if system_prompt is not None:
        settings.setdefault("node_parser", {})["system_prompt"] = system_prompt
    save_settings()

def update_event_recorder_config(temperature: float = None, max_tokens: int = None,
                                 system_prompt: str = None) -> None:
    settings = get_settings()
    if temperature is not None:
        settings.setdefault("event_recorder", {})["temperature"] = temperature
    if max_tokens is not None:
        settings.setdefault("event_recorder", {})["max_tokens"] = max_tokens
    if system_prompt is not None:
        settings.setdefault("event_recorder", {})["system_prompt"] = system_prompt
    save_settings()

def update_world_outline_config(temperature: float = None, max_tokens: int = None,
                                 system_prompt: str = None) -> None:
    settings = get_settings()
    if temperature is not None:
        settings.setdefault("world_outline", {})["temperature"] = temperature
    if max_tokens is not None:
        settings.setdefault("world_outline", {})["max_tokens"] = max_tokens
    if system_prompt is not None:
        settings.setdefault("world_outline", {})["system_prompt"] = system_prompt
    save_settings()

def update_continue_outline_config(temperature: float = None, max_tokens: int = None,
                                    system_prompt: str = None) -> None:
    settings = get_settings()
    if temperature is not None:
        settings.setdefault("continue_outline", {})["temperature"] = temperature
    if max_tokens is not None:
        settings.setdefault("continue_outline", {})["max_tokens"] = max_tokens
    if system_prompt is not None:
        settings.setdefault("continue_outline", {})["system_prompt"] = system_prompt
    save_settings()

def reset_to_defaults() -> dict:
    global _settings
    _settings = DEFAULT_SETTINGS.copy()
    save_settings()
    return _settings

def reset_api_to_defaults() -> dict:
    settings = get_settings()
    settings["api"] = DEFAULT_SETTINGS["api"].copy()
    save_settings()
    return settings
