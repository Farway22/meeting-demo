# MeetingMind · 会议智能助手

> 将会议纪要转化为结构化行动计划，通过 AI 协助和自动化 Agent 提升团队执行效率

## 🎯 核心价值

MeetingMind 解决的是**会议到执行**的信息断层问题：

- **会议信息碎片化** → 自动提取结构化任务
- **任务分配不清** → 按人生成个性化待办清单
- **执行缺乏协助** → AI 实时问答、建议、协作
- **自动化程度低** → OpenClaw Agent 在电脑上自主执行
- **进度难追踪** → 实时标记完成、可视化进度

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    MeetingMind 三层架构                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  📋 会议分析页                                               │
│  ├─ 输入：会议记录 + 参与者（文本/文件上传）                 │
│  ├─ 处理：LLM 管道提取任务、优先级、依赖关系                 │
│  └─ 输出：执行计划 + 个人待办清单（JSON/Markdown）          │
│                                                              │
│  💼 工作模式页 · 问答模式                                    │
│  ├─ 左侧：任务列表 + 完成追踪 + 模型配置                     │
│  ├─ 右侧：AI 问答助手 + 浏览器搜索                           │
│  └─ 功能：Skill 模板、消息历史、任务上下文注入               │
│                                                              │
│  🤖 工作模式页 · Agent 模式                                  │
│  ├─ 连接：OpenClaw Gateway（本地 Agent 平台）               │
│  ├─ 执行：自动化任务（网页操作、文档生成、邮件等）          │
│  └─ 反馈：实时显示 Agent 执行结果                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 环境要求
- Python 3.9+
- macOS / Linux / Windows
- OpenClaw（可选，仅 Agent 模式需要）

### 安装依赖

```bash
cd meeting_demo/meeting-action-agent
pip install -r requirements.txt
```

### 启动应用

```bash
# 设置 API Key（可选，使用默认 DeepSeek）
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.deepseek.com"
export OPENAI_MODEL="deepseek-chat"

# 启动 Streamlit
python3 -m streamlit run demo_ui.py --server.port 8503
```

访问 **http://localhost:8503**

---

## 📖 功能详解

### 1️⃣ 会议分析页 (`pages/1_会议分析.py`)

#### 输入方式
- **📁 上传文件**：支持 `.txt` / `.md` 格式
  - 会议内容文件：自动读取并填入
  - 参与者文件：每行格式 `姓名/角色`
- **✏️ 手动输入**：直接粘贴文本

#### 处理流程
```
会议记录 + 参与者
    ↓
LLM 分析管道（DeepSeek/Gemini）
    ↓
提取：
  • 执行计划（主流程 + 并行任务）
  • 任务详情（优先级、阻塞关系、截止日期）
  • 个人待办（按人员分配）
    ↓
结构化输出
```

#### 输出内容

**执行计划视图**
- 主流程步骤数
- 并行任务数
- 关键阻塞项
- 涉及人员数

**任务详情标签**
- 任务名称、优先级、截止日期
- 负责人、依赖关系
- 是否为阻塞项

**个人待办标签**
- 按人员分组
- 支持 JSON / Markdown 下载
- 可直接导入工作模式

#### 特性
- ✅ 分析完成后输入区自动折叠
- ✅ 状态持久化（返回页面结果不丢失）
- ✅ 加载示例数据快速体验
- ✅ 支持重新分析（修改输入后重新运行）

---

### 2️⃣ 工作模式页 · 问答模式 (`pages/2_工作模式.py`)

#### 左侧侧栏

**用户 & 模型**
```
👤 用户选择
   ├─ 当前用户名
   └─ 待办数量统计

🤖 模型选择
   ├─ 文职/DeepSeek
   ├─ 通用/Gemini
   └─ 支持添加自定义模型
```

**任务列表**
```
📋 MY TASKS (完成数/总数)
├─ [▶ 开始] [✅ 完成] 前端接入支付页面 (HIGH, 周三)
├─ [✓ 进行中] [↩ 撤销] 与产品对接 (MED, 周四)
└─ ...
```

**设置面板**
```
⚙ 设置
├─ Skill 模板（写作、代码审查、邮件等）
├─ 模型配置（API Key、Base URL、Model ID）
├─ 上传/清除任务清单
└─ 返回首页
```

#### 右侧聊天区

**任务上下文卡片**
```
┌─ [HIGH] task_001 ─────────────────────┐
│ 前端接入支付页面                       │
│ 截止：周三 · 等待后端接口完成         │
└───────────────────────────────────────┘
```

**消息流**
- 用户消息：右对齐，深色背景
- 助手消息：左对齐，浅色背景
- 支持 Markdown 格式（代码块、列表、链接等）
- 动画过渡（fadeUp 效果）

**输入区**
- 底部固定输入框（`st.chat_input` 原生）
- 占位符：`"针对此任务提问或请求协助..."`
- 🌐 浏览器搜索按钮（有消息时显示）

#### 工作流

```
1. 选择任务
   ↓
2. 查看任务上下文
   ↓
3. 提问 / 请求协助
   ↓
4. AI 回复（支持 Markdown）
   ↓
5. 标记完成 ✅
   ├─ 任务变灰色删除线
   ├─ 进度计数更新
   └─ 自动退出对话
```

#### 特性
- ✅ 任务完成后可撤销（↩ 撤销）
- ✅ 消息历史保留（切换任务时清空）
- ✅ 任务上下文自动注入 LLM 提示词
- ✅ 支持多模型切换
- ✅ Skill 模板快速切换工作角色

---

### 3️⃣ 工作模式页 · Agent 模式（核心创新）

#### 什么是 Agent 模式？

Agent 模式连接 **OpenClaw**（本地 AI Agent 平台），让 AI 在你的电脑上**自主执行任务**：

- 🌐 打开网页、填表、搜索信息
- 📧 撰写并发送邮件
- 📊 生成报告、数据分析
- 💻 代码审查、文档编写
- 🔄 重复性工作自动化

#### 前置条件

1. **安装 OpenClaw**
   ```bash
   # macOS
   brew install openclaw
   
   # 或从源码安装
   npm install -g openclaw
   ```

2. **查看本机 Agent**
   ```bash
   openclaw agents list
   ```
   输出示例：
   ```
   Agents:
   - main (default)
     Workspace: ~/.openclaw/workspace
     Model: moonshot/kimi-k2.5
   ```

#### 使用流程

**第一步：配置 Agent 目标**

在 Agent 模式页面，展开「⚙ Agent 目标配置」，选择一种方式：

| 方式 | 填写内容 | 示例 |
|------|---------|------|
| `--to 手机号` | E.164 格式 | `+8613800138000` |
| `--agent 名称` | Agent 名称 | `main` |
| `--session-id` | 会话 ID | 从 `openclaw sessions` 获取 |

**第二步：检查 Gateway**

页面自动检测 OpenClaw Gateway 状态：
- 🟢 **运行中** → 直接可用
- 🟡 **未运行** → 点击「▶ 启动 Gateway」（后台启动）

**第三步：发送指令**

在聊天框输入指令，系统自动拼入任务上下文：

```
用户输入：帮我整理本周的工作成果

→ 完整指令：
当前任务：完成周报。截止：周五。
用户指令：帮我整理本周的工作成果

→ 执行：
openclaw agent --agent main --message "当前任务：完成周报。截止：周五。用户指令：帮我整理本周的工作成果"
```

**第四步：查看结果**

Agent 执行结果实时显示在聊天区：
- ✅ 成功：显示执行结果
- ⏱ 超时：60s 无响应，提示任务可能在后台运行
- ❌ 失败：显示错误信息

#### 实际应用场景

**场景 1：周报生成**
```
任务：完成周报
指令：帮我整理本周的工作成果，包括完成的功能、遇到的问题、下周计划

Agent 自动：
1. 打开任务管理系统
2. 提取本周完成的任务
3. 查看 Slack/邮件 中的问题记录
4. 生成周报文档
5. 发送给主管
```

**场景 2：数据收集**
```
任务：收集竞品信息
指令：访问 3 个竞品网站，收集他们的定价、功能、用户评价

Agent 自动：
1. 打开浏览器
2. 逐个访问竞品网站
3. 提取关键信息
4. 生成对比表格
5. 保存到本地
```

**场景 3：邮件处理**
```
任务：发送项目进度邮件
指令：根据本周的任务完成情况，给团队发送进度邮件

Agent 自动：
1. 查询任务完成数据
2. 撰写邮件内容
3. 添加附件（报告、截图等）
4. 发送给指定收件人
```

#### 特性
- ✅ Gateway 自动检测 + 一键启动
- ✅ 灵活的目标配置（手机号 / Agent 名称 / Session ID）
- ✅ 任务上下文自动注入
- ✅ 实时执行反馈
- ✅ 60s 超时保护

---

## 🎨 UI/UX 设计

### 设计理念
- **简洁高效**：最少化操作步骤
- **视觉反馈**：动画、颜色、进度指示
- **深色侧栏**：ChatGPT 风格，专业感
- **响应式布局**：适配不同屏幕

### 色彩系统
- **主色**：#DC2626（红色，品牌色）
- **文本**：#1A1917（深灰）
- **辅助**：#78716C（浅灰）
- **成功**：#16A34A（绿色）
- **警告**：#D97706（橙色）

### 动画效果
- **fadeIn**：页面加载时淡入
- **fadeUp**：消息出现时向上淡入
- **transition**：按钮、卡片悬停效果

---

## 🔧 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端** | Streamlit 1.28+ | 快速 Web UI，无需前端代码 |
| **LLM** | DeepSeek / Gemini | 会议分析 + 问答协助 |
| **Agent** | OpenClaw | 本地自动化执行 |
| **存储** | Session State | 会话级缓存（内存） |
| **浏览器** | Selenium + WebDriver Manager | 浏览器自动化演示 |

### 依赖包
```
streamlit>=1.28.0
openai>=1.0.0
webdriver-manager>=4.0.0
selenium>=4.0.0
python-docx>=0.8.11  # 可选，用于 .docx 支持
pdfplumber>=0.10.0   # 可选，用于 .pdf 支持
```

---

## 📁 项目结构

```
meeting_demo/
├── meeting-action-agent/
│   ├── demo_ui.py                    # 首页（模式选择）
│   ├── pages/
│   │   ├── 1_会议分析.py             # 会议分析页
│   │   └── 2_工作模式.py             # 工作模式页
│   ├── utils.py                      # 工具函数（渲染、解析、导出）
│   ├── backend/
│   │   └── app/prototype/
│   │       ├── meeting_pipeline.py   # LLM 分析管道
│   │       └── llm.py                # LLM 调用封装
│   └── requirements.txt
└── README.md
```

---

## 🔐 配置管理

### 环境变量

```bash
# LLM 配置
export OPENAI_API_KEY="sk-xxx"
export OPENAI_BASE_URL="https://api.deepseek.com"
export OPENAI_MODEL="deepseek-chat"

# 可选：使用 Gemini
export OPENAI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
export OPENAI_MODEL="gemini-2.0-flash"
```

### 在应用内配置

所有配置也可在 UI 侧栏动态设置，无需重启应用。

---

## 💡 高级用法

### 自定义 Skill 模板

在 `pages/2_工作模式.py` 中修改 `SKILL_TEMPLATES`：

```python
SKILL_TEMPLATES = {
    "你的角色": "你的系统提示词...",
    "写作助手": "你擅长中文写作，帮助用户撰写、润色各类文档...",
    # 添加更多
}
```

### 扩展 LLM 模型

在侧栏「⚙ 设置」→「模型配置」中添加新模型：
- 显示名称：自定义
- API Key：模型提供商的密钥
- Base URL：API 端点
- Model ID：模型标识符

### 导出任务清单

支持两种格式：
- **JSON**：结构化数据，便于程序处理
- **Markdown**：可读性强，便于分享

---

## 🚧 已知限制

1. **会话级存储**：刷新页面后数据丢失（可扩展为数据库）
2. **单用户**：暂不支持多用户协作（可添加用户认证）
3. **Agent 执行**：需要本地 OpenClaw 环境
4. **LLM 成本**：每次分析都调用 API（可添加缓存）

---

## 🔮 未来规划

### 短期（1-2 周）
- [ ] 数据库持久化（替代 Session State）
- [ ] 会议历史库 + 搜索
- [ ] 任务评论讨论功能
- [ ] 截止日期预警提醒

### 中期（1-2 月）
- [ ] 团队协作（权限管理、实时共享）
- [ ] 智能重排（基于优先级和依赖关系）
- [ ] Agent 工作流（复杂多步骤自动化）
- [ ] 数据看板（工作量分析、完成率统计）

### 长期（3-6 月）
- [ ] Skill 市场（用户自定义 Skill、分享）
- [ ] 与 OpenClaw 深度集成（自定义 Agent 行为）
- [ ] 本地知识库（RAG 增强）
- [ ] 移动端支持

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发流程
1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/xxx`)
3. 提交更改 (`git commit -m "Add xxx"`)
4. 推送到分支 (`git push origin feature/xxx`)
5. 创建 Pull Request

---

## 📄 许可证

MIT License

---

## 📞 联系方式

- 📧 Email: [your-email]
- 💬 Issues: [GitHub Issues]
- 🐦 Twitter: [@your-handle]

---

## 🙏 致谢

感谢以下开源项目的支持：
- [Streamlit](https://streamlit.io/)
- [OpenAI Python SDK](https://github.com/openai/openai-python)
- [OpenClaw](https://openclaw.ai/)
- [Selenium](https://www.selenium.dev/)

---

**MeetingMind** · 让会议更高效，让执行更自动化。
