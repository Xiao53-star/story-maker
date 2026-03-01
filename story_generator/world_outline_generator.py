import json
import re
from typing import Generator, List, Dict
from story_generator.config import PERIOD_CN
from story_generator.prompt import (
    build_world_outline_prompt, 
    build_continue_outline_prompt,
    WORLD_OUTLINE_SYSTEM_PROMPT
)
from story_generator.api_client import APIClient
from story_generator import settings


class WorldOutlineGenerator(APIClient):
    def __init__(self, api_key: str, model: str = None):
        super().__init__(api_key, model, "world_outline")
        self._continue_client: APIClient = None
    
    def _get_continue_client(self) -> APIClient:
        if self._continue_client is None:
            self._continue_client = APIClient(self.api_key, self.model, "continue_outline")
        return self._continue_client
    
    def generate_outline(self, user_input: str = "", identity: str = "", goal: str = "") -> str:
        prompt = build_world_outline_prompt(user_input, identity, goal)
        return self._call_api(prompt)
    
    def generate_outline_stream(self, user_input: str = "", identity: str = "", goal: str = "") -> Generator[str, None, None]:
        prompt = build_world_outline_prompt(user_input, identity, goal)
        return self._call_api_stream(prompt)
    
    def generate_continue_outline(self, world_description: str, history: List[Dict],
                                   completed_nodes: List[Dict], current_time: tuple,
                                   player_location: str) -> str:
        history_summary = self._format_history(history)
        completed_nodes_str = self._format_completed_nodes(completed_nodes)
        current_day, current_period = current_time
        period_cn = PERIOD_CN.get(current_period, current_period)
        
        prompt = build_continue_outline_prompt(
            world_description=world_description,
            history_summary=history_summary,
            completed_nodes=completed_nodes_str,
            current_day=current_day,
            current_period=period_cn,
            player_location=player_location
        )
        return self._get_continue_client()._call_api(prompt)
    
    def generate_continue_outline_stream(self, world_description: str, history: List[Dict],
                                          completed_nodes: List[Dict], current_time: tuple,
                                          player_location: str) -> Generator[str, None, None]:
        history_summary = self._format_history(history)
        completed_nodes_str = self._format_completed_nodes(completed_nodes)
        current_day, current_period = current_time
        period_cn = PERIOD_CN.get(current_period, current_period)
        
        prompt = build_continue_outline_prompt(
            world_description=world_description,
            history_summary=history_summary,
            completed_nodes=completed_nodes_str,
            current_day=current_day,
            current_period=period_cn,
            player_location=player_location
        )
        return self._get_continue_client()._call_api_stream(prompt)
    
    def _format_history(self, history: List[Dict]) -> str:
        if not history:
            return "暂无历史事件"
        lines = []
        for item in history[-10:]:
            time_str = item.get("time", "未知时间")
            event = item.get("event", "未知事件")
            lines.append(f"- {time_str}：{event}")
        return "\n".join(lines)
    
    def _format_completed_nodes(self, nodes: List[Dict]) -> str:
        if not nodes:
            return "暂无已完成节点"
        lines = []
        for node in nodes:
            trigger_time = node.get("trigger_time", {})
            day = trigger_time.get("day", "?")
            period = trigger_time.get("period", "?")
            period_cn = PERIOD_CN.get(period, period)
            name = node.get("name", "未知事件")
            desc = node.get("description", "")
            lines.append(f"- 第{day}天{period_cn}：{name} - {desc}")
        return "\n".join(lines)
    
    def parse_outline_to_nodes(self, outline_text: str) -> List[Dict]:
        nodes = []
        lines = outline_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            match = re.match(r'第(\d+)天(早晨|中午|下午|傍晚|夜晚)[：:]\s*(.+)', line)
            if match:
                day = int(match.group(1))
                period_cn = match.group(2)
                description = match.group(3).strip()
                
                period_map = {v: k for k, v in PERIOD_CN.items()}
                period = period_map.get(period_cn, "morning")
                
                nodes.append({
                    "name": description[:30] if len(description) > 30 else description,
                    "trigger_time": {
                        "day": day,
                        "period": period
                    },
                    "description": description,
                    "triggered": False
                })
        
        return nodes
    
    def parse_continue_outline_to_nodes(self, outline_text: str, start_day: int, start_period: str) -> List[Dict]:
        nodes = []
        lines = outline_text.split('\n')
        
        period_order = ["morning", "noon", "afternoon", "evening", "night"]
        start_idx = period_order.index(start_period) if start_period in period_order else 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            match = re.match(r'第(\d+)天(早晨|中午|下午|傍晚|夜晚)[：:]\s*(.+)', line)
            if match:
                day = int(match.group(1))
                period_cn = match.group(2)
                description = match.group(3).strip()
                
                period_map = {v: k for k, v in PERIOD_CN.items()}
                period = period_map.get(period_cn, "morning")
                
                nodes.append({
                    "name": description[:30] if len(description) > 30 else description,
                    "trigger_time": {
                        "day": day,
                        "period": period
                    },
                    "description": description,
                    "triggered": False
                })
        
        return nodes
    
    def extract_world_info(self, outline_text: str) -> Dict[str, str]:
        info = {
            "world_description": "",
            "player_identity": "",
            "player_goal": ""
        }
        
        world_match = re.search(r'【世界观】\s*(.+?)(?=【|$)', outline_text, re.DOTALL)
        if world_match:
            info["world_description"] = world_match.group(1).strip()
        
        player_match = re.search(r'【主角】\s*(.+?)(?=【|$)', outline_text, re.DOTALL)
        if player_match:
            info["player_identity"] = player_match.group(1).strip()
        
        goal_match = re.search(r'【核心目标】\s*(.+?)(?=【|$)', outline_text, re.DOTALL)
        if goal_match:
            info["player_goal"] = goal_match.group(1).strip()
        
        return info
