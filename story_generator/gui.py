import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import json
import shutil
from datetime import datetime
from typing import Optional, Callable, Any

from story_generator.config import PERIOD_CN, list_all_saves, get_save_dir, SAVES_BASE_DIR
from story_generator.state_manager import StateManager
from story_generator.narrative_engine import NarrativeEngine
from story_generator.node_parser import NodeParser
from story_generator.event_recorder import EventRecorder
from story_generator.world_outline_generator import WorldOutlineGenerator
from story_generator.utils import load_api_key
from story_generator import settings


COLORS = {
    "bg": "#1E1E2E",
    "card": "#2D2D44",
    "button": "#5F9EA0",
    "button_hover": "#4682B4",
    "text": "#FFFFFF",
    "text_secondary": "#CCCCCC",
    "border": "#3D3D54",
    "input_bg": "#23232E",
    "danger": "#FF6B6B",
    "danger_hover": "#FF5252",
    "success": "#4ECDC4",
}
FONT_SIZE = 14

class StyledButton(ctk.CTkButton):
    def __init__(self, master: Any, text: str, command: Callable[[], None] = None, 
                 style: str = "primary", width: int = 200, height: int = 45, **kwargs):
        if style == "primary":
            default_fg_color = COLORS["button"]
            default_hover_color = COLORS["button_hover"]
            default_text_color = "#FFFFFF"
        elif style == "secondary":
            default_fg_color = COLORS["card"]
            default_hover_color = COLORS["border"]
            default_text_color = COLORS["text"]
        elif style == "danger":
            default_fg_color = COLORS["danger"]
            default_hover_color = COLORS["danger_hover"]
            default_text_color = "#FFFFFF"
        else:
            default_fg_color = COLORS["button"]
            default_hover_color = COLORS["button_hover"]
            default_text_color = "#FFFFFF"
        
        fg_color = kwargs.pop("fg_color", default_fg_color)
        hover_color = kwargs.pop("hover_color", default_hover_color)
        text_color = kwargs.pop("text_color", default_text_color)
        
        super().__init__(
            master,
            text=text,
            command=command,
            width=width,
            height=height,
            fg_color=fg_color,
            hover_color=hover_color,
            text_color=text_color,
            corner_radius=10,
            font=ctk.CTkFont(family="Microsoft YaHei", size=FONT_SIZE),
            **kwargs
        )
    
    def configure(self, **kwargs):
        if "style" in kwargs:
            style = kwargs.pop("style")
            if style == "primary":
                kwargs["fg_color"] = COLORS["button"]
                kwargs["hover_color"] = COLORS["button_hover"]
                kwargs["text_color"] = "#FFFFFF"
            elif style == "secondary":
                kwargs["fg_color"] = COLORS["card"]
                kwargs["hover_color"] = COLORS["border"]
                kwargs["text_color"] = COLORS["text"]
            elif style == "danger":
                kwargs["fg_color"] = COLORS["danger"]
                kwargs["hover_color"] = COLORS["danger_hover"]
                kwargs["text_color"] = "#FFFFFF"
        super().configure(**kwargs)


class CardFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=COLORS["card"],
            corner_radius=15,
            **kwargs
        )


class StartFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.setup_ui()
    
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        center_frame = ctk.CTkFrame(self, fg_color="transparent")
        center_frame.grid(row=0, column=0, sticky="nsew")
        center_frame.grid_columnconfigure(0, weight=1)
        
        title_label = ctk.CTkLabel(
            center_frame,
            text="故事生成器",
            font=ctk.CTkFont(family="Microsoft YaHei", size=42, weight="bold"),
            text_color=COLORS["text"]
        )
        title_label.grid(row=0, column=0, pady=(120, 10))
        
        subtitle_label = ctk.CTkLabel(
            center_frame,
            text="时间驱动的交互式故事体验",
            font=ctk.CTkFont(family="Microsoft YaHei", size=16),
            text_color=COLORS["text_secondary"]
        )
        subtitle_label.grid(row=1, column=0, pady=(0, 60))
        
        buttons_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        buttons_frame.grid(row=2, column=0)
        
        self.new_game_btn = StyledButton(buttons_frame, "开始新游戏", command=self.on_new_game)
        self.new_game_btn.grid(row=0, column=0, pady=8)
        
        self.save_btn = StyledButton(buttons_frame, "存档", style="secondary", command=self.on_save_manager)
        self.save_btn.grid(row=1, column=0, pady=8)
        
        self.settings_btn = StyledButton(buttons_frame, "设置", style="secondary", command=self.on_settings)
        self.settings_btn.grid(row=2, column=0, pady=8)
        
        self.exit_btn = StyledButton(buttons_frame, "退出", style="danger", command=self.on_exit)
        self.exit_btn.grid(row=3, column=0, pady=8)
    
    def on_new_game(self):
        self.app.show_frame("new_game")
    
    def on_save_manager(self):
        self.app.show_frame("save_manager")
    
    def on_settings(self):
        self.app.show_frame("settings")
    
    def on_exit(self):
        self.app.quit()
    
    def refresh(self):
        pass


class NewGameFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.outline_generator: Optional[WorldOutlineGenerator] = None
        self.current_outline = ""
        self.is_generating = False
        self.setup_ui()
    
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=40, pady=(30, 10))
        header.grid_columnconfigure(1, weight=1)
        
        back_btn = StyledButton(header, "← 返回", style="secondary", width=100, height=35,
                                command=lambda: self.app.show_frame("start"))
        back_btn.grid(row=0, column=0, padx=10)
        
        title = ctk.CTkLabel(header, text="创建新角色", 
                             font=ctk.CTkFont(family="Microsoft YaHei", size=24, weight="bold"),
                             text_color=COLORS["text"])
        title.grid(row=0, column=1, sticky="w", padx=20)
        
        content = CardFrame(self)
        content.grid(row=1, column=0, sticky="nsew", padx=40, pady=20)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(6, weight=1)
        
        identity_label = ctk.CTkLabel(content, text="角色身份（可选）",
                                      font=ctk.CTkFont(family="Microsoft YaHei", size=16),
                                      text_color=COLORS["text"])
        identity_label.grid(row=0, column=0, sticky="w", padx=30, pady=(30, 5))
        
        self.identity_entry = ctk.CTkEntry(
            content, placeholder_text="如：流浪剑客、神秘法师、商队护卫...（留空则由大纲决定）",
            height=45, corner_radius=10,
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Microsoft YaHei", size=FONT_SIZE)
        )
        self.identity_entry.grid(row=1, column=0, sticky="ew", padx=30, pady=(0, 20))
        
        goal_label = ctk.CTkLabel(content, text="角色目标（可选）",
                                  font=ctk.CTkFont(family="Microsoft YaHei", size=16),
                                  text_color=COLORS["text"])
        goal_label.grid(row=2, column=0, sticky="w", padx=30, pady=(0, 5))
        
        self.goal_entry = ctk.CTkEntry(
            content, placeholder_text="如：寻找神器、复仇、探索世界...（留空则由大纲决定）",
            height=45, corner_radius=10,
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Microsoft YaHei", size=FONT_SIZE)
        )
        self.goal_entry.grid(row=3, column=0, sticky="ew", padx=30, pady=(0, 20))
        
        outline_header = ctk.CTkFrame(content, fg_color="transparent")
        outline_header.grid(row=4, column=0, sticky="ew", padx=30, pady=(10, 5))
        outline_header.grid_columnconfigure(0, weight=1)
        
        outline_label = ctk.CTkLabel(outline_header, text="世界大纲",
                                     font=ctk.CTkFont(family="Microsoft YaHei", size=16),
                                     text_color=COLORS["text"])
        outline_label.grid(row=0, column=0, sticky="w")
        
        self.generate_btn = StyledButton(outline_header, "自动生成大纲", width=140, height=35,
                                         command=self.generate_outline)
        self.generate_btn.grid(row=0, column=1, padx=5)
        
        self.outline_hint = ctk.CTkLabel(
            outline_header, text="输入主题或直接点击生成",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            text_color=COLORS["text_secondary"]
        )
        self.outline_hint.grid(row=0, column=2, padx=10)
        
        self.outline_text = ctk.CTkTextbox(
            content, height=200, corner_radius=10,
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Microsoft YaHei", size=FONT_SIZE)
        )
        self.outline_text.grid(row=5, column=0, sticky="ew", padx=30, pady=(0, 10))
        
        self.loading_label = ctk.CTkLabel(
            content, text="",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            text_color=COLORS["text_secondary"]
        )
        self.loading_label.grid(row=6, column=0, sticky="w", padx=30, pady=(0, 10))
        
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.grid(row=7, column=0, pady=20)
        
        start_btn = StyledButton(btn_frame, "开始冒险", width=200, height=50,
                                 command=self.start_game)
        start_btn.grid(row=0, column=0, padx=10)
        
        skip_btn = StyledButton(btn_frame, "跳过大纲直接开始", style="secondary", width=200, height=50,
                                command=self.start_game_without_outline)
        skip_btn.grid(row=0, column=1, padx=10)
    
    def generate_outline(self):
        if self.is_generating:
            return
        
        user_input = self.outline_text.get("1.0", "end").strip()
        if user_input and user_input.startswith("【"):
            user_input = ""
        
        identity = self.identity_entry.get().strip()
        goal = self.goal_entry.get().strip()
        
        try:
            api_key = load_api_key()
            self.outline_generator = WorldOutlineGenerator(api_key)
        except Exception as e:
            messagebox.showerror("错误", f"加载 API Key 失败: {e}")
            return
        
        self.is_generating = True
        self.generate_btn.configure(state="disabled", text="生成中...")
        self.loading_label.configure(text="正在生成世界大纲...", text_color=COLORS["text_secondary"])
        self.outline_text.delete("1.0", "end")
        
        threading.Thread(target=self._generate_outline_thread, args=(user_input, identity, goal), daemon=True).start()
    
    def _generate_outline_thread(self, user_input: str, identity: str, goal: str):
        try:
            gen = self.outline_generator.generate_outline_stream(user_input, identity, goal)
            full_text = ""
            
            for chunk in gen:
                full_text += chunk
                self.after(0, lambda c=chunk: self._append_outline_chunk(c))
            
            self.current_outline = full_text
            self.after(0, lambda: self.loading_label.configure(
                text="大纲生成完成！可再次点击生成新大纲，或直接开始冒险", 
                text_color=COLORS["success"]
            ))
            
        except Exception as e:
            self.after(0, lambda: self.loading_label.configure(
                text=f"生成失败: {str(e)}", 
                text_color=COLORS["danger"]
            ))
        finally:
            self.after(0, self._finish_generation)
    
    def _append_outline_chunk(self, chunk: str):
        self.outline_text.insert("end", chunk)
        self.outline_text.see("end")
    
    def _finish_generation(self):
        self.is_generating = False
        self.generate_btn.configure(state="normal", text="自动生成大纲")
    
    def start_game(self):
        if self.is_generating:
            return
        
        identity = self.identity_entry.get().strip()
        goal = self.goal_entry.get().strip()
        outline = self.outline_text.get("1.0", "end").strip()
        
        self.app.start_new_game(identity, goal, outline)
    
    def start_game_without_outline(self):
        if self.is_generating:
            return
        
        identity = self.identity_entry.get().strip()
        goal = self.goal_entry.get().strip()
        
        if not identity:
            identity = "冒险者"
        if not goal:
            goal = "探索这个世界"
        
        self.app.start_new_game(identity, goal, "")


class GameFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.state_mgr: Optional[StateManager] = None
        self.engine: Optional[NarrativeEngine] = None
        self.is_generating = False
        self.first_generation = True
        self.setup_ui()
    
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=7)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        
        main_card = CardFrame(self)
        main_card.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)
        main_card.grid_columnconfigure(0, weight=1)
        main_card.grid_rowconfigure(1, weight=1)
        
        header = ctk.CTkFrame(main_card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        header.grid_columnconfigure(1, weight=1)
        
        self.time_label = ctk.CTkLabel(
            header, text="第1天 早晨",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color=COLORS["text"]
        )
        self.time_label.grid(row=0, column=0, sticky="w")
        
        self.location_label = ctk.CTkLabel(
            header, text="",
            font=ctk.CTkFont(family="Microsoft YaHei", size=14),
            text_color=COLORS["text_secondary"]
        )
        self.location_label.grid(row=0, column=1, sticky="e")
        
        self.story_text = ctk.CTkTextbox(
            main_card, wrap="word",
            font=ctk.CTkFont(family="Microsoft YaHei", size=FONT_SIZE),
            text_color=COLORS["text"],
            fg_color="transparent",
            corner_radius=0
        )
        self.story_text.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        
        side_card = CardFrame(self)
        side_card.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        side_card.grid_columnconfigure(0, weight=1)
        
        status_title = ctk.CTkLabel(
            side_card, text="角色状态",
            font=ctk.CTkFont(family="Microsoft YaHei", size=16, weight="bold"),
            text_color=COLORS["text"]
        )
        status_title.grid(row=0, column=0, pady=(20, 10))
        
        self.status_frame = ctk.CTkFrame(side_card, fg_color="transparent")
        self.status_frame.grid(row=1, column=0, sticky="ew", padx=15)
        self.status_frame.grid_columnconfigure(0, weight=1)
        
        self.identity_label = ctk.CTkLabel(
            self.status_frame, text="身份：未知",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        self.identity_label.grid(row=0, column=0, sticky="ew", pady=3)
        
        self.goal_label = ctk.CTkLabel(
            self.status_frame, text="目标：未知",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        self.goal_label.grid(row=1, column=0, sticky="ew", pady=3)
        
        self.hp_frame = ctk.CTkFrame(self.status_frame, fg_color="transparent")
        self.hp_frame.grid(row=2, column=0, sticky="ew", pady=5)
        self.hp_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.hp_frame, text="生命值：",
                     font=ctk.CTkFont(family="Microsoft YaHei", size=13),
                     text_color=COLORS["text_secondary"]).grid(row=0, column=0)
        
        self.hp_bar = ctk.CTkProgressBar(self.hp_frame, width=120, height=15,
                                         progress_color=COLORS["success"],
                                         fg_color=COLORS["border"])
        self.hp_bar.grid(row=0, column=1, padx=10)
        self.hp_bar.set(1.0)
        
        self.money_label = ctk.CTkLabel(
            self.status_frame, text="金钱：50",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        self.money_label.grid(row=3, column=0, sticky="ew", pady=3)
        
        self.inventory_label = ctk.CTkLabel(
            self.status_frame, text="背包：空",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=COLORS["text_secondary"],
            anchor="w", wraplength=180, justify="left"
        )
        self.inventory_label.grid(row=4, column=0, sticky="ew", pady=3)
        
        buttons_frame = ctk.CTkFrame(side_card, fg_color="transparent")
        buttons_frame.grid(row=2, column=0, pady=30)
        
        save_btn = StyledButton(buttons_frame, "保存游戏", width=160, height=38,
                               command=self.save_game)
        save_btn.grid(row=0, column=0, columnspan=2, pady=5)
        
        load_btn = StyledButton(buttons_frame, "读取存档", fg_color=COLORS["bg"], hover_color=COLORS["border"], width=75, height=38,
                               command=lambda: self.app.show_frame("save_manager"))
        load_btn.grid(row=1, column=0, pady=5, padx=2)
        
        edit_save_btn = StyledButton(buttons_frame, "修改存档", fg_color=COLORS["bg"], hover_color=COLORS["border"], width=75, height=38,
                               command=self.edit_save)
        edit_save_btn.grid(row=1, column=1, pady=5, padx=2)
        
        menu_btn = StyledButton(buttons_frame, "返回主菜单", fg_color=COLORS["bg"], hover_color=COLORS["border"], width=160, height=38,
                               command=self.return_to_menu)
        menu_btn.grid(row=2, column=0, columnspan=2, pady=5)
        
        input_card = CardFrame(self)
        input_card.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 20))
        input_card.grid_columnconfigure(0, weight=1)
        
        input_frame = ctk.CTkFrame(input_card, fg_color="transparent")
        input_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=15)
        input_frame.grid_columnconfigure(0, weight=1)
        
        self.input_entry = ctk.CTkEntry(
            input_frame, placeholder_text="输入你的行动或 /help 查看命令...",
            height=45, corner_radius=10,
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Microsoft YaHei", size=FONT_SIZE)
        )
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.input_entry.bind("<Return>", lambda e: self.submit_input())
        
        self.submit_btn = StyledButton(input_frame, "提交", width=80, height=45,
                                       command=self.submit_input)
        self.submit_btn.grid(row=0, column=1)
        
        self.loading_label = ctk.CTkLabel(
            input_frame, text="",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            text_color=COLORS["text_secondary"]
        )
        self.loading_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(5, 0))
    
    def set_state_manager(self, state_mgr: StateManager, engine: NarrativeEngine):
        self.state_mgr = state_mgr
        self.engine = engine
        self.first_generation = True
        self.update_status()
        self.update_time_display()
        self.story_text.delete("1.0", "end")
        world_events = self.state_mgr._get_world_events()
        if world_events:
            self.story_text.insert("1.0", world_events)
            self.story_text.see("end")
    
    def update_status(self):
        if not self.state_mgr:
            return
        
        player = self.state_mgr.data.get("player", {})
        stats = player.get("stats", {})
        inventory = player.get("inventory", [])
        
        self.identity_label.configure(text=f"身份：{player.get('identity', '未知')}")
        self.goal_label.configure(text=f"目标：{player.get('goal', '未知')}")
        
        health = stats.get("health", 100)
        self.hp_bar.set(health / 100)
        
        self.money_label.configure(text=f"金钱：{stats.get('money', 0)}")
        
        inv_text = "背包：空" if not inventory else f"背包：{', '.join(inventory)}"
        self.inventory_label.configure(text=inv_text)
        
        self.location_label.configure(text=f"📍 {player.get('location', '未知')}")
    
    def update_time_display(self):
        if not self.state_mgr:
            return
        day, period = self.state_mgr.get_current_time()
        period_cn = PERIOD_CN.get(period, period)
        self.time_label.configure(text=f"第{day}天 {period_cn}")
    
    def update_story(self, text: str, append: bool = True):
        if append:
            current = self.story_text.get("1.0", "end")
            if current.strip():
                self.story_text.insert("end", "\n\n" + "=" * 40 + "\n\n")
            self.story_text.insert("end", text)
            self.story_text.see("end")
            if self.first_generation:
                self.first_generation = False
        else:
            self.story_text.delete("1.0", "end")
            self.story_text.insert("1.0", text)
            self.story_text.see("end")
    
    def save_game(self):
        if self.state_mgr:
            self.state_mgr.save_current()
            self.show_message("游戏已保存", "success")
    
    def show_message(self, message: str, msg_type: str = "info"):
        if msg_type == "success":
            color = COLORS["success"]
        elif msg_type == "error":
            color = COLORS["danger"]
        else:
            color = COLORS["text_secondary"]
        self.loading_label.configure(text=message, text_color=color)
        self.after(3000, lambda: self.loading_label.configure(text=""))
    
    def submit_input(self):
        if self.is_generating:
            return
        
        text = self.input_entry.get().strip()
        if not text:
            return
        
        self.input_entry.delete(0, "end")
        
        if text.startswith("/"):
            self.handle_command(text)
            return
        
        self.is_generating = True
        self.submit_btn.configure(state="disabled")
        self.loading_label.configure(text="正在生成故事...", text_color=COLORS["text_secondary"])
        
        threading.Thread(target=self._generate_story, args=(text,), daemon=True).start()
    
    def _generate_story(self, player_input: str):
        try:
            summary = self.state_mgr.get_world_summary()
            cur_time = self.state_mgr.get_current_time()
            
            pending = self.state_mgr.get_all_future_nodes()
            
            self.after(0, lambda: self._prepare_story_display())
            
            gen = self.engine.generate_story_stream(
                summary, cur_time, pending, player_input,
                self.state_mgr.data["player"].get("identity", "冒险者"),
                self.state_mgr.data["player"].get("location", "")
            )
            
            story_text = ""
            ai_json = None
            
            try:
                while True:
                    chunk = next(gen)
                    story_text += chunk
                    self.after(0, lambda c=chunk: self._append_story_chunk(c))
            except StopIteration as e:
                story_text, ai_json = e.value
            
            if ai_json:
                self.state_mgr.update_from_ai_response(ai_json)
                
                time_skip = ai_json.get("time_skip", {})
                if time_skip and time_skip.get("target_day") and time_skip.get("target_period"):
                    target_day = time_skip["target_day"]
                    target_period = time_skip["target_period"]
                    from_time = cur_time
                    to_time = (target_day, target_period)
                    self.state_mgr.node_mgr.mark_all_in_range_triggered(from_time, to_time)
                    self.state_mgr.set_time(target_day, target_period)
                else:
                    periods = ai_json.get("time_advance", {}).get("periods", 1)
                    self.state_mgr.advance_time(periods)
                    if pending:
                        self.state_mgr.mark_nodes_triggered(pending)
            else:
                self.state_mgr.advance_time(1)
                if pending:
                    self.state_mgr.mark_nodes_triggered(pending)
            
            new_time = self.state_mgr.get_current_time()
            player_location = self.state_mgr.data["player"].get("location", "")
            if self.app.event_recorder:
                try:
                    self.app.event_recorder.record_event(story_text, new_time, player_location)
                except Exception as e:
                    print(f"事件记录失败: {e}")
            
            self.state_mgr.save_summary_log()
            self.state_mgr.save_current()
            
            self.after(0, self.update_status)
            self.after(0, self.update_time_display)
            self.after(0, lambda: self.show_message("故事已生成，存档已自动保存", "success"))
            
        except Exception as e:
            self.after(0, lambda: self.show_message(f"生成失败: {str(e)}", "error"))
        finally:
            self.after(0, lambda: self.finish_generation())
    
    def _prepare_story_display(self):
        current = self.story_text.get("1.0", "end")
        if current.strip():
            self.story_text.insert("end", "\n\n" + "=" * 40 + "\n\n")
        self.story_text.see("end")
    
    def _append_story_chunk(self, chunk: str):
        self.story_text.insert("end", chunk)
        self.story_text.see("end")
    
    def finish_generation(self):
        self.is_generating = False
        self.submit_btn.configure(state="normal")
        self.loading_label.configure(text="")
    
    def handle_command(self, cmd: str):
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        
        if command == "/save":
            self.save_game()
        elif command == "/time":
            day, period = self.state_mgr.get_current_time()
            self.show_message(f"当前时间：第{day}天 {PERIOD_CN.get(period, period)}")
        elif command == "/status":
            self.update_status()
            self.show_message("状态已更新")
        elif command == "/help":
            help_text = """可用命令：
/save - 保存游戏
/time - 显示当前时间
/status - 显示角色状态
/help - 显示帮助
输入其他文字进行游戏"""
            self.update_story(help_text)
        elif command == "/quit":
            self.return_to_menu()
        else:
            self.show_message(f"未知命令: {command}", "error")
    
    def return_to_menu(self):
        if self.is_generating:
            return
        self.app.show_frame("start")
    
    def edit_save(self):
        if self.is_generating:
            return
        if self.state_mgr and self.state_mgr.save_number:
            self.app.frames["save_editor"].set_save_number(self.state_mgr.save_number, "game")
            self.app.show_frame("save_editor")


class SaveManagerFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.setup_ui()
    
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=40, pady=(30, 10))
        header.grid_columnconfigure(1, weight=1)
        
        back_btn = StyledButton(header, "← 返回", style="secondary", width=100, height=35,
                               command=lambda: self.app.show_frame("start"))
        back_btn.grid(row=0, column=0, padx=10)
        
        title = ctk.CTkLabel(header, text="存档管理",
                             font=ctk.CTkFont(family="Microsoft YaHei", size=24, weight="bold"),
                             text_color=COLORS["text"])
        title.grid(row=0, column=1, sticky="w", padx=20)
        
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", )
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=40, pady=20)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
    
    def refresh(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        
        saves = list_all_saves()
        
        if not saves:
            no_save_label = ctk.CTkLabel(
                self.scroll_frame, text="暂无存档",
                font=ctk.CTkFont(family="Microsoft YaHei", size=16),
                text_color=COLORS["text_secondary"]
            )
            no_save_label.grid(row=0, column=0, pady=50)
            return
        
        for i, save in enumerate(saves):
            self.create_save_card(save, i)
    
    def create_save_card(self, save: dict, row: int):
        card = CardFrame(self.scroll_frame)
        card.grid(row=row, column=0, sticky="ew", pady=8)
        card.grid_columnconfigure(1, weight=1)
        
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.grid(row=0, column=0, sticky="w", padx=20, pady=15)
        
        name_label = ctk.CTkLabel(
            info_frame, text=save.get("name", "未知存档"),
            font=ctk.CTkFont(family="Microsoft YaHei", size=16, weight="bold"),
            text_color=COLORS["text"]
        )
        name_label.grid(row=0, column=0, sticky="w")
        
        player = save.get("player", {})
        time_info = save.get("time", {})
        identity = player.get("identity", "未知")
        day = time_info.get("day", "?")
        
        nodes = save.get("nodes", [])
        all_nodes_completed = all(n.get("triggered", False) for n in nodes) if nodes else False
        nodes_status = "全部完成" if all_nodes_completed and nodes else f"{sum(1 for n in nodes if n.get('triggered'))}/{len(nodes)}" if nodes else "无节点"
        
        detail_label = ctk.CTkLabel(
            info_frame, text=f"{identity} | 第{day}天 | 节点: {nodes_status}",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=COLORS["text_secondary"]
        )
        detail_label.grid(row=1, column=0, sticky="w", pady=(3, 0))
        
        last_saved = save.get("last_saved", "")
        if last_saved:
            try:
                dt = datetime.fromisoformat(last_saved)
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                time_str = last_saved
        else:
            time_str = "未知"
        
        time_label = ctk.CTkLabel(
            info_frame, text=f"保存时间: {time_str}",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            text_color=COLORS["text_secondary"]
        )
        time_label.grid(row=2, column=0, sticky="w", pady=(3, 0))
        
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e", padx=20, pady=15)
        
        load_btn = StyledButton(btn_frame, "读取", width=60, height=35,
                               command=lambda s=save: self.load_save(s))
        load_btn.grid(row=0, column=0, padx=3)
        
        if all_nodes_completed and nodes:
            continue_btn = StyledButton(btn_frame, "续写", fg_color=COLORS["success"], hover_color="#3DB9AA", width=60, height=35,
                                   command=lambda s=save: self.continue_outline(s))
            continue_btn.grid(row=0, column=1, padx=3)
        
        edit_btn = StyledButton(btn_frame, "修改", fg_color=COLORS["bg"], hover_color=COLORS["border"], width=60, height=35,
                               command=lambda s=save: self.edit_save(s))
        edit_btn.grid(row=0, column=2, padx=3)
        
        delete_btn = StyledButton(btn_frame, "删除", style="danger", width=60, height=35,
                                 command=lambda s=save: self.delete_save(s))
        delete_btn.grid(row=0, column=3, padx=3)
    
    def continue_outline(self, save: dict):
        save_name = save.get("name", "")
        if not save_name:
            return
        
        save_num = int(save_name.replace("save", ""))
        self.app.frames["continue_outline"].set_save_number(save_num)
        self.app.show_frame("continue_outline")
    
    def load_save(self, save: dict):
        save_name = save.get("name", "")
        if not save_name:
            return
        
        save_num = int(save_name.replace("save", ""))
        if self.app.load_game(save_num):
            self.app.show_frame("game")
    
    def edit_save(self, save: dict):
        save_name = save.get("name", "")
        if not save_name:
            return
        
        save_num = int(save_name.replace("save", ""))
        self.app.frames["save_editor"].set_save_number(save_num, "save_manager")
        self.app.show_frame("save_editor")
    
    def delete_save(self, save: dict):
        save_name = save.get("name", "")
        if not save_name:
            return
        
        if messagebox.askyesno("确认删除", f"确定要删除 {save_name} 吗？\n此操作不可撤销。"):
            save_path = save.get("path", "")
            if save_path and os.path.exists(save_path):
                shutil.rmtree(save_path)
                self.refresh()


class SettingsFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.setup_ui()
    
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=40, pady=(30, 10))
        header.grid_columnconfigure(1, weight=1)
        
        back_btn = StyledButton(header, "← 返回", style="secondary", width=100, height=35,
                               command=lambda: self.app.show_frame("start"))
        back_btn.grid(row=0, column=0, padx=10)
        
        title = ctk.CTkLabel(header, text="设置",
                             font=ctk.CTkFont(family="Microsoft YaHei", size=24, weight="bold"),
                             text_color=COLORS["text"])
        title.grid(row=0, column=1, sticky="w", padx=20)
        
        content = CardFrame(self)
        content.grid(row=1, column=0, sticky="nsew", padx=40, pady=20)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)
        
        self.scroll_frame = ctk.CTkScrollableFrame(content, fg_color="transparent", )
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
    
    def refresh(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        
        self.create_api_section()
        self.create_prompt_section()
    
    def create_api_section(self):
        section_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        section_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        section_frame.grid_columnconfigure(0, weight=1)
        
        section_label = ctk.CTkLabel(
            section_frame, text="API 配置",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color=COLORS["text"]
        )
        section_label.grid(row=0, column=0, sticky="w")
        
        # 添加API设置的保存和重置按钮
        api_buttons_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        api_buttons_frame.grid(row=0, column=1, sticky="e")
        
        save_api_btn = StyledButton(api_buttons_frame, "保存", width=100, height=35,
                                   command=self.save_api_settings)
        save_api_btn.grid(row=0, column=0, padx=5)
        
        reset_api_btn = StyledButton(api_buttons_frame, "重置", style="danger", width=100, height=35,
                                    command=self.reset_api_settings)
        reset_api_btn.grid(row=0, column=1, padx=5)
        
        api_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        api_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        api_frame.grid_columnconfigure(1, weight=1)
        
        current_settings = settings.get_settings()
        api_config = current_settings.get("api", {})
        
        ctk.CTkLabel(api_frame, text="API Key:",
                     font=ctk.CTkFont(family="Microsoft YaHei", size=14),
                     text_color=COLORS["text_secondary"]).grid(row=0, column=0, sticky="w", pady=8)
        
        self.api_key_entry = ctk.CTkEntry(
            api_frame, placeholder_text="输入 API Key...",
            height=40, corner_radius=8, show="*",
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Microsoft YaHei", size=FONT_SIZE)
        )
        self.api_key_entry.grid(row=0, column=1, sticky="ew", padx=(15, 0), pady=8)
        self.api_key_entry.insert(0, api_config.get("api_key", ""))
        
        ctk.CTkLabel(api_frame, text="API URL:",
                     font=ctk.CTkFont(family="Microsoft YaHei", size=14),
                     text_color=COLORS["text_secondary"]).grid(row=1, column=0, sticky="w", pady=8)
        
        self.api_url_entry = ctk.CTkEntry(
            api_frame, placeholder_text="输入 API URL...",
            height=40, corner_radius=8,
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Microsoft YaHei", size=FONT_SIZE)
        )
        self.api_url_entry.grid(row=1, column=1, sticky="ew", padx=(15, 0), pady=8)
        self.api_url_entry.insert(0, api_config.get("api_url", ""))
        
        ctk.CTkLabel(api_frame, text="模型:",
                     font=ctk.CTkFont(family="Microsoft YaHei", size=14),
                     text_color=COLORS["text_secondary"]).grid(row=2, column=0, sticky="w", pady=8)
        
        self.model_entry = ctk.CTkEntry(
            api_frame, placeholder_text="输入模型名称...",
            height=40, corner_radius=8,
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Microsoft YaHei", size=FONT_SIZE)
        )
        self.model_entry.grid(row=2, column=1, sticky="ew", padx=(15, 0), pady=8)
        self.model_entry.insert(0, api_config.get("model", ""))
    
    def create_prompt_section(self):
        section_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        section_frame.grid(row=2, column=0, sticky="ew", pady=(20, 15))
        section_frame.grid_columnconfigure(0, weight=1)
        
        section_label = ctk.CTkLabel(
            section_frame, text="AI 参数配置",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color=COLORS["text"]
        )
        section_label.grid(row=0, column=0, sticky="w")
        
        readme_btn = StyledButton(section_frame, "README", style="secondary", width=100, height=32,
                                  fg_color=COLORS["bg"], hover_color=COLORS["button_hover"],
                                  command=lambda: self.app.show_frame("readme"))
        readme_btn.grid(row=0, column=1, padx=10)
        
        prompt_types = [
            ("narrative", "故事生成", "narrative_settings"),
            ("node_parser", "大纲解析", "node_parser_settings"),
            ("event_recorder", "事件记录", "event_recorder_settings"),
            ("world_outline", "世界大纲", "world_outline_settings"),
            ("continue_outline", "故事续写", "continue_outline_settings")
        ]
        
        for i, (key, name, _) in enumerate(prompt_types):
            card = ctk.CTkFrame(self.scroll_frame, fg_color=COLORS["input_bg"], corner_radius=10)
            card.grid(row=3 + i, column=0, sticky="ew", pady=5)
            card.grid_columnconfigure(0, weight=1)
            
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.grid(row=0, column=0, sticky="w", padx=15, pady=12)
            
            ctk.CTkLabel(
                info_frame, text=name,
                font=ctk.CTkFont(family="Microsoft YaHei", size=15, weight="bold"),
                text_color=COLORS["text"]
            ).grid(row=0, column=0, sticky="w")
            
            current_settings = settings.get_settings()
            config = current_settings.get(key, {})
            temp = config.get("temperature", 0.5)
            tokens = config.get("max_tokens", 500)
            
            ctk.CTkLabel(
                info_frame, text=f"温度: {temp} | 最大Token: {tokens}",
                font=ctk.CTkFont(family="Microsoft YaHei", size=12),
                text_color=COLORS["text_secondary"]
            ).grid(row=1, column=0, sticky="w")
            
            btn = StyledButton(card, "编辑", style="secondary", width=80, height=32,
                              command=lambda k=key: self.app.show_frame(f"prompt_{k}"))
            btn.grid(row=0, column=1, padx=15, pady=12)
    
    def save_api_settings(self):
        api_key = self.api_key_entry.get().strip()
        api_url = self.api_url_entry.get().strip()
        model = self.model_entry.get().strip()
        
        settings.update_api_settings(
            api_key=api_key,
            api_url=api_url,
            model=model
        )
        
        messagebox.showinfo("成功", "API设置已保存")
    
    def reset_api_settings(self):
        if messagebox.askyesno("确认", "确定要恢复默认API设置吗？"):
            settings.reset_api_to_defaults()
            self.refresh()
            messagebox.showinfo("成功", "已恢复默认API设置")


class PromptSettingsFrame(ctk.CTkFrame):
    def __init__(self, master, app, prompt_type: str, prompt_name: str):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.prompt_type = prompt_type
        self.prompt_name = prompt_name
        self.setup_ui()
    
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=40, pady=(30, 10))
        header.grid_columnconfigure(1, weight=1)
        
        back_btn = StyledButton(header, "← 返回", style="secondary", width=100, height=35,
                               command=lambda: self.app.show_frame("settings"))
        back_btn.grid(row=0, column=0, padx=10)
        
        title = ctk.CTkLabel(header, text=f"{self.prompt_name} 设置",
                             font=ctk.CTkFont(family="Microsoft YaHei", size=24, weight="bold"),
                             text_color=COLORS["text"])
        title.grid(row=0, column=1, sticky="w", padx=20)
        
        content = CardFrame(self)
        content.grid(row=1, column=0, sticky="nsew", padx=40, pady=20)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(3, weight=1)
        
        params_frame = ctk.CTkFrame(content, fg_color="transparent")
        params_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 10))
        params_frame.grid_columnconfigure(1, weight=1)
        
        current_settings = settings.get_settings()
        config = current_settings.get(self.prompt_type, {})
        
        ctk.CTkLabel(params_frame, text="温度 (Temperature):",
                     font=ctk.CTkFont(family="Microsoft YaHei", size=14),
                     text_color=COLORS["text"]).grid(row=0, column=0, sticky="w", pady=10)
        
        self.temp_slider = ctk.CTkSlider(
            params_frame, from_=0.0, to=2.0, number_of_steps=20,
            height=20, corner_radius=10,
            fg_color=COLORS["border"],
            progress_color=COLORS["button"]
        )
        self.temp_slider.grid(row=0, column=1, sticky="ew", padx=(15, 10), pady=10)
        self.temp_slider.set(config.get("temperature", 0.5))
        
        self.temp_label = ctk.CTkLabel(
            params_frame, text="0.5",
            font=ctk.CTkFont(family="Microsoft YaHei", size=14),
            text_color=COLORS["text_secondary"], width=50
        )
        self.temp_label.grid(row=0, column=2, pady=10)
        self.temp_slider.configure(command=self._update_temp_label)
        
        ctk.CTkLabel(params_frame, text="最大Token数:",
                     font=ctk.CTkFont(family="Microsoft YaHei", size=14),
                     text_color=COLORS["text"]).grid(row=1, column=0, sticky="w", pady=10)
        
        self.tokens_entry = ctk.CTkEntry(
            params_frame, placeholder_text="100-4000",
            height=40, corner_radius=8,
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Microsoft YaHei", size=FONT_SIZE)
        )
        self.tokens_entry.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(15, 0), pady=10)
        self.tokens_entry.insert(0, str(config.get("max_tokens", 500)))
        
        prompt_label = ctk.CTkLabel(content, text="系统提示词 (System Prompt):",
                                    font=ctk.CTkFont(family="Microsoft YaHei", size=14),
                                    text_color=COLORS["text"])
        prompt_label.grid(row=2, column=0, sticky="w", padx=30, pady=(20, 5))
        
        self.prompt_text = ctk.CTkTextbox(
            content, height=200, corner_radius=10,
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Microsoft YaHei", size=FONT_SIZE)
        )
        self.prompt_text.grid(row=3, column=0, sticky="nsew", padx=30, pady=(0, 10))
        self.prompt_text.insert("1.0", config.get("system_prompt", ""))
        
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.grid(row=4, column=0, pady=20)
        
        save_btn = StyledButton(btn_frame, "保存", width=150, height=40,
                               command=self.save_settings)
        save_btn.grid(row=0, column=0, padx=10)
        
        reset_btn = StyledButton(btn_frame, "恢复默认", style="secondary", width=150, height=40,
                                command=self.reset_settings)
        reset_btn.grid(row=0, column=1, padx=10)
    
    def _update_temp_label(self, value):
        self.temp_label.configure(text=f"{value:.1f}")
    
    def save_settings(self):
        try:
            temperature = round(self.temp_slider.get(), 2)
            max_tokens = int(self.tokens_entry.get().strip())
            if max_tokens < 100 or max_tokens > 4000:
                raise ValueError("Token数应在100-4000之间")
        except ValueError as e:
            messagebox.showerror("错误", f"参数错误: {e}")
            return
        
        system_prompt = self.prompt_text.get("1.0", "end").strip()
        
        update_func = getattr(settings, f"update_{self.prompt_type}_config", None)
        if update_func:
            update_func(temperature=temperature, max_tokens=max_tokens, system_prompt=system_prompt)
            messagebox.showinfo("成功", "设置已保存")
        else:
            messagebox.showerror("错误", "未知的配置类型")
    
    def reset_settings(self):
        default_settings = settings.DEFAULT_SETTINGS.get(self.prompt_type, {})
        
        self.temp_slider.set(default_settings.get("temperature", 0.5))
        self._update_temp_label(default_settings.get("temperature", 0.5))
        
        self.tokens_entry.delete(0, "end")
        self.tokens_entry.insert(0, str(default_settings.get("max_tokens", 500)))
        
        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", default_settings.get("system_prompt", ""))


class ReadmeFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.setup_ui()
    
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=40, pady=(30, 10))
        header.grid_columnconfigure(1, weight=1)
        
        back_btn = StyledButton(header, "← 返回", style="secondary", width=100, height=35,
                               command=lambda: self.app.show_frame("settings"))
        back_btn.grid(row=0, column=0, padx=10)
        
        title = ctk.CTkLabel(header, text="README",
                             font=ctk.CTkFont(family="Microsoft YaHei", size=24, weight="bold"),
                             text_color=COLORS["text"])
        title.grid(row=0, column=1, sticky="w", padx=20)
        
        content = CardFrame(self)
        content.grid(row=1, column=0, sticky="nsew", padx=40, pady=20)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)
        
        self.readme_text = ctk.CTkTextbox(
            content, wrap="word",
            font=ctk.CTkFont(family="Microsoft YaHei", size=FONT_SIZE),
            text_color=COLORS["text"],
            fg_color="transparent",
            corner_radius=0
        )
        self.readme_text.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        self.load_readme()
    
    def load_readme(self):
        readme_content = """# 故事生成器 - 使用指南

## 功能介绍

这是一个基于 AI 的交互式故事生成器，通过时间驱动的机制创造引人入胜的叙事体验。

### 核心功能

- **交互式叙事**：AI 根据你的行动生成连贯的故事
- **时间系统**：世界按天+时段推进（早晨、中午、下午、傍晚、夜晚）
- **事件节点**：预设关键事件在特定时间触发
- **世界大纲**：AI 自动生成或手动输入完整世界设定
- **故事续写**：节点完成后可续写新情节
- **存档编辑**：直接编辑存档数据

---

##  API 配置攻略

#### 方式一：使用硅基流动 API（推荐）

### 注册步骤

1. 访问注册链接：
   https://cloud.siliconflow.cn/i/nhJtWwFi

2. 注册账号（支持手机号/微信）

3. 进入控制台 → API 密钥 → 创建新密钥

4. 复制 API Key

### 在程序中配置

打开「设置」页面，填入：

┌────────────────────────────────────────┐
│ API Key:    sk-xxxxxxxxxxxxxxxxxxxxxxxx                                │
│ API URL:    https://api.siliconflow.cn/v1/chat/completions │
│ 模型:       deepseek-ai/DeepSeek-V3                                      │
└────────────────────────────────────────┘

### 推荐模型

| 模型名称 | 特点 | 
|---------|------|
| deepseek-ai/DeepSeek-V3 | 综合能力最强，中文优秀 |
| Qwen/Qwen2.5-72B-Instruct | 通义千问，中文理解好 |
| meta-llama/Llama-3.3-70B-Instruct | 英文能力强，英文故事 |

### 费用说明

- 新用户注册即送免费额度
- DeepSeek-V3.2 约 2元/百万token
- GLM-4-9B 免费使用（有限额）
- 按实际使用量计费，无最低消费

#### 方式二：使用 DeepSeek API

在程序的「设置」页面配置：
- **API Key**: 你的 DeepSeek API 密钥
- **API URL**: `https://api.deepseek.com/v1/chat/completions`
- **模型**: `deepseek-chat`

#### 方式三：其他兼容 OpenAI 格式的 API

任何兼容 OpenAI Chat Completions API 格式的服务都可以使用，只需修改 API URL 和模型名称。
---

## 快速开始

### 1. 配置 API（见上方攻略）

### 2. 开始新游戏

点击「开始新游戏」：
- **角色身份**（可选）：如"流浪剑客"、"东北农民"等
- **角色目标**（可选）：如"寻找神器"、"发家致富"等
- **世界大纲**：点击「自动生成大纲」或手动输入

### 3. 游戏操作

输入你的行动，AI 会生成故事发展。

---

## 时间系统

五个时段：早晨 → 中午 → 下午 → 傍晚 → 夜晚

### 时间跳过

输入指令快速跳过时间：
- "休息到第二天晚上"
- "等待三天后早晨"
- "睡到第五天中午"

**注意**：事件节点不会被跳过，会在故事中描述。

---

## 世界大纲

### 自动生成

点击「自动生成大纲」，AI 会生成完整设定：
- 世界观描述
- 主角身份和目标
- 5-15个事件节点

### 手动输入

支持多种题材：西幻、玄幻、科幻、都市、末世、仙侠、乡土现实等。

示例：
```
来自光之国的年轻奥特曼，因意外坠落地球，被人类少年的篮球比赛吸引，萌生了篮球梦。他化身人类少年，加入校园篮球队，却因力量难以控制、缺乏篮球技巧屡屡受挫。在队友的鼓励与教练的指导下，他学会收敛力量、精进技巧，逐渐融入团队。与此同时，怪兽突然出现，企图破坏城市篮球场。奥特曼在守护城市与追逐篮球梦之间找到平衡，一边和队友并肩备战市级联赛，一边在危机时刻变身守护家园，最终带领球队夺冠。
```

### 续写功能

所有节点完成后，在存档管理点击「续写」，AI 会生成新情节。

---

## AI 参数说明(不建议使用超过1.2的温度，可能会导致ai不遵循设置的输出规则而导致无法存档)

在「设置」→「AI 参数配置」中调整：

### 故事生成
- 温度 0.8：较有创意
- 最大Token 800：控制故事长度

### 大纲解析
- 温度 0.3：较严谨，确保解析准确

### 事件记录
- 温度 0.1：最严谨，简洁记录

### 世界大纲 / 故事续写
- 温度 0.9：很有创意

---

## 存档管理

- 自动创建存档
- 支持：读取、修改、删除
- 存档位置：程序目录 `saves` 文件夹

### 存档编辑器

可编辑：
- save.json：完整存档数据
- world_event.txt：事件记录

---

## 常见问题

Q: 生成失败？
A: 检查 API Key 是否正确，网络是否稳定。

Q: 故事质量不好？
A: 1) 使用更强的模型 2) 调高温度 3) 提供详细大纲

Q: 如何获得更好的大纲？
A: 在大纲文本框输入你的想法，AI 会基于此生成。

---

版本: 0.3.0
"""
        self.readme_text.insert("1.0", readme_content)
        self.readme_text.configure(state="disabled")


class SaveEditorFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.save_dir = None
        self.editing_save_num = None
        self.setup_ui()
    
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=40, pady=(30, 10))
        header.grid_columnconfigure(1, weight=1)
        
        self.back_btn = StyledButton(header, "← 返回", fg_color=COLORS["bg"], hover_color=COLORS["border"], width=100, height=35,
                               command=lambda: self.app.show_frame("game"))
        self.back_btn.grid(row=0, column=0, padx=10)
        
        self.title = ctk.CTkLabel(header, text="存档编辑器",
                             font=ctk.CTkFont(family="Microsoft YaHei", size=24, weight="bold"),
                             text_color=COLORS["text"])
        self.title.grid(row=0, column=1, sticky="w", padx=20)
        
        content = CardFrame(self)
        content.grid(row=1, column=0, sticky="nsew", padx=40, pady=20)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)
        
        self.tab_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.tab_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        
        self.tab_btn_save = StyledButton(self.tab_frame, "save.json", style="primary", width=120, height=32,
                                        command=lambda: self.switch_tab("save"))
        self.tab_btn_save.grid(row=0, column=0, padx=5)
        
        self.tab_btn_event = StyledButton(self.tab_frame, "world_event.txt", style="secondary", width=120, height=32,
                                         command=lambda: self.switch_tab("event"))
        self.tab_btn_event.grid(row=0, column=1, padx=5)
        
        self.editor_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.editor_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.editor_frame.grid_columnconfigure(0, weight=1)
        self.editor_frame.grid_rowconfigure(0, weight=1)
        
        self.save_editor = ctk.CTkTextbox(
            self.editor_frame, wrap="none",
            font=ctk.CTkFont(family="Consolas", size=13),
            text_color=COLORS["text"],
            fg_color=COLORS["input_bg"],
            corner_radius=10
        )
        self.save_editor.grid(row=0, column=0, sticky="nsew")
        
        self.event_editor = ctk.CTkTextbox(
            self.editor_frame, wrap="word",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=COLORS["text"],
            fg_color=COLORS["input_bg"],
            corner_radius=10
        )
        
        self.current_tab = "save"
        
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.grid(row=2, column=0, pady=15)
        
        save_btn = StyledButton(btn_frame, "保存修改", width=150, height=40,
                               command=self.save_changes)
        save_btn.grid(row=0, column=0, padx=10)
        
        reload_btn = StyledButton(btn_frame, "重新加载", style="secondary", width=150, height=40,
                                 command=self.refresh)
        reload_btn.grid(row=0, column=1, padx=10)
        
        self.status_label = ctk.CTkLabel(
            content, text="",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            text_color=COLORS["text_secondary"]
        )
        self.status_label.grid(row=3, column=0, pady=(0, 10))
    
    def set_save_number(self, save_num: int, return_to: str = "game"):
        self.editing_save_num = save_num
        self.save_dir = get_save_dir(save_num)
        self.return_to = return_to
        self.title.configure(text=f"存档编辑器 - save{save_num}")
        self.back_btn.configure(command=lambda: self.app.show_frame(return_to))
    
    def switch_tab(self, tab: str):
        if tab == self.current_tab:
            return
        
        self.current_tab = tab
        
        if tab == "save":
            self.tab_btn_save.configure(style="primary")
            self.tab_btn_event.configure(style="secondary")
            self.event_editor.grid_forget()
            self.save_editor.grid(row=0, column=0, sticky="nsew")
        else:
            self.tab_btn_save.configure(style="secondary")
            self.tab_btn_event.configure(style="primary")
            self.save_editor.grid_forget()
            self.event_editor.grid(row=0, column=0, sticky="nsew")
    
    def refresh(self):
        if self.editing_save_num:
            self.save_dir = get_save_dir(self.editing_save_num)
        elif self.app.state_mgr and self.app.state_mgr.save_number:
            self.editing_save_num = self.app.state_mgr.save_number
            self.save_dir = get_save_dir(self.editing_save_num)
        else:
            self.save_dir = None
        
        self.load_save_json()
        self.load_world_event()
        self.status_label.configure(text="")
    
    def load_save_json(self):
        self.save_editor.delete("1.0", "end")
        
        if not self.save_dir:
            self.save_editor.insert("1.0", "// 无存档加载")
            return
        
        save_path = os.path.join(self.save_dir, "save.json")
        if os.path.exists(save_path):
            try:
                with open(save_path, "r", encoding="utf-8") as f:
                    content = f.read()
                data = json.loads(content)
                formatted = json.dumps(data, ensure_ascii=False, indent=2)
                self.save_editor.insert("1.0", formatted)
            except Exception as e:
                self.save_editor.insert("1.0", f"// 加载失败: {e}")
        else:
            self.save_editor.insert("1.0", "// 存档文件不存在")
    
    def load_world_event(self):
        self.event_editor.delete("1.0", "end")
        
        if not self.save_dir:
            self.event_editor.insert("1.0", "// 无存档加载")
            return
        
        event_path = os.path.join(self.save_dir, "world_event.txt")
        if os.path.exists(event_path):
            try:
                with open(event_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.event_editor.insert("1.0", content)
            except Exception as e:
                self.event_editor.insert("1.0", f"// 加载失败: {e}")
        else:
            self.event_editor.insert("1.0", "// 事件文件不存在")
    
    def save_changes(self):
        if not self.save_dir:
            self.status_label.configure(text="错误：无存档加载", text_color=COLORS["danger"])
            return
        
        try:
            if self.current_tab == "save":
                content = self.save_editor.get("1.0", "end").strip()
                data = json.loads(content)
                
                save_path = os.path.join(self.save_dir, "save.json")
                with open(save_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                if self.app.state_mgr:
                    self.app.state_mgr.data = data
                
                self.status_label.configure(text="save.json 已保存", text_color=COLORS["success"])
            else:
                content = self.event_editor.get("1.0", "end").strip()
                
                event_path = os.path.join(self.save_dir, "world_event.txt")
                with open(event_path, "w", encoding="utf-8") as f:
                    f.write(content)
                
                self.status_label.configure(text="world_event.txt 已保存", text_color=COLORS["success"])
                
        except json.JSONDecodeError as e:
            self.status_label.configure(text=f"JSON 格式错误: {e}", text_color=COLORS["danger"])
        except Exception as e:
            self.status_label.configure(text=f"保存失败: {e}", text_color=COLORS["danger"])


class ContinueOutlineFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.save_num: Optional[int] = None
        self.state_mgr: Optional[StateManager] = None
        self.outline_generator: Optional[WorldOutlineGenerator] = None
        self.node_parser: Optional[NodeParser] = None
        self.is_generating = False
        self.current_outline = ""
        self.setup_ui()
    
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=40, pady=(30, 10))
        header.grid_columnconfigure(1, weight=1)
        
        back_btn = StyledButton(header, "← 返回", style="secondary", width=100, height=35,
                                command=lambda: self.app.show_frame("save_manager"))
        back_btn.grid(row=0, column=0, padx=10)
        
        self.title = ctk.CTkLabel(header, text="续写故事大纲",
                                   font=ctk.CTkFont(family="Microsoft YaHei", size=24, weight="bold"),
                                   text_color=COLORS["text"])
        self.title.grid(row=0, column=1, sticky="w", padx=20)
        
        content = CardFrame(self)
        content.grid(row=1, column=0, sticky="nsew", padx=40, pady=20)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(3, weight=1)
        
        info_frame = ctk.CTkFrame(content, fg_color="transparent")
        info_frame.grid(row=0, column=0, sticky="ew", padx=30, pady=(20, 10))
        info_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(info_frame, text="当前状态：",
                     font=ctk.CTkFont(family="Microsoft YaHei", size=14),
                     text_color=COLORS["text"]).grid(row=0, column=0, sticky="w")
        
        self.status_info = ctk.CTkLabel(info_frame, text="未加载存档",
                                        font=ctk.CTkFont(family="Microsoft YaHei", size=14),
                                        text_color=COLORS["text_secondary"])
        self.status_info.grid(row=0, column=1, sticky="w", padx=10)
        
        completed_frame = ctk.CTkFrame(content, fg_color="transparent")
        completed_frame.grid(row=1, column=0, sticky="ew", padx=30, pady=10)
        completed_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(completed_frame, text="已完成事件节点",
                     font=ctk.CTkFont(family="Microsoft YaHei", size=16),
                     text_color=COLORS["text"]).grid(row=0, column=0, sticky="w")
        
        self.completed_nodes_text = ctk.CTkTextbox(
            completed_frame, height=120, corner_radius=10,
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Microsoft YaHei", size=13)
        )
        self.completed_nodes_text.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        self.completed_nodes_text.configure(state="disabled")
        
        outline_header = ctk.CTkFrame(content, fg_color="transparent")
        outline_header.grid(row=2, column=0, sticky="ew", padx=30, pady=(15, 5))
        outline_header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(outline_header, text="续写内容",
                     font=ctk.CTkFont(family="Microsoft YaHei", size=16),
                     text_color=COLORS["text"]).grid(row=0, column=0, sticky="w")
        
        self.generate_btn = StyledButton(outline_header, "续写", width=100, height=35,
                                         command=self.generate_continue)
        self.generate_btn.grid(row=0, column=1, padx=5)
        
        self.outline_text = ctk.CTkTextbox(
            content, height=180, corner_radius=10,
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Microsoft YaHei", size=FONT_SIZE)
        )
        self.outline_text.grid(row=3, column=0, sticky="nsew", padx=30, pady=(0, 10))
        
        self.loading_label = ctk.CTkLabel(
            content, text="",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            text_color=COLORS["text_secondary"]
        )
        self.loading_label.grid(row=4, column=0, sticky="w", padx=30, pady=(0, 10))
        
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.grid(row=5, column=0, pady=20)
        
        confirm_btn = StyledButton(btn_frame, "确认续写", width=150, height=45,
                                   command=self.confirm_continue)
        confirm_btn.grid(row=0, column=0, padx=10)
        
        cancel_btn = StyledButton(btn_frame, "取消", style="secondary", width=150, height=45,
                                  command=lambda: self.app.show_frame("save_manager"))
        cancel_btn.grid(row=0, column=1, padx=10)
    
    def set_save_number(self, save_num: int):
        self.save_num = save_num
        self.title.configure(text=f"续写故事大纲 - save{save_num}")
        self.load_save_info()
    
    def load_save_info(self):
        if not self.save_num:
            return
        
        self.state_mgr = StateManager()
        if not self.state_mgr.load_save(self.save_num):
            self.status_info.configure(text="加载存档失败")
            return
        
        player = self.state_mgr.data.get("player", {})
        current_time = self.state_mgr.get_current_time()
        day, period = current_time
        period_cn = PERIOD_CN.get(period, period)
        
        self.status_info.configure(
            text=f"{player.get('identity', '未知')} | 第{day}天 {period_cn} | {player.get('location', '未知')}"
        )
        
        completed_nodes = [n for n in self.state_mgr.data.get("nodes", []) if n.get("triggered")]
        
        self.completed_nodes_text.configure(state="normal")
        self.completed_nodes_text.delete("1.0", "end")
        
        if completed_nodes:
            for node in completed_nodes:
                trigger_time = node.get("trigger_time", {})
                node_day = trigger_time.get("day", "?")
                node_period = trigger_time.get("period", "?")
                node_period_cn = PERIOD_CN.get(node_period, node_period)
                desc = node.get("description", node.get("name", "未知事件"))
                self.completed_nodes_text.insert("end", f"第{node_day}天{node_period_cn}：{desc}\n")
        else:
            self.completed_nodes_text.insert("1.0", "暂无已完成节点")
        
        self.completed_nodes_text.configure(state="disabled")
        self.outline_text.delete("1.0", "end")
        self.loading_label.configure(text="")
    
    def generate_continue(self):
        if self.is_generating:
            return
        
        if not self.state_mgr:
            messagebox.showerror("错误", "请先加载存档")
            return
        
        try:
            api_key = load_api_key()
            self.outline_generator = WorldOutlineGenerator(api_key)
            self.node_parser = NodeParser(api_key)
        except Exception as e:
            messagebox.showerror("错误", f"加载 API Key 失败: {e}")
            return
        
        self.is_generating = True
        self.generate_btn.configure(state="disabled", text="生成中...")
        self.loading_label.configure(text="正在生成续写内容...", text_color=COLORS["text_secondary"])
        self.outline_text.delete("1.0", "end")
        
        threading.Thread(target=self._generate_continue_thread, daemon=True).start()
    
    def _generate_continue_thread(self):
        try:
            world_description = self.state_mgr.data.get("world_description", "")
            history = self.state_mgr.data.get("history", [])
            completed_nodes = [n for n in self.state_mgr.data.get("nodes", []) if n.get("triggered")]
            current_time = self.state_mgr.get_current_time()
            player_location = self.state_mgr.data.get("player", {}).get("location", "未知")
            
            gen = self.outline_generator.generate_continue_outline_stream(
                world_description=world_description,
                history=history,
                completed_nodes=completed_nodes,
                current_time=current_time,
                player_location=player_location
            )
            
            full_text = ""
            for chunk in gen:
                full_text += chunk
                self.after(0, lambda c=chunk: self._append_outline_chunk(c))
            
            self.current_outline = full_text
            self.after(0, lambda: self.loading_label.configure(
                text="续写生成完成！可再次点击重新生成，或确认续写", 
                text_color=COLORS["success"]
            ))
            
        except Exception as e:
            self.after(0, lambda: self.loading_label.configure(
                text=f"生成失败: {str(e)}", 
                text_color=COLORS["danger"]
            ))
        finally:
            self.after(0, self._finish_generation)
    
    def _append_outline_chunk(self, chunk: str):
        self.outline_text.insert("end", chunk)
        self.outline_text.see("end")
    
    def _finish_generation(self):
        self.is_generating = False
        self.generate_btn.configure(state="normal", text="续写")
    
    def confirm_continue(self):
        if self.is_generating:
            return
        
        outline = self.outline_text.get("1.0", "end").strip()
        if not outline:
            messagebox.showwarning("提示", "请先生成续写内容")
            return
        
        if not self.state_mgr:
            messagebox.showerror("错误", "存档未加载")
            return
        
        if not self.node_parser:
            try:
                api_key = load_api_key()
                self.node_parser = NodeParser(api_key)
            except Exception as e:
                messagebox.showerror("错误", f"加载 API Key 失败: {e}")
                return
        
        try:
            new_nodes = self.node_parser.parse_outline(outline)
            
            if not new_nodes:
                messagebox.showwarning("提示", "未能从续写内容中解析出事件节点")
                return
            
            existing_nodes = self.state_mgr.data.get("nodes", [])
            max_id = max([n.get("id", 0) for n in existing_nodes], default=0)
            
            for i, node in enumerate(new_nodes):
                node["id"] = max_id + i + 1
                node["triggered"] = False
                existing_nodes.append(node)
            
            self.state_mgr.data["nodes"] = existing_nodes
            self.state_mgr.save_current()
            
            messagebox.showinfo("成功", f"续写成功！新增 {len(new_nodes)} 个事件节点")
            self.app.show_frame("save_manager")
            
        except Exception as e:
            messagebox.showerror("错误", f"续写失败: {str(e)}")
    
    def refresh(self):
        if self.save_num:
            self.load_save_info()


class App(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        super().__init__()
        
        self.title("故事生成器")
        self.geometry("1100x800")
        self.minsize(900, 700)
        
        self.center_window()
        
        self.configure(fg_color=COLORS["bg"])
        
        self.state_mgr: Optional[StateManager] = None
        self.engine: Optional[NarrativeEngine] = None
        self.parser: Optional[NodeParser] = None
        self.event_recorder: Optional[EventRecorder] = None
        
        self.frames = {}
        self.current_frame = None
        
        self.create_frames()
        self.show_frame("start")
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        x = (self.winfo_screenwidth() - width) // 2 - 100
        y = (self.winfo_screenheight() - height) // 2 - 200
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_frames(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)
        
        self.container = container
        
        self.frames["start"] = StartFrame(container, self)
        self.frames["new_game"] = NewGameFrame(container, self)
        self.frames["game"] = GameFrame(container, self)
        self.frames["save_manager"] = SaveManagerFrame(container, self)
        self.frames["save_editor"] = SaveEditorFrame(container, self)
        self.frames["settings"] = SettingsFrame(container, self)
        self.frames["readme"] = ReadmeFrame(container, self)
        self.frames["continue_outline"] = ContinueOutlineFrame(container, self)
        
        prompt_configs = [
            ("narrative", "故事生成"),
            ("node_parser", "大纲解析"),
            ("event_recorder", "事件记录"),
            ("world_outline", "世界大纲"),
            ("continue_outline", "故事续写")
        ]
        for key, name in prompt_configs:
            self.frames[f"prompt_{key}"] = PromptSettingsFrame(container, self, key, name)
        
        for frame in self.frames.values():
            frame.grid(row=0, column=0, sticky="nsew")
    
    def show_frame(self, name: str):
        if name in self.frames:
            frame = self.frames[name]
            if hasattr(frame, 'refresh'):
                frame.refresh()
            frame.tkraise()
            self.current_frame = name
    
    def start_new_game(self, identity: str, goal: str, outline: str = ""):
        try:
            api_key = load_api_key()
        except Exception as e:
            messagebox.showerror("错误", f"加载 API Key 失败: {e}")
            return
        
        self.state_mgr = StateManager()
        
        # ===== 以下为快速本地操作，可在主线程执行 =====
        if outline.strip():
            try:
                outline_gen = WorldOutlineGenerator(api_key)
                world_info = outline_gen.extract_world_info(outline)
                
                if not identity and world_info.get("player_identity"):
                    identity = world_info["player_identity"].split("，")[0].strip()
                if not goal and world_info.get("player_goal"):
                    goal = world_info["player_goal"]
                
                if world_info.get("world_description"):
                    self.state_mgr.data["world_description"] = world_info["world_description"]
            except Exception as e:
                print(f"解析大纲信息失败: {e}")
        
        if not identity:
            identity = "冒险者"
        if not goal:
            goal = "探索这个世界"
        
        self.state_mgr.data["player"]["identity"] = identity
        self.state_mgr.data["player"]["goal"] = goal
        
        save_num = self.state_mgr.new_save()
        
        self.engine = NarrativeEngine(api_key)
        self.parser = NodeParser(api_key)
        self.event_recorder = EventRecorder(api_key)
        self.engine.set_event_recorder(self.event_recorder)
        
        # ===== 先显示游戏界面，让用户看到进度 =====
        self.frames["game"].set_state_manager(self.state_mgr, self.engine)
        self.show_frame("game")
        
        # ===== 以下为耗时操作，放入子线程执行 =====
        # 子线程任务：1. AI解析大纲节点  2. AI生成初始世界
        threading.Thread(target=self._start_new_game_thread, args=(identity, goal, outline), daemon=True).start()
    
    def _start_new_game_thread(self, identity: str, goal: str, outline: str):
        """子线程：执行耗时的 AI 解析大纲和生成初始世界"""
        game_frame = self.frames["game"]
        
        # 显示加载状态
        self.after(0, lambda: game_frame.loading_label.configure(text="正在解析大纲节点...", text_color=COLORS["text_secondary"]))
        self.after(0, lambda: game_frame.submit_btn.configure(state="disabled"))
        
        # ===== 耗时操作1：AI 解析大纲为节点 =====
        if outline.strip():
            try:
                nodes = self.parser.parse_outline(outline)
                if nodes:
                    for i, n in enumerate(nodes):
                        n["id"] = i + 1
                        n["triggered"] = False
                    self.state_mgr.node_mgr.load_nodes(nodes)
                    # 保存解析结果到存档
                    self.state_mgr.save_current()
            except Exception as e:
                print(f"解析大纲失败: {e}")
        
        # ===== 耗时操作2：AI 生成初始世界 =====
        self.after(0, lambda: game_frame.loading_label.configure(text="正在生成初始世界..."))
        
        try:
            story, ai_json = self.engine.generate_story(
                "（新世界，无历史）",
                (1, "morning"),
                [],
                f"生成初始世界描述，玩家是{identity}，目标是{goal}",
                identity
            )
            
            self.after(0, lambda: game_frame.update_story(story))
            
            if ai_json:
                self.state_mgr.update_from_ai_response(ai_json)
                if "player_changes" in ai_json and "location" in ai_json.get("player_changes", {}):
                    self.state_mgr.data["player"]["location"] = ai_json["player_changes"]["location"]
                elif not self.state_mgr.data["player"].get("location"):
                    self.state_mgr.data["player"]["location"] = "旅店"
            else:
                self.state_mgr.data["player"]["location"] = "旅店"
            
            self.state_mgr.data["history"].append({
                "time": "第1天早晨",
                "event": f"{identity}开始了冒险旅程"
            })
            
            self.state_mgr.save_summary_log()
            self.state_mgr.save_current()
            
            self.after(0, game_frame.update_status)
            self.after(0, game_frame.update_time_display)
            
        except Exception as e:
            self.after(0, lambda: game_frame.update_story(f"生成初始世界失败: {e}\n请尝试重新开始游戏。"))
            self.state_mgr.data["player"]["location"] = "旅店"
            self.state_mgr.data["world_description"] = f"一个充满冒险的世界，{identity}开始了旅程。"
        finally:
            self.after(0, lambda: game_frame.submit_btn.configure(state="normal"))
            self.after(0, lambda: game_frame.loading_label.configure(text=""))
    
    def load_game(self, save_num: int) -> bool:
        try:
            api_key = load_api_key()
        except Exception as e:
            messagebox.showerror("错误", f"加载 API Key 失败: {e}")
            return False
        
        self.state_mgr = StateManager()
        if not self.state_mgr.load_save(save_num):
            messagebox.showerror("错误", "加载存档失败")
            return False
        
        self.engine = NarrativeEngine(api_key)
        self.event_recorder = EventRecorder(api_key)
        self.engine.set_event_recorder(self.event_recorder)
        
        self.frames["game"].set_state_manager(self.state_mgr, self.engine)
        
        summary = self.state_mgr.get_world_summary()
        self.frames["game"].update_story(f"已加载存档 save{save_num}\n\n{summary}", append=False)
        
        return True
    
    def on_closing(self):
        self.destroy()


def run_gui():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
