# AgentScope 示例 Agent

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/agentscope-ai/agentscope-samples/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://www.python.org/)
[![Docs](https://img.shields.io/badge/docs-AgentScope-blue)](https://doc.agentscope.io/)
[![Runtime Docs](https://img.shields.io/badge/docs-AgentScope%20Runtime-red)](https://runtime.agentscope.io/)
[![Last Commit](https://img.shields.io/github/last-commit/agentscope-ai/agentscope-samples)](https://github.com/agentscope-ai/agentscope-samples)

[[README]](README.md)

欢迎来到 **AgentScope 示例 Agent** 仓库！🎯
该仓库提供**可直接使用的 Python 示例 Agent**，它们构建于以下项目之上：

- [AgentScope](https://github.com/agentscope-ai/agentscope)
- [AgentScope Runtime](https://github.com/agentscope-ai/agentscope-runtime)

这些示例涵盖了广泛的使用场景 —— 从轻量级命令行 Agent，到同时具备前端和后端的**可部署全栈应用**。

---

## 📖 关于 AgentScope & AgentScope Runtime

### **AgentScope**

AgentScope 是一个多 Agent 框架，旨在以**简单高效**的方式构建**基于 LLM 的 Agent 应用**。它提供了用于定义 Agent、集成工具、管理对话以及编排多 Agent 工作流的抽象能力。

### **AgentScope Runtime**

AgentScope Runtime 是一个**全面的运行时框架**，主要解决部署和运行 Agent 的两个关键问题：

1. **高效的 Agent 部署** —— 支持跨环境的可扩展部署和管理。
2. **沙盒化工具执行** —— 安全、隔离地运行工具和外部操作。

它包括**Agent 部署**以及**安全的沙盒化工具执行**能力，可搭配 **AgentScope** 或其他 Agent 框架使用。

---

## ✨ 快速开始

- 所有示例均基于 **Python**。
- 示例按功能使用场景组织。
- 有些示例仅使用 **AgentScope**（纯 Python Agent）。
- 有些示例同时使用 **AgentScope 和 AgentScope Runtime** 来实现**带前端+后端的可部署全栈应用**。
- 全栈运行时版本的文件夹名称以：
  **`_fullstack_runtime`** 结尾

> 📌 **运行示例之前**，请查看对应的 `README.md` 获取安装与运行说明。

### 安装依赖

- [AgentScope 文档](https://doc.agentscope.io/)
- [AgentScope Runtime 文档](https://runtime.agentscope.io/)

---

## 🌳 仓库结构

```bash
├── browser_use/
│   ├── agent_browser/                      # 纯 Python 浏览器 Agent
│   └── browser_use_fullstack_runtime/      # 全栈运行时版本（前端+后端）
│
├── deep_research/
│   ├── agent_deep_research/                # 纯 Python 多 Agent 研究流程
│   └── qwen_langgraph_search_fullstack_runtime/    # 全栈运行时研究应用
│
├── games/
│   └── game_werewolves/                    # 角色扮演推理游戏
│
├── conversational_agents/
│   ├── chatbot/                            # 聊天机器人应用
│   ├── chatbot_fullstack_runtime/          # 带界面的运行时聊天机器人
│   ├── multiagent_conversation/            # 多 Agent 对话场景
│   └── multiagent_debate/                  # Agent 辩论场景
│
├── evaluation/
│   └── ace_bench/                          # 基准测试与评估工具
│
├── functionality/
│   ├── long_term_memory_mem0/              # 长期记忆集成
│   ├── mcp/                                # Memory/Context 协议演示
│   ├── plan/                               # ReAct Agent 任务计划
│   ├── rag/                                # AgentScope 中的 RAG
│   ├── session_with_sqlite/                # 基于 SQLite 的持久对话
│   ├── stream_printing_messages/           # 信息流式输出与打印
│   ├── structured_output/                  # 结构化输出解析与验证
│   ├── multiagent_concurrent/              # 多 Agent 并发任务执行
│   └── meta_planner_agent/                  # 带工具编排的计划 Agent
│
└── README.md
```

---

## 📌 示例列表

| 分类                    | 示例文件夹                                           | 使用 AgentScope | 使用 AgentScope Runtime | 描述 |
| ----------------------- |-----------------------------------------------------| --------------- | ----------------------- |------|
| **浏览器相关**          | browser_use/agent_browser                           | ✅               | ❌                       | 基于 AgentScope 的命令行浏览器自动化 |
|                         | browser_use/browser_use_fullstack_runtime           | ✅               | ✅                       | 带 UI 和沙盒环境的全栈浏览器自动化 |
| **深度研究**            | deep_research/agent_deep_research                   | ✅               | ❌                       | 多 Agent 研究流程 |
|                         | deep_research/qwen_langgraph_search_fullstack_runtime | ❌               | ✅                       | 全栈运行时深度研究应用 |
| **游戏**                | games/game_werewolves                               | ✅               | ❌                       | 多 Agent 角色扮演推理游戏 |
| **对话应用**            | conversational_agents/chatbot_fullstack_runtime     | ✅               | ✅                       | 带前端/后端的聊天机器人 |
|                         | conversational_agents/chatbot                       | ✅               | ❌                       | 聊天机器人 |
|                         | conversational_agents/multiagent_conversation       | ✅               | ❌                       | 多 Agent 对话场景 |
|                         | conversational_agents/multiagent_debate             | ✅               | ❌                       | Agent 辩论 |
| **评估**                | evaluation/ace_bench                                | ✅               | ❌                       | ACE Bench 基准测试 |
| **功能演示**            | functionality/long_term_memory_mem0                 | ✅               | ❌                       | 长期记忆（mem0 支持） |
|                         | functionality/mcp                                   | ✅               | ❌                       | Memory/Context 协议 Demo |
|                         | functionality/session_with_sqlite                   | ✅               | ❌                       | 基于 SQLite 的持久上下文 |
|                         | functionality/structured_output                     | ✅               | ❌                       | 结构化数据提取与验证 |
|                         | functionality/multiagent_concurrent                 | ✅               | ❌                       | 多 Agent 并发任务执行 |
|                         | functionality/meta_planner_agent                    | ✅               | ❌                       | 带工具编排的计划 Agent |
|                         | functionality/plan                                  | ✅               | ❌                       | 使用 ReAct Agent 规划任务 |
|                         | functionality/rag                                   | ✅               | ❌                       | 检索增强生成 (RAG) 集成 |
|                         | functionality/stream_printing_messages              | ✅               | ❌                       | 实时信息流输出与打印 |

---

## ℹ️ 获取帮助

如果你：

- 需要安装帮助  
- 遇到问题  
- 想了解某个示例的工作方式  

请：

1. 阅读该示例的 `README.md`
2. 提交 [GitHub Issue](https://github.com/agentscope-ai/agentscope-samples/issues)
3. 加入社区讨论：

| [Discord](https://discord.gg/eYMpfnkG8h) | 钉钉 |
|------------------------------------------|------|
| <img src="https://gw.alicdn.com/imgextra/i1/O1CN01hhD1mu1Dd3BWVUvxN_!!6000000000238-2-tps-400-400.png" width="100" height="100"> | <img src="https://img.alicdn.com/imgextra/i1/O1CN01LxzZha1thpIN2cc2E_!!6000000005934-2-tps-497-477.png" width="100" height="100"> |

---

## 🤝 参与贡献

欢迎提交：

- Bug 报告  
- 新功能请求  
- 文档改进  
- 代码贡献  

详情见 [Contributing](https://github.com/agentscope-ai/agentscope-samples/blob/main/CONTRIBUTING_zh.md) 文档。

---

## 📄 许可证

本项目基于 **Apache 2.0 License** 授权，详见 [LICENSE](https://github.com/agentscope-ai/agentscope-samples/blob/main/LICENSE) 文件。

---

## 🔗 相关资源

- [AgentScope 文档](https://doc.agentscope.io/)
- [AgentScope Runtime 文档](https://runtime.agentscope.io/)
- [AgentScope GitHub 仓库](https://github.com/agentscope-ai/agentscope)
- [AgentScope Runtime GitHub 仓库](https://github.com/agentscope-ai/agentscope-runtime)
