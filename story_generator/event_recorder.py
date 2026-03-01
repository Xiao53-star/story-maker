import os
from story_generator.config import PERIOD_CN, get_current_save_dir, get_save_files
from story_generator.prompt import EVENT_RECORDER_PROMPT_TEMPLATE
from story_generator.api_client import APIClient


class EventRecorder(APIClient):
    def __init__(self, api_key: str, model: str = None):
        super().__init__(api_key, model, "event_recorder")
    
    def _get_event_file(self) -> str:
        save_dir = get_current_save_dir()
        if not save_dir:
            return ""
        files = get_save_files(save_dir)
        return files.get("world_event", "")
    
    def record_event(self, story_text: str, current_time: tuple[int, str], player_location: str = "") -> str:
        event_file = self._get_event_file()
        if not event_file:
            return ""
        
        save_dir = get_current_save_dir()
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
        
        day, period = current_time
        period_cn = PERIOD_CN.get(period, period)
        
        prompt = EVENT_RECORDER_PROMPT_TEMPLATE.format(
            day=day,
            period_cn=period_cn,
            story_text=story_text[:1000]
        )
        
        event_summary = self._call_api(prompt).strip()
        
        location_str = f"[{player_location}] " if player_location else ""
        with open(event_file, "a", encoding="utf-8") as f:
            f.write(f"第{day}天{period_cn}：{location_str}{event_summary}\n")
        
        return event_summary
    
    def get_all_events(self) -> str:
        event_file = self._get_event_file()
        if not event_file or not os.path.exists(event_file):
            return ""
        
        with open(event_file, "r", encoding="utf-8") as f:
            return f.read()
    
    def get_recent_events(self, max_lines: int = 20) -> str:
        event_file = self._get_event_file()
        if not event_file or not os.path.exists(event_file):
            return ""
        
        with open(event_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        recent_lines = lines[-max_lines:] if len(lines) > max_lines else lines
        return "".join(recent_lines)
