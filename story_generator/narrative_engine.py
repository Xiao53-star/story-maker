import json
import os
import re
from datetime import datetime
from typing import Optional, Generator
from story_generator.config import PERIOD_CN, get_current_save_dir, get_save_files
from story_generator.prompt import build_narrative_prompt
from story_generator.api_client import APIClient


class NarrativeEngine(APIClient):
    def __init__(self, api_key: str, model: str = None):
        super().__init__(api_key, model, "narrative")
        self.event_recorder = None
    
    def set_event_recorder(self, event_recorder) -> None:
        self.event_recorder = event_recorder
    
    def _get_log_files(self) -> dict:
        save_dir = get_current_save_dir()
        if not save_dir:
            return {}
        return get_save_files(save_dir)
    
    def _save_story_log(self, story_text: str, current_time: tuple[int, str]) -> None:
        files = self._get_log_files()
        if not files or "story_log" not in files:
            return
        
        save_dir = get_current_save_dir()
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
        
        day, period = current_time
        period_cn = PERIOD_CN.get(period, period)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(files["story_log"], "a", encoding="utf-8") as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"[{timestamp}] 第{day}天 {period_cn}\n")
            f.write(f"{'='*50}\n")
            f.write(story_text)
            f.write("\n")
    
    def _parse_response(self, response: str) -> tuple[str, Optional[dict]]:
        pattern = r'\[STATE\](.*?)\[/STATE\]'
        match = re.search(pattern, response, re.DOTALL)
        
        if match:
            json_str = match.group(1).strip()
            story_text = response[:match.start()].strip()
            
            try:
                ai_json = json.loads(json_str)
                return story_text, ai_json
            except json.JSONDecodeError:
                return response, None
        
        return response, None
    
    def generate_story(self, world_summary: str, current_time: tuple[int, str],
                       pending_nodes: list[dict], player_input: str,
                       player_identity: str, player_location: str = "") -> tuple[str, Optional[dict]]:
        prompt = build_narrative_prompt(
            world_summary, current_time, pending_nodes, 
            player_input, player_identity, player_location
        )
        
        response = self._call_api(prompt)
        story_text, ai_json = self._parse_response(response)
        
        self._save_story_log(story_text, current_time)
        
        return story_text, ai_json
    
    def generate_story_stream(self, world_summary: str, current_time: tuple[int, str],
                              pending_nodes: list[dict], player_input: str,
                              player_identity: str, player_location: str = "") -> Generator[str, None, tuple[str, Optional[dict]]]:
        prompt = build_narrative_prompt(
            world_summary, current_time, pending_nodes, 
            player_input, player_identity, player_location
        )
        
        full_response = ""
        story_text = ""
        json_started = False
        
        for chunk in self._call_api_stream(prompt):
            full_response += chunk
            
            if json_started:
                continue
            
            if "[" in chunk:
                json_started = True
                idx = chunk.find("[")
                before_json = chunk[:idx]
                if before_json:
                    story_text += before_json
                    yield before_json
                continue
            
            story_text += chunk
            yield chunk
        
        ai_json = None
        pattern = r'\[STATE\](.*?)\[/STATE\]'
        match = re.search(pattern, full_response, re.DOTALL)
        
        if match:
            json_str = match.group(1).strip()
            try:
                ai_json = json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        story_text = story_text.strip()
        self._save_story_log(story_text, current_time)
        
        return story_text, ai_json
