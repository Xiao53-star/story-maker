import json
import os
import shutil
from datetime import datetime
from typing import Optional
from story_generator.config import (
    PERIOD_ORDER, PERIOD_CN, MAX_HISTORY_ENTRIES, SUMMARY_MAX_HISTORY,
    get_current_save_dir, set_current_save_dir, get_next_save_number,
    get_save_dir, get_save_files, list_all_saves
)

class TimeManager:
    def __init__(self, day: int = 1, period: str = "morning"):
        self.day = day
        self.period = period
        self.period_order = PERIOD_ORDER
    
    def advance(self, periods: int = 1) -> None:
        current_idx = self.period_order.index(self.period)
        current_idx += periods
        while current_idx >= len(self.period_order):
            current_idx -= len(self.period_order)
            self.day += 1
        self.period = self.period_order[current_idx]
    
    def set(self, day: int, period: str) -> None:
        if period not in self.period_order:
            raise ValueError(f"Invalid period: {period}")
        self.day = day
        self.period = period
    
    def get(self) -> tuple[int, str]:
        return (self.day, self.period)
    
    def to_dict(self) -> dict:
        return {"day": self.day, "period": self.period}
    
    @classmethod
    def from_dict(cls, data: dict) -> "TimeManager":
        return cls(day=data.get("day", 1), period=data.get("period", "morning"))


class NodeManager:
    def __init__(self):
        self.nodes: list[dict] = []
    
    def load_nodes(self, nodes: list[dict]) -> None:
        self.nodes = nodes
    
    def add_node(self, node: dict) -> int:
        node_id = max([n.get("id", 0) for n in self.nodes], default=0) + 1
        node["id"] = node_id
        if "triggered" not in node:
            node["triggered"] = False
        self.nodes.append(node)
        return node_id
    
    def check_nodes(self, current_time: tuple[int, str]) -> list[dict]:
        current_day, current_period = current_time
        pending = []
        
        for node in self.nodes:
            if node.get("triggered", False):
                continue
            
            trigger_time = node.get("trigger_time", {})
            trigger_day = trigger_time.get("day", 1)
            trigger_period = trigger_time.get("period", "morning")
            
            if trigger_day == current_day and trigger_period == current_period:
                pending.append(node)
        
        return pending
    
    def get_nodes_in_range(self, from_time: tuple[int, str], to_time: tuple[int, str]) -> list[dict]:
        from_day, from_period = from_time
        to_day, to_period = to_time
        from_idx = PERIOD_ORDER.index(from_period)
        to_idx = PERIOD_ORDER.index(to_period)
        pending = []
        
        for node in self.nodes:
            if node.get("triggered", False):
                continue
            
            trigger_time = node.get("trigger_time", {})
            trigger_day = trigger_time.get("day", 1)
            trigger_period = trigger_time.get("period", "morning")
            trigger_idx = PERIOD_ORDER.index(trigger_period)
            
            if trigger_day < from_day:
                pending.append(node)
            elif trigger_day == from_day and trigger_idx <= from_idx:
                pending.append(node)
            elif from_day < trigger_day < to_day:
                pending.append(node)
            elif trigger_day == to_day and trigger_idx <= to_idx:
                pending.append(node)
        
        return pending
    
    def mark_triggered(self, nodes: list[dict]) -> None:
        node_ids = {n.get("id") for n in nodes}
        for node in self.nodes:
            if node.get("id") in node_ids:
                node["triggered"] = True
    
    def mark_all_in_range_triggered(self, from_time: tuple[int, str], to_time: tuple[int, str]) -> None:
        nodes = self.get_nodes_in_range(from_time, to_time)
        self.mark_triggered(nodes)
    
    def to_list(self) -> list[dict]:
        return self.nodes
    
    @classmethod
    def from_list(cls, nodes: list[dict]) -> "NodeManager":
        nm = cls()
        nm.nodes = nodes
        return nm


class StateManager:
    def __init__(self):
        self.time_mgr = TimeManager()
        self.node_mgr = NodeManager()
        self.data = self._get_default_data()
        self.save_number = None
    
    def _get_default_data(self) -> dict:
        return {
            "world_description": "",
            "player": {
                "identity": "",
                "goal": "",
                "location": "",
                "inventory": [],
                "stats": {"health": 100, "money": 50}
            },
            "characters": {},
            "factions": {},
            "locations": {},
            "history": [],
            "time": self.time_mgr.to_dict(),
            "nodes": [],
            "last_saved": None
        }
    
    def new_save(self) -> int:
        save_number = get_next_save_number()
        save_dir = get_save_dir(save_number)
        os.makedirs(save_dir, exist_ok=True)
        
        self.save_number = save_number
        set_current_save_dir(save_dir)
        
        self._save_all_files()
        
        return save_number
    
    def load_save(self, save_number: int) -> bool:
        save_dir = get_save_dir(save_number)
        files = get_save_files(save_dir)
        
        if not os.path.exists(files["save"]):
            return False
        
        with open(files["save"], "r", encoding="utf-8") as f:
            self.data = json.load(f)
        
        self.time_mgr = TimeManager.from_dict(self.data.get("time", {}))
        self.node_mgr = NodeManager.from_list(self.data.get("nodes", []))
        self.save_number = save_number
        set_current_save_dir(save_dir)
        
        return True
    
    def save_current(self) -> None:
        if self.save_number is None:
            self.new_save()
        else:
            self._save_all_files()
    
    def _save_all_files(self) -> None:
        save_dir = get_current_save_dir()
        if not save_dir:
            return
        
        files = get_save_files(save_dir)
        os.makedirs(save_dir, exist_ok=True)
        
        self.data["time"] = self.time_mgr.to_dict()
        self.data["nodes"] = self.node_mgr.to_list()
        self.data["last_saved"] = datetime.now().isoformat()
        
        with open(files["save"], "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def get_save_files_paths(self) -> dict:
        save_dir = get_current_save_dir()
        if not save_dir:
            return {}
        return get_save_files(save_dir)
    
    def update_from_ai_response(self, ai_json: dict) -> None:
        if not ai_json:
            return
        
        if "new_characters" in ai_json:
            for char in ai_json["new_characters"]:
                name = char.get("name", "未知角色")
                self.data["characters"][name] = {
                    "location": char.get("location", ""),
                    "attitude": char.get("attitude", 0),
                    "status": char.get("status", "正常")
                }
        
        if "character_changes" in ai_json:
            for char_name, changes in ai_json["character_changes"].items():
                if char_name in self.data["characters"]:
                    if "attitude" in changes:
                        current = self.data["characters"][char_name].get("attitude", 0)
                        self.data["characters"][char_name]["attitude"] = current + changes["attitude"]
                    if "location" in changes:
                        self.data["characters"][char_name]["location"] = changes["location"]
        
        if "location_changes" in ai_json:
            for loc_name, changes in ai_json["location_changes"].items():
                if loc_name not in self.data["locations"]:
                    self.data["locations"][loc_name] = {"description": "", "status": "正常"}
                if "status" in changes:
                    self.data["locations"][loc_name]["status"] = changes["status"]
        
        if "player_changes" in ai_json:
            pc = ai_json["player_changes"]
            if "inventory" in pc:
                inv_changes = pc["inventory"]
                if "添加" in inv_changes:
                    self.data["player"]["inventory"].extend(inv_changes["添加"])
                if "移除" in inv_changes:
                    for item in inv_changes["移除"]:
                        if item in self.data["player"]["inventory"]:
                            self.data["player"]["inventory"].remove(item)
            if "location" in pc:
                self.data["player"]["location"] = pc["location"]
        
        if "history_entry" in ai_json:
            entry = ai_json["history_entry"][:100]
            time_str = f"第{self.time_mgr.day}天{PERIOD_CN.get(self.time_mgr.period, self.time_mgr.period)}"
            self.data["history"].append({"time": time_str, "event": entry})
            if len(self.data["history"]) > MAX_HISTORY_ENTRIES:
                self.data["history"] = self.data["history"][-MAX_HISTORY_ENTRIES:]
    
    def get_world_summary(self) -> str:
        parts = []
        
        world_description = self.data.get("world_description", "")
        if world_description:
            parts.append(f"世界观：{world_description}")
        
        player = self.data.get("player", {})
        identity = player.get("identity", "未知身份")
        location = player.get("location", "未知位置")
        goal = player.get("goal", "未知目标")
        inventory = player.get("inventory", [])
        parts.append(f"玩家角色：{identity}，目标：{goal}，当前位置：{location}")
        if inventory:
            parts.append(f"背包：{', '.join(inventory)}")
        
        characters = self.data.get("characters", {})
        if characters:
            char_desc = []
            for name, info in list(characters.items())[:5]:
                loc = info.get("location", "未知")
                att = info.get("attitude", 0)
                char_desc.append(f"{name}(位置:{loc},态度:{att})")
            parts.append(f"关键角色：{'; '.join(char_desc)}")
        
        factions = self.data.get("factions", {})
        if factions:
            fac_desc = []
            for name, info in list(factions.items())[:3]:
                rel = info.get("relationship_with_player", 0)
                fac_desc.append(f"{name}(关系:{rel})")
            parts.append(f"势力：{'; '.join(fac_desc)}")
        
        world_events = self._get_world_events()
        if world_events:
            parts.append(f"世界事件历史：\n{world_events}")
        
        return "\n".join(parts)
    
    def _get_world_events(self) -> str:
        files = self.get_save_files_paths()
        if not files or "world_event" not in files:
            return ""
        
        if not os.path.exists(files["world_event"]):
            return ""
        
        with open(files["world_event"], "r", encoding="utf-8") as f:
            return f.read()
    
    def _save_summary_log(self, summary: str) -> None:
        files = self.get_save_files_paths()
        if not files or "summary_log" not in files:
            return
        
        save_dir = get_current_save_dir()
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
        
        day, period = self.time_mgr.get()
        period_cn = PERIOD_CN.get(period, period)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(files["summary_log"], "a", encoding="utf-8") as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"[{timestamp}] 第{day}天 {period_cn}\n")
            f.write(f"{'='*50}\n")
            f.write(summary)
            f.write("\n")
    
    def save_summary_log(self) -> None:
        summary = self.get_world_summary()
        self._save_summary_log(summary)
    
    def get_current_time(self) -> tuple[int, str]:
        return self.time_mgr.get()
    
    def advance_time(self, periods: int = 1) -> None:
        self.time_mgr.advance(periods)
    
    def set_time(self, day: int, period: str) -> None:
        self.time_mgr.set(day, period)
    
    def skip_to_time(self, target_day: int, target_period: str) -> list[dict]:
        if target_period not in PERIOD_ORDER:
            raise ValueError(f"Invalid period: {target_period}")
        
        from_time = self.time_mgr.get()
        to_time = (target_day, target_period)
        
        nodes_in_range = self.node_mgr.get_nodes_in_range(from_time, to_time)
        
        self.time_mgr.set(target_day, target_period)
        
        return nodes_in_range
    
    def check_nodes(self) -> list[dict]:
        return self.node_mgr.check_nodes(self.time_mgr.get())
    
    def get_all_future_nodes(self) -> list[dict]:
        return [n for n in self.node_mgr.nodes if not n.get("triggered", False)]
    
    def mark_nodes_triggered(self, nodes: list[dict]) -> None:
        self.node_mgr.mark_triggered(nodes)
    
    def mark_all_nodes_in_range_triggered(self, from_time: tuple[int, str], to_time: tuple[int, str]) -> None:
        self.node_mgr.mark_all_in_range_triggered(from_time, to_time)
