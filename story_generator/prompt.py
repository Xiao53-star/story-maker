from story_generator.config import PERIOD_CN

NARRATIVE_TEMPERATURE = 0.8

NARRATIVE_MAX_TOKENS = 800
NARRATIVE_MAX_TOKENS1 = NARRATIVE_MAX_TOKENS - 200

NODE_PARSER_TEMPERATURE = 0.3

NODE_PARSER_MAX_TOKENS = 2000

NARRATIVE_SYSTEM_PROMPT = "你是一个交互式故事生成器，擅长创造引人入胜的叙事体验。"

NARRATIVE_PROMPT_TEMPLATE = """你是一个交互式故事生成器。世界设定如下：
{world_summary}

当前时间：第{day}天 {period_cn}。
未来事件节点：{node_section}
玩家行动：{player_input}

请描述故事。故事要生动有趣，体现角色特点和世界氛围。

【事件节点处理规则】
未来事件节点列出了所有尚未触发的预定事件及其触发时间。你需要：
1. 如果当前时间正好是某个节点的触发时间，必须将该事件融入故事中
2. 如果玩家输入包含时间跳过意图，跳过期间经过的所有节点事件都必须在故事中描述

【时间跳过规则 - 重要】
你需要智能判断玩家输入是否包含时间跳过意图。任何表达想要"让时间流逝到某个时刻"的意图都应该被识别，包括但不限于：
- 直接表达：休息到/睡到/等到/跳过到/休息至/睡至/等至/跳过至
- 间接表达：我想休息、睡一觉、打发时间、等待、暂停、消磨时间
- 时间表达：明天见、三天后、过几天、下个早晨、到了晚上
- 状态表达：睡个觉、打个盹、休息一下、等天亮、等天黑

如果识别到时间跳过意图，你需要：
1. 根据玩家输入推断目标时间（目标天数和时段），如果玩家没有指定具体时间，合理推断（如"睡一觉"默认跳到下2个时段）
2. 检查跳过期间是否有事件节点，如果有，必须在故事中描述这些事件是如何在跳过期间发生的
3. 生成 time_skip 字段指定目标时间

故事结束后，另起一行输出 [STATE] 标签，内附 JSON 描述世界变化，格式如下：
[STATE]
{{
  "new_characters": [{{"name": "名字", "location": "位置", "attitude": 态度数值, "status": "状态"}}],
  "character_changes": {{"角色名": {{"attitude": 变化值, "location": "新位置"}}}},
  "location_changes": {{"地点名": {{"status": "新状态"}}}},
  "player_changes": {{"inventory": {{"添加": ["物品"], "移除": ["物品"]}}, "location": "新位置"}},
  "history_entry": "本次事件简短描述（不超过50字）",
  "time_advance": {{"periods": 1}},
  "time_skip": {{"target_day": 目标天数, "target_period": "目标时段"}}
}}
[/STATE]

注意：
1. 只在必要时才添加新角色或改变状态
2. 态度数值范围 -100 到 100，正值友好，负值敌对
3. time_advance 用于正常推进时间（1-5个时段），time_skip 用于跳过到指定时间
4. time_skip 和 time_advance 只能使用其中一个，有 time_skip 时忽略 time_advance
5. 时段可选值：morning（早晨）、noon（中午）、afternoon（下午）、evening（傍晚）、night（夜晚）
6. 如果没有变化，可以返回空对象 {{}}
7. 除了所要求的json格式的输出，其他所有输出不得含有 '['字符
8. 禁止提前发生未来世界节点事件，所有时间节点事件必须在对应时间发生
9. 所有输出必须在 {NARRATIVE_MAX_TOKENS1} 个 token 内

"""

NODE_PARSER_SYSTEM_PROMPT = "你是一个故事大纲解析器，擅长将故事大纲分解为结构化的事件节点。"

NODE_PARSER_PROMPT_TEMPLATE = """请将以下故事大纲解析为事件节点列表。

大纲内容：
{user_input}

要求：
1. 将大纲分解为若干关键事件节点并进行合理的拓展
2. 每个节点包含：name（事件名称）、trigger_time（触发时间，含day和period）、description（事件描述）
3. 时段可选值：{periods}
4. 按时间顺序排列

请输出 JSON 数组格式：
[
  {{
    "name": "事件名称",
    "trigger_time": {{"day": 1, "period": "morning"}},
    "description": "事件详细描述"
  }}
]

只输出 JSON 数组，不要其他解释。"""

def format_period_cn(period: str) -> str:
    return PERIOD_CN.get(period, period)


def format_node_with_time(node: dict) -> str:
    trigger_time = node.get("trigger_time", {})
    trigger_day = trigger_time.get("day", "?")
    trigger_period = trigger_time.get("period", "?")
    period_cn = format_period_cn(trigger_period)
    desc = node.get("description", node.get("name", "未知事件"))
    return f"- 第{trigger_day}天{period_cn}：{desc}"


def build_node_section(pending_nodes: list, is_time_skip: bool = False) -> str:
    if not pending_nodes:
        return "无"
    
    node_details = "\n".join(format_node_with_time(n) for n in pending_nodes)
    return f"\n{node_details}\n"


def build_narrative_prompt(world_summary: str, current_time: tuple, 
                           pending_nodes: list, player_input: str, 
                           player_identity: str, player_location: str = "") -> str:
    day, period = current_time
    period_cn = format_period_cn(period)
    node_section = build_node_section(pending_nodes)
    
    return NARRATIVE_PROMPT_TEMPLATE.format(
        world_summary=world_summary,
        day=day,
        period_cn=period_cn,
        node_section=node_section,
        player_identity=player_identity,
        player_location=player_location or "未知",
        player_input=player_input,
        NARRATIVE_MAX_TOKENS1=NARRATIVE_MAX_TOKENS1
    )

def build_node_parser_prompt(user_input: str, period_order: list) -> str:
    periods = "、".join(period_order)
    return NODE_PARSER_PROMPT_TEMPLATE.format(user_input=user_input, periods=periods)

EVENT_RECORDER_TEMPERATURE = 0.1

EVENT_RECORDER_MAX_TOKENS = 300

EVENT_RECORDER_SYSTEM_PROMPT = "你是一个事件记录员，擅长从故事中提取关键事件并精简记录。"

EVENT_RECORDER_PROMPT_TEMPLATE = """请从以下故事片段中提取关键事件，精简记录。

时间：第{day}天 {period_cn}
故事内容：
{story_text}

要求：
1. 提取最重要的1-3个事件
2. 每个事件用一句话描述（不超过30字）
3. 包含关键人物、地点、行动、结果
4. 按重要性排列
5. 格式：事件1；事件2；事件3

只输出事件描述，不要其他内容。"""


WORLD_OUTLINE_TEMPERATURE = 0.9

WORLD_OUTLINE_MAX_TOKENS = 2000

WORLD_OUTLINE_SYSTEM_PROMPT = "你是一个世界大纲生成器，擅长创造完整、引人入胜的故事大纲，并能基于现有内容进行续写扩展。"

WORLD_OUTLINE_PROMPT_TEMPLATE = """请生成一个完整的世界大纲。

{input_section}

要求：
1. 创造一个完整、有吸引力的故事大纲
2. 大纲应包含以下要素：
   - 世界观设定（世界类型、背景、规则）
   - 主要角色（主角身份、性格特点）
   - 核心冲突（主要矛盾、挑战）
   - 故事主线（起承转合的关键事件）
3. 大纲需要能被拆解为多个时间节点的事件
4. 事件按时间顺序排列，每个事件有明确的触发时间
5. 语言简洁有力，精简描述，避免各心理，动作等描写

请按以下格式输出：

【世界观】
（描述世界设定，如：西幻/玄幻/科幻/都市等，世界背景，特殊规则）

【主角】
（主角身份、特点、初始状态）

【核心目标】
（主角的主要目标和动机）

【主角经历】
（主角的主要经历，一整段话输出）
...

注意：
- 主角经历应包含7-13个关键事件
- 主要经历间的时间跨度建议在3-10天
- 确保故事有起承转合的完整结构"""

WORLD_OUTLINE_RANDOM_PROMPT = """请随机生成一个完整的世界大纲。

题材不限，可以是：西幻、玄幻、都市、末世、仙侠等类型。
{identity_section}
{goal_section}
要求：
1. 创造一个完整、有吸引力的故事大纲
2. 大纲应包含以下要素：
   - 世界观设定（世界类型、背景、规则）
   - 主要角色（主角身份、性格特点）
   - 核心冲突（主要矛盾、挑战）
   - 故事主线（起承转合的关键事件）
3. 大纲需要能被拆解为多个时间节点的事件
4. 事件按时间顺序排列，每个事件有明确的触发时间
5. 语言简洁有力，适合游戏叙事

请按以下格式输出：

【世界观】
（描述世界设定，如：西幻/玄幻/科幻/都市等，世界背景，特殊规则）

【主角】
（主角身份、特点、初始状态）

【核心目标】
（主角的主要目标和动机）

【主角经历】
（主角的主要经历，一整段话输出）
...

注意：
- 主角经历应包含7-13个关键事件
- 主要经历间的时间跨度建议在3-10天
- 确保故事有起承转合的完整结构"""


CONTINUE_OUTLINE_TEMPERATURE = 0.9

CONTINUE_OUTLINE_MAX_TOKENS = 2000

CONTINUE_OUTLINE_SYSTEM_PROMPT = "你是一个故事续写专家，擅长基于现有故事内容进行连贯、精彩的续写扩展。"

CONTINUE_OUTLINE_PROMPT_TEMPLATE = """请基于以下已有内容，续写扩展故事大纲。

【已有世界观】
{world_description}

【已有历史事件】
{history_summary}

【已完成事件节点】
{completed_nodes}

【当前状态】
时间：第{current_day}天 {current_period}
主角位置：{player_location}

要求：
1. 严格继承原有世界观和设定
2. 续写内容要与已有故事自然衔接
3. 创造新的冲突和挑战，推动故事发展
4. 保持故事风格的一致性
5. 续写内容应能被拆解为新的时间节点事件

请按以下格式输出续写内容：

【续写事件节点】
第X天早晨：事件描述
第X天中午：事件描述
...

注意：
- 续写事件从当前时间之后开始
- 新增3-8个事件节点
- 每个事件描述简洁（20-50字）
- 确保与已完成内容无缝衔接
- 引入新的挑战或转折"""


def build_world_outline_prompt(user_input: str = "", identity: str = "", goal: str = "") -> str:
    identity_section = f"\n主角身份：{identity}" if identity else ""
    goal_section = f"\n主角目标：{goal}" if goal else ""
    
    if user_input.strip():
        input_section = f"玩家输入：{user_input}"
        if identity:
            input_section += f"\n主角身份：{identity}"
        if goal:
            input_section += f"\n主角目标：{goal}"
        return WORLD_OUTLINE_PROMPT_TEMPLATE.format(input_section=input_section)
    else:
        return WORLD_OUTLINE_RANDOM_PROMPT.format(
            identity_section=identity_section,
            goal_section=goal_section
        )


def build_continue_outline_prompt(world_description: str, history_summary: str,
                                   completed_nodes: str, current_day: int,
                                   current_period: str, player_location: str) -> str:
    return CONTINUE_OUTLINE_PROMPT_TEMPLATE.format(
        world_description=world_description,
        history_summary=history_summary,
        completed_nodes=completed_nodes,
        current_day=current_day,
        current_period=current_period,
        player_location=player_location
    )
