# 故事生成器

基于 Python 的交互式故事生成器。玩家设定角色，通过文字行动；AI 根据世界状态、时间和预设事件节点生成剧情。世界以"天+时段"推进，节点事件强制发生。

## 功能特点

- **图形界面**：现代化的深色主题 GUI，基于 CustomTkinter
- **交互式叙事**：AI 根据玩家行动生成连贯的故事
- **时间系统**：世界按天+时段推进（早晨、中午、下午、傍晚、夜晚）
- **时间跳过**：支持快速跳过时间，事件节点不会被忽略
- **事件节点**：预设关键事件在特定时间触发
- **世界大纲自动生成**：AI 自动生成完整的世界设定和事件节点
- **故事续写**：当所有事件节点完成后，可续写生成新的情节
- **存档编辑器**：直接编辑存档 JSON 和事件记录
- **世界一致性**：多个 AI 协同工作，保证剧情连贯
- **本地存储**：JSON 存档，支持保存/读取
- **可配置**：通过设置界面配置 API 和 AI 参数

## 系统架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  叙事 AI    │────▶│   事件记录 AI │────▶│  状态管理     │
│ (生成故事)   │     │  (精简事件)   │     │ (世界摘要)   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
  story_log.txt      world_event.txt     save.json
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行程序

```bash
python -m story_generator.gui
```

或使用命令行版本：(功能缺失，bug很多)

```bash
python -m story_generator.main
```

### 3. 配置 API

#### 方式一：使用硅基流动 API（推荐）

硅基流动提供多种开源大模型的 API 服务，价格实惠，响应快速。

**注册步骤：**
1. 访问 [硅基流动云平台](https://cloud.siliconflow.cn/i/nhJtWwFi) 注册账号
2. 进入控制台，获取 API Key
3. 在程序「设置」页面填入：
   - **API Key**: 你的硅基流动 API Key
   - **API URL**: `https://api.siliconflow.cn/v1/chat/completions`
   - **模型**: 推荐使用 `deepseek-ai/DeepSeek-V3` 或 `Qwen/Qwen2.5-72B-Instruct`

**推荐模型：**
| 模型名称 | 特点 | 适用场景 |
|---------|------|---------|
| `deepseek-ai/DeepSeek-V3` | 综合能力强，中文优秀 | 故事生成、大纲解析 |
| `Qwen/Qwen2.5-72B-Instruct` | 通义千问，中文理解好 | 故事生成 |
| `THUDM/glm-4-9b-chat` | 智谱GLM，免费额度 | 测试使用 |

#### 方式二：使用 DeepSeek API

在程序的「设置」页面配置：
- **API Key**: 你的 DeepSeek API 密钥
- **API URL**: `https://api.deepseek.com/v1/chat/completions`
- **模型**: `deepseek-chat`

#### 方式三：其他兼容 OpenAI 格式的 API

任何兼容 OpenAI Chat Completions API 格式的服务都可以使用，只需修改 API URL 和模型名称。

#### 方式四：环境变量或配置文件

```python
# 在 story_generator/config.py 中设置
DEEPSEEK_API_KEY = "your_api_key_here"
```

或创建 `.env` 文件：

```
DEEPSEEK_API_KEY=your_api_key_here
```

或设置环境变量：

```bash
export DEEPSEEK_API_KEY=your_api_key_here
```

### 4. 开始游戏

1. 点击「开始新游戏」
2. 填写角色身份和目标（可选）
3. 点击「自动生成大纲」或手动输入世界大纲
4. 开始冒险！

## 游戏命令

| 命令 | 说明 |
|------|------|
| `/save` | 保存游戏 |
| `/time` | 显示当前时间 |
| `/status` | 显示角色状态 |
| `/help` | 显示帮助 |
| `/quit` | 返回主菜单 |

## 时间系统

游戏时间分为五个时段：
- 早晨 (morning)
- 中午 (noon)
- 下午 (afternoon)
- 傍晚 (evening)
- 夜晚 (night)

每次行动后时间会自动推进。

### 时间跳过

你可以通过输入特定指令快速跳过时间：
- "休息到第二天晚上"
- "等待三天后早晨"
- "睡到第五天中午"
- "跳过到第10天夜晚"

**注意**：跳过期间如果有预定的事件节点，这些事件会在故事中得到描述和解决，不会被忽略。

## 世界大纲系统

### 自动生成大纲

点击「自动生成大纲」按钮，AI 会生成完整的世界大纲，包含：
- 世界观设定
- 主角身份
- 核心目标
- 事件节点（5-15个）

你可以在文本框中输入主题想法，AI 会基于你的输入生成大纲。

### 手动输入大纲

支持多种题材：西幻、玄幻、科幻、都市、末世、仙侠、赛博朋克、乡土现实等。

示例大纲：
```
来自光之国的年轻奥特曼，因意外坠落地球，被人类少年的篮球比赛吸引，萌生了篮球梦。他化身人类少年，加入校园篮球队，却因力量难以控制、缺乏篮球技巧屡屡受挫。在队友的鼓励与教练的指导下，他学会收敛力量、精进技巧，逐渐融入团队。与此同时，怪兽突然出现，企图破坏城市篮球场。奥特曼在守护城市与追逐篮球梦之间找到平衡，一边和队友并肩备战市级联赛，一边在危机时刻变身守护家园，最终带领球队夺冠。
```

### 事件节点

大纲会被解析为事件节点，在特定时间触发。节点格式：
```
第1天早晨：事件描述
第2天傍晚：事件描述
```

### 续写功能

当所有事件节点完成后，可以在存档管理中点击「续写」，AI 会基于已有故事生成新的情节和事件节点。

## 文件结构

```
story_generator/
├── __init__.py                # 模块导出
├── config.py                  # 配置（API Key、文件路径等）
├── prompt.py                  # AI 提示词模板
├── utils.py                   # 工具函数
├── settings.py                # 设置管理
├── state_manager.py           # 状态管理器
├── narrative_engine.py        # 叙事引擎
├── node_parser.py             # 节点解析器
├── event_recorder.py          # 事件记录器
├── world_outline_generator.py # 世界大纲生成器
├── api_client.py              # API 客户端
├── gui.py                     # 图形界面
└── main.py                    # 命令行入口

saves/
├── save1/
│   ├── save.json              # 游戏存档
│   ├── world_event.txt        # 世界事件历史
│   ├── story_log.txt          # 完整故事文本
│   ├── summary_log.txt        # 世界摘要记录
│   └── nodes_log.txt          # 节点大纲记录
└── save2/
    └── ...

settings.json                  # 用户设置（API配置等）
```

## AI 模块

### 1. NarrativeEngine（叙事引擎）

**职责**：生成故事内容

- 接收玩家行动和世界摘要
- 生成连贯的故事文本
- 返回 JSON 格式的状态变化
- 支持时间跳过指令
- 默认温度：0.8（较有创意）

### 2. NodeParser（节点解析器）

**职责**：将大纲解析为事件节点

- 接收自然语言的世界大纲
- 解析为结构化的节点列表
- 每个节点包含名称、触发时间、描述
- 默认温度：0.3（较严谨）

### 3. EventRecorder（事件记录器）

**职责**：精简记录关键事件

- 从故事文本提取 1-3 个关键事件
- 每个事件一句话描述
- 追加保存到 world_event.txt
- 默认温度：0.1（较严谨）

### 4. WorldOutlineGenerator（世界大纲生成器）

**职责**：生成世界大纲

- 根据用户输入或随机生成完整世界设定
- 包含世界观、主角、目标、事件节点
- 支持流式输出
- 默认温度：0.9（较有创意）

### 5. ContinueOutline（故事续写）

**职责**：续写故事大纲

- 基于已完成的事件节点生成新情节
- 保持故事连贯性
- 默认温度：0.9（较有创意）

## 数据流

```
玩家行动
    │
    ▼
获取世界摘要（含所有历史事件）
    │
    ▼
叙事 AI 生成故事
    │
    ├─────▶ 保存到 story_log.txt
    │
    ├─────▶ 保存 JSON 到 state_log.json
    │
    ▼
事件记录 AI 精简事件
    │
    └─────▶ 追加到 world_event.txt
    │
    ▼
更新状态、推进时间
```

## 设置界面

通过 GUI 的设置界面可以配置：

### API 配置
- API Key
- API URL
- 模型名称

### AI 参数配置
每个 AI 模块都可以单独配置：
- **温度 (Temperature)**：控制输出的随机性
- **最大 Token 数**：控制输出长度
- **系统提示词**：自定义 AI 行为

## 自定义提示词

所有 AI 提示词在 `prompt.py` 中可修改：

- `NARRATIVE_PROMPT_TEMPLATE` - 叙事提示词
- `NODE_PARSER_PROMPT_TEMPLATE` - 节点解析提示词
- `EVENT_RECORDER_PROMPT_TEMPLATE` - 事件记录提示词
- `WORLD_OUTLINE_PROMPT_TEMPLATE` - 世界大纲生成提示词
- `CONTINUE_OUTLINE_PROMPT_TEMPLATE` - 故事续写提示词

## 配置参数

在 `config.py` 中可调整：

```python
MAX_HISTORY_ENTRIES = 10      # 历史记录最大条数
SUMMARY_MAX_HISTORY = 5       # 摘要显示历史条数
```

## 存档编辑器

可以在 GUI 中直接编辑存档文件：
- **save.json**：完整的存档数据（JSON格式）
- **world_event.txt**：世界事件记录

## 打包为 EXE

使用 PyInstaller 打包：

```bash
pip install pyinstaller
pyinstaller -F -m story_generator.gui -n story_generator
```

打包后，存档和设置将保存在 EXE 文件所在目录。

## 依赖

- Python 3.10+
- requests
- customtkinter
- python-dotenv（可选）

## 常见问题

### Q: 生成失败怎么办？
A: 检查 API Key 是否正确，网络是否稳定。可以尝试降低温度参数。

### Q: 如何获得更好的故事质量？
A: 
1. 使用更强大的模型（如 DeepSeek-V3）
2. 调高故事生成的温度参数（0.8-1.0）
3. 提供详细的世界大纲

### Q: 存档在哪里？
A: 存档保存在程序目录的 `saves` 文件夹中。

### Q: 支持哪些语言？
A: 界面为中文，故事生成支持中英文，取决于使用的模型。

## 许可

MIT License

---

版本: 0.3.0
