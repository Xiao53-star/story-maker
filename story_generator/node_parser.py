import json
import os
import re
from datetime import datetime
from typing import Optional
from story_generator.config import PERIOD_ORDER, get_current_save_dir, get_save_files
from story_generator.prompt import build_node_parser_prompt
from story_generator.api_client import APIClient


class NodeParser(APIClient):
    def __init__(self, api_key: str, model: str = None):
        super().__init__(api_key, model, "node_parser")
    
    def _get_nodes_log_file(self) -> str:
        save_dir = get_current_save_dir()
        if not save_dir:
            return ""
        files = get_save_files(save_dir)
        return files.get("nodes_log", "")
    
    def _save_nodes_log(self, outline: str, nodes: list[dict]) -> None:
        nodes_file = self._get_nodes_log_file()
        if not nodes_file:
            return
        
        save_dir = get_current_save_dir()
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(nodes_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"[{timestamp}] 大纲解析\n")
            f.write(f"{'='*50}\n")
            f.write(f"原始大纲：\n{outline}\n\n")
            f.write(f"解析结果：\n")
            f.write(json.dumps(nodes, ensure_ascii=False, indent=2))
            f.write("\n")
    
    def _extract_json(self, response: str) -> Optional[list]:
        response = response.strip()
        
        json_patterns = [
            r'```json\s*([\s\S]*?)\s*```',
            r'```\s*([\s\S]*?)\s*```',
            r'(\[[\s\S]*\])',
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, response)
            if match:
                json_str = match.group(1).strip()
                try:
                    result = json.loads(json_str)
                    if isinstance(result, list):
                        return result
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def _validate_node(self, node: dict) -> bool:
        if not isinstance(node, dict):
            return False
        if "name" not in node or "description" not in node:
            return False
        
        trigger_time = node.get("trigger_time", {})
        if not isinstance(trigger_time, dict):
            return False
        if "day" not in trigger_time or "period" not in trigger_time:
            return False
        if trigger_time["period"] not in PERIOD_ORDER:
            return False
        
        return True
    
    def parse_outline(self, user_input: str) -> list[dict]:
        if not user_input.strip():
            return []
        
        prompt = build_node_parser_prompt(user_input, PERIOD_ORDER)
        response = self._call_api(prompt)
        
        nodes = self._extract_json(response)
        if not nodes:
            print(f"警告：无法解析节点，API 返回格式错误")
            print(f"API 原始响应: {response[:500]}...")
            return []
        
        valid_nodes = []
        for node in nodes:
            if self._validate_node(node):
                valid_nodes.append({
                    "name": node["name"],
                    "trigger_time": node["trigger_time"],
                    "description": node["description"]
                })
            else:
                print(f"警告：节点格式无效，已跳过: {node.get('name', '未知')}")
        
        if valid_nodes:
            self._save_nodes_log(user_input, valid_nodes)
        
        return valid_nodes
