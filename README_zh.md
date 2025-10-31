# AgentScope 示例 Agent

<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-5-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->
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
├── alias/                                  # 解决现实问题的智能体程序
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
├── sample_template/                        # 新样例贡献模板
└── README.md
```

---

## 📌 示例列表

| 分类        | 示例文件夹                                                 | 使用 AgentScope | 使用 AgentScope Runtime | 描述                      |
|-----------|-------------------------------------------------------|---------------|-----------------------|-------------------------|
| **浏览器相关** | browser_use/agent_browser                             | ✅             | ❌                     | 基于 AgentScope 的命令行浏览器自动化 |
|           | browser_use/browser_use_fullstack_runtime             | ✅             | ✅                     | 带 UI 和沙盒环境的全栈浏览器自动化     |
| **深度研究**  | deep_research/agent_deep_research                     | ✅             | ❌                     | 多 Agent 研究流程            |
|           | deep_research/qwen_langgraph_search_fullstack_runtime | ❌             | ✅                     | 全栈运行时深度研究应用             |
| **游戏**    | games/game_werewolves                                 | ✅             | ❌                     | 多 Agent 角色扮演推理游戏        |
| **对话应用**  | conversational_agents/chatbot_fullstack_runtime       | ✅             | ✅                     | 带前端/后端的聊天机器人            |
|           | conversational_agents/chatbot                         | ✅             | ❌                     | 聊天机器人                   |
|           | conversational_agents/multiagent_conversation         | ✅             | ❌                     | 多 Agent 对话场景            |
|           | conversational_agents/multiagent_debate               | ✅             | ❌                     | Agent 辩论                |
| **评估**    | evaluation/ace_bench                                  | ✅             | ❌                     | ACE Bench 基准测试          |
| **Alias** | alias/                                                | ✅             | ✅                     | 在沙盒中运行的可以解决真实问题的智能体程序   |

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

## 贡献者 ✨

感谢这些优秀的贡献者们 ([表情符号说明](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="http://weiruikuang.com"><img src="https://avatars.githubusercontent.com/u/39145382?v=4?s=100" width="100px;" alt="Weirui Kuang"/><br /><sub><b>Weirui Kuang</b></sub></a><br /><a href="#maintenance-rayrayraykk" title="Maintenance">🚧</a> <a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=rayrayraykk" title="Code">💻</a> <a href="https://github.com/agentscope-ai/agentscope-samples/pulls?q=is%3Apr+reviewed-by%3Arayrayraykk" title="Reviewed Pull Requests">👀</a> <a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=rayrayraykk" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Osier-Yi"><img src="https://avatars.githubusercontent.com/u/8287381?v=4?s=100" width="100px;" alt="Osier-Yi"/><br /><sub><b>Osier-Yi</b></sub></a><br /><a href="#maintenance-Osier-Yi" title="Maintenance">🚧</a> <a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=Osier-Yi" title="Code">💻</a> <a href="https://github.com/agentscope-ai/agentscope-samples/pulls?q=is%3Apr+reviewed-by%3AOsier-Yi" title="Reviewed Pull Requests">👀</a> <a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=Osier-Yi" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://davdgao.github.io/"><img src="https://avatars.githubusercontent.com/u/102287034?v=4?s=100" width="100px;" alt="DavdGao"/><br /><sub><b>DavdGao</b></sub></a><br /><a href="#maintenance-DavdGao" title="Maintenance">🚧</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/qbc2016"><img src="https://avatars.githubusercontent.com/u/22984042?v=4?s=100" width="100px;" alt="qbc"/><br /><sub><b>qbc</b></sub></a><br /><a href="#maintenance-qbc2016" title="Maintenance">🚧</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/411380764"><img src="https://avatars.githubusercontent.com/u/61401544?v=4?s=100" width="100px;" alt="Lamont Huffman"/><br /><sub><b>Lamont Huffman</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=411380764" title="Code">💻</a> <a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=411380764" title="Tests">⚠️</a></td>
    </tr>
  </tbody>
  <tfoot>
    <tr>
      <td align="center" size="13px" colspan="7">
        <img src="https://raw.githubusercontent.com/all-contributors/all-contributors-cli/1b8533af435da9854653492b1327a23a4dbd0a10/assets/logo-small.svg">
          <a href="https://all-contributors.js.org/docs/en/bot/usage">Add your contributions</a>
        </img>
      </td>
    </tr>
  </tfoot>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

本项目遵循 [all-contributors](https://github.com/all-contributors/all-contributors) 规范。欢迎任何形式的贡献！