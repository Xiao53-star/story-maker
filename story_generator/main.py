import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from story_generator.config import PERIOD_CN, list_all_saves, get_save_dir
from story_generator.state_manager import StateManager
from story_generator.narrative_engine import NarrativeEngine
from story_generator.node_parser import NodeParser
from story_generator.event_recorder import EventRecorder
from story_generator.utils import multiline_input, load_api_key


def handle_command(cmd: str, state_mgr: StateManager) -> bool:
    parts = cmd.split(maxsplit=1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    
    if command == "/save":
        state_mgr.save_current()
        print(f"游戏已保存至 save{state_mgr.save_number}")
        return True
    
    elif command == "/load":
        saves = list_all_saves()
        if not saves:
            print("没有可用的存档")
            return True
        
        if args.strip():
            try:
                save_num = int(args.strip().replace("save", ""))
                if state_mgr.load_save(save_num):
                    print(f"已加载存档 save{save_num}")
                    day, period = state_mgr.get_current_time()
                    period_cn = PERIOD_CN.get(period, period)
                    print(f"当前时间：第{day}天 {period_cn}")
                else:
                    print(f"存档 save{save_num} 不存在")
            except ValueError:
                print("请输入有效的存档编号")
        else:
            print("\n可用存档：")
            for i, save in enumerate(saves, 1):
                player = save.get("player", {})
                time_info = save.get("time", {})
                last_saved = save.get("last_saved", "未知")
                print(f"  {i}. {save['name']} - {player.get('identity', '未知')} "
                      f"(第{time_info.get('day', '?')}天) - {last_saved}")
            
            print("\n请输入存档编号（1-{}）：".format(len(saves)), end="")
            try:
                choice = int(input().strip())
                if 1 <= choice <= len(saves):
                    save_name = saves[choice - 1]["name"]
                    save_num = int(save_name.replace("save", ""))
                    if state_mgr.load_save(save_num):
                        print(f"已加载存档 {save_name}")
                        day, period = state_mgr.get_current_time()
                        period_cn = PERIOD_CN.get(period, period)
                        print(f"当前时间：第{day}天 {period_cn}")
                else:
                    print("无效的选择")
            except ValueError:
                print("请输入数字")
        return True
    
    elif command == "/time":
        day, period = state_mgr.get_current_time()
        print(f"当前时间：第{day}天 {PERIOD_CN.get(period, period)}")
        return True
    
    elif command == "/status":
        player = state_mgr.data.get("player", {})
        print(f"角色：{player.get('identity', '未知')}")
        print(f"位置：{player.get('location', '未知')}")
        print(f"目标：{player.get('goal', '未知')}")
        print(f"背包：{', '.join(player.get('inventory', [])) or '空'}")
        stats = player.get("stats", {})
        print(f"生命值：{stats.get('health', 100)}  金钱：{stats.get('money', 0)}")
        return True
    
    elif command == "/help":
        print("可用命令：")
        print("  /save - 保存游戏")
        print("  /load [编号] - 加载存档（不填编号则显示列表）")
        print("  /time - 显示当前时间")
        print("  /status - 显示角色状态")
        print("  /help - 显示帮助")
        print("  /quit - 退出游戏")
        return True
    
    elif command == "/quit":
        print("感谢游玩！")
        return False
    
    else:
        print(f"未知命令: {command}，输入 /help 查看帮助")
        return True


def confirm_nodes(nodes: list[dict]) -> bool:
    print("\n解析到以下事件节点：")
    for i, node in enumerate(nodes, 1):
        tt = node.get("trigger_time", {})
        day = tt.get("day", "?")
        period = tt.get("period", "?")
        period_cn = PERIOD_CN.get(period, period)
        print(f"  {i}. [{day}天{period_cn}] {node.get('name', '未知')}")
        print(f"     描述：{node.get('description', '无')[:50]}...")
    
    print("\n是否使用这些节点？(y/n): ", end="")
    choice = input().strip().lower()
    return choice == 'y'


def select_save_or_new() -> tuple[StateManager, bool]:
    saves = list_all_saves()
    
    if not saves:
        print("\n没有找到存档，将创建新游戏。")
        state_mgr = StateManager()
        return state_mgr, True
    
    print("\n" + "=" * 50)
    print("    存档选择")
    print("=" * 50)
    print("\n可用存档：")
    for i, save in enumerate(saves, 1):
        player = save.get("player", {})
        time_info = save.get("time", {})
        last_saved = save.get("last_saved", "未知")
        identity = player.get("identity", "未知")
        day = time_info.get("day", "?")
        print(f"  {i}. {save['name']} - {identity} (第{day}天) - {last_saved}")
    
    print(f"  {len(saves) + 1}. 新建游戏")
    print("  0. 退出")
    
    while True:
        print(f"\n请选择 (0-{len(saves) + 1})：", end="")
        try:
            choice = int(input().strip())
            
            if choice == 0:
                print("再见！")
                return None, False
            
            if choice == len(saves) + 1:
                state_mgr = StateManager()
                return state_mgr, True
            
            if 1 <= choice <= len(saves):
                save_name = saves[choice - 1]["name"]
                save_num = int(save_name.replace("save", ""))
                state_mgr = StateManager()
                if state_mgr.load_save(save_num):
                    print(f"\n已加载存档 {save_name}")
                    day, period = state_mgr.get_current_time()
                    period_cn = PERIOD_CN.get(period, period)
                    print(f"当前时间：第{day}天 {period_cn}")
                    return state_mgr, False
                else:
                    print(f"加载存档失败，请重新选择")
            else:
                print("无效的选择，请重新输入")
        except ValueError:
            print("请输入数字")


def main():
    print("=" * 50)
    print("    故事生成器 - 时间驱动版")
    print("=" * 50)
    
    try:
        api_key = load_api_key()
    except Exception as e:
        print(f"加载 API Key 失败: {e}")
        return
    
    state_mgr, is_new_game = select_save_or_new()
    
    if state_mgr is None:
        return
    
    engine = NarrativeEngine(api_key)
    parser = NodeParser(api_key)
    event_recorder = EventRecorder(api_key)
    engine.set_event_recorder(event_recorder)
    
    if is_new_game:
        print("\n请设定你的角色身份（如：流浪剑客、神秘法师、商队护卫等）：")
        identity = input("> ").strip()
        if not identity:
            identity = "冒险者"
        state_mgr.data["player"]["identity"] = identity
        
        print("\n请设定你的角色目标（如：寻找神器、复仇、探索世界等）：")
        goal = input("> ").strip()
        if not goal:
            goal = "探索这个世界"
        state_mgr.data["player"]["goal"] = goal
        
        save_num = state_mgr.new_save()
        print(f"\n已创建存档 save{save_num}")
        
        print("\n是否输入世界大纲？(y/n): ", end="")
        if input().strip().lower() == 'y':
            print("请输入世界大纲（空行结束）：")
            outline = multiline_input("")
            if outline.strip():
                print("正在解析大纲...")
                try:
                    nodes = parser.parse_outline(outline)
                    if nodes and confirm_nodes(nodes):
                        for i, n in enumerate(nodes):
                            n["id"] = i + 1
                            n["triggered"] = False
                        state_mgr.node_mgr.load_nodes(nodes)
                        print(f"已加载 {len(nodes)} 个事件节点")
                except Exception as e:
                    print(f"解析大纲失败: {e}")
        
        print("\n正在生成初始世界...")
        try:
            story, ai_json = engine.generate_story(
                "（新世界，无历史）",
                (1, "morning"),
                [],
                f"生成初始世界描述，玩家是{identity}，目标是{goal}",
                identity
            )
            print("\n" + "=" * 50)
            print(story)
            print("=" * 50)
            
            if ai_json:
                state_mgr.update_from_ai_response(ai_json)
                if "player_changes" in ai_json and "location" in ai_json.get("player_changes", {}):
                    state_mgr.data["player"]["location"] = ai_json["player_changes"]["location"]
                elif not state_mgr.data["player"].get("location"):
                    state_mgr.data["player"]["location"] = "旅店"
            else:
                state_mgr.data["player"]["location"] = "旅店"
                
        except Exception as e:
            print(f"生成初始世界失败: {e}")
            state_mgr.data["player"]["location"] = "旅店"
            state_mgr.data["world_description"] = f"一个充满冒险的世界，{identity}开始了旅程。"
        
        state_mgr.data["history"].append({
            "time": "第1天早晨",
            "event": f"{identity}开始了冒险旅程"
        })
        
        state_mgr.save_summary_log()
        state_mgr.save_current()
    
    print("\n游戏开始！输入行动描述来进行游戏，输入 /help 查看命令。")
    
    while True:
        day, period = state_mgr.get_current_time()
        period_cn = PERIOD_CN.get(period, period)
        print(f"\n【第{day}天 {period_cn}】")
        print("> ", end="")
        
        try:
            cmd = input().strip()
        except EOFError:
            break
        
        if not cmd:
            continue
        
        if cmd.startswith('/'):
            if not handle_command(cmd, state_mgr):
                break
            continue
        
        summary = state_mgr.get_world_summary()
        cur_time = state_mgr.get_current_time()
        pending = state_mgr.check_nodes()
        
        try:
            story, ai_json = engine.generate_story(
                summary, cur_time, pending, cmd,
                state_mgr.data["player"].get("identity", "冒险者"),
                state_mgr.data["player"].get("location", "")
            )
            
            print("\n" + "-" * 40)
            print(story)
            print("-" * 40)
            
            if ai_json:
                state_mgr.update_from_ai_response(ai_json)
                periods = ai_json.get("time_advance", {}).get("periods", 1)
            else:
                periods = 1
            
            state_mgr.advance_time(periods)
            
            if pending:
                state_mgr.mark_nodes_triggered(pending)
            
            state_mgr.save_summary_log()
                
        except Exception as e:
            print(f"生成故事时出错: {e}")
            print("请重试或使用 /save 保存游戏")


if __name__ == "__main__":
    main()
