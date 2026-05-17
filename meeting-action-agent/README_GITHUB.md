# MeetingMind · 会议智能助手

MeetingMind 是一个基于 Streamlit 的会议到执行助手，帮助你把会议纪要快速转化为结构化任务、个人待办和可协作的工作流。

## 核心功能

- 会议纪要分析：提取任务、负责人、截止日期、优先级
- 工作模式：按任务上下文和 AI 对话协作
- 多模型配置：可切换 DeepSeek、Gemini 或自定义模型
- Skill 模板：写作、代码审查、邮件、会议总结等
- Agent 模式：可连接本机 OpenClaw 执行自动化任务

## 运行环境

- Python 3.9+
- macOS / Linux / Windows
- Streamlit
- 可选：OpenClaw（仅 Agent 模式需要）

## 安装

```bash
git clone <your-repo-url>
cd meeting-action-agent
pip install -r requirements.txt
```

## 启动

```bash
streamlit run demo_ui.py
```

然后访问 Streamlit 提示的本地地址。

## 部署到 Streamlit Community Cloud

1. 将仓库推送到 GitHub（应用目录为 `meeting-action-agent/`）。
2. 打开 [share.streamlit.io](https://share.streamlit.io) → **New app**。
3. **Main file path** 填写：`meeting-action-agent/demo_ui.py`（若仓库根目录就是 `meeting-action-agent`，则填 `demo_ui.py`）。
4. **App settings → Secrets**，粘贴 `.streamlit/secrets.toml.example` 中的内容并填入真实 API Key：

```toml
OPENAI_API_KEY = "sk-..."
OPENAI_BASE_URL = "https://api.deepseek.com"
OPENAI_MODEL = "deepseek-chat"
```

5. 点击 **Deploy**。云端可正常使用会议分析与问答；使用 Agent 模式或浏览器搜索时，会提示在本地部署后使用。

| 文件 | 作用 |
|------|------|
| `requirements.txt` | Python 依赖 |
| `.streamlit/config.toml` | 关闭首次邮箱提示、关闭使用统计 |
| `.streamlit/secrets.toml.example` | Secrets 模板 |
| `.python-version` | 推荐 Python 3.11 |
| `cloud_config.py` | 云端 / 本地模式检测 |

## 配置模型

在应用右侧/侧边栏中可以直接配置：

- API Key
- Base URL
- Model ID

如果你想使用环境变量，也可以自行设置：

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.deepseek.com"
export OPENAI_MODEL="deepseek-chat"
```

## 使用说明

### 1. 总结会议

1. 打开首页
2. 进入「总结会议」
3. 粘贴会议纪要或上传文本
4. 生成结构化任务与待办

### 2. 开始工作

1. 打开首页
2. 进入「开始工作」
3. 上传任务清单 JSON
4. 选择任务开始对话

### 3. Agent 模式

Agent 模式依赖本机安装的 OpenClaw。

推荐方式是：

- 用户在自己的电脑上运行本项目
- 用户在自己的电脑上运行 OpenClaw Gateway
- 页面中配置 Agent 名称、手机号或 Session ID

这样最安全，也最适合当前演示版。

## 给 GitHub 发布时建议补充的内容

- `requirements.txt`
- `.env.example`
- 项目截图
- 示例输入文件
- 常见问题 FAQ
- OpenClaw 本地运行说明

## 推荐仓库结构

```text
meeting-action-agent/
├── demo_ui.py
├── pages/
│   ├── 1_会议分析.py
│   └── 2_工作模式.py
├── backend/
├── data/
├── utils.py
├── requirements.txt
└── README.md
```

## 说明

这个项目当前更适合「本地可运行演示版」。如果未来要做成公开在线服务，建议把 Agent 功能拆成独立的本地连接器，而不是让云端网页直接控制用户电脑。
