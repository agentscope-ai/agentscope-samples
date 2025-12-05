# AgentScope 示例 Agent

<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-14-orange.svg?style=flat-square)](#contributors-)
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
├── data_juicer_agent/                      # 数据处理多智能体系统
├── sample_template/                        # 新样例贡献模板
└── README.md
```

---

## 📌 示例列表

| 分类        | 示例文件夹                                                 | 使用 AgentScope | 使用 AgentScope Runtime | 描述                      |
|-----------|-------------------------------------------------------|---------------|-----------------------|-------------------------|
| **数据处理**            | data_juicer_agent/                                 | ✅               | ❌                       | 基于 Data-Juicer 的多智能体数据处理 |
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
| **通用智能体** | alias/                                                | ✅             | ✅                     | 在沙盒中运行的可以解决真实问题的智能体程序   |

---

## 🌟 特色示例

### DataJuicer 智能体

一个强大的数据处理多智能体系统，利用 Data-Juicer 的 200+ 算子进行智能数据处理：

- **智能查询**：从 200+ 数据处理算子中找到合适的算子
- **自动化流程**：从自然语言描述生成 Data-Juicer YAML 配置
- **自定义开发**：通过 AI 辅助创建领域特定的算子
- **多种检索模式**：基于 LLM 和向量的算子匹配
- **MCP 集成**：原生模型上下文协议支持

📖 **文档**：[English](data_juicer_agent/README.md) | [中文](data_juicer_agent/README_ZH.md)

### Alias 智能体

*Alias-Agent*（简称 *Alias*）旨在作为一个智能助手来处理多样且复杂的真实世界任务，提供三种操作模式以实现灵活的任务执行：
- **Simple React**：采用经典的推理-行动循环来迭代解决问题并执行工具调用。
- **Planner-Worker**：使用智能规划将复杂任务分解为可管理的子任务，并由专门的执行智能体独立处理每个子任务。
- **Built-in Agents**：利用针对特定领域定制的专用智能体，包括用于全面分析的Deep Research Agent和用于基于 Web 交互的Browser-use Agent。

除了作为一个即用型智能体，我们也希望 Alias 能够成为一个基础模板，可以迁移到不同的场景。

📖 **文档**：[English](alias/README.md) | [中文](alias/README_ZH.md)

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
      <td align="center" valign="top" width="14.28%"><a href="https://yxdyc.github.io/"><img src="https://avatars.githubusercontent.com/u/67475544?v=4?s=100" width="100px;" alt="Daoyuan Chen"/><br /><sub><b>Daoyuan Chen</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=yxdyc" title="Code">💻</a> <a href="#example-yxdyc" title="Examples">💡</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/cmgzn"><img src="https://avatars.githubusercontent.com/u/85746275?v=4?s=100" width="100px;" alt="MeiXin Chen"/><br /><sub><b>MeiXin Chen</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=cmgzn" title="Code">💻</a> <a href="#example-cmgzn" title="Examples">💡</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://hylcool.github.io/"><img src="https://avatars.githubusercontent.com/u/12782861?v=4?s=100" width="100px;" alt="Yilun Huang"/><br /><sub><b>Yilun Huang</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=HYLcool" title="Code">💻</a> <a href="#example-HYLcool" title="Examples">💡</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://shenqianli.github.io/"><img src="https://avatars.githubusercontent.com/u/28307002?v=4?s=100" width="100px;" alt="ShenQianli"/><br /><sub><b>ShenQianli</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=ShenQianLi" title="Code">💻</a> <a href="#example-ShenQianLi" title="Examples">💡</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ZiTao-Li"><img src="https://avatars.githubusercontent.com/u/135263265?v=4?s=100" width="100px;" alt="ZiTao-Li"/><br /><sub><b>ZiTao-Li</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=ZiTao-Li" title="Code">💻</a> <a href="#example-ZiTao-Li" title="Examples">💡</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://xieyxclack.github.io/"><img src="https://avatars.githubusercontent.com/u/31954383?v=4?s=100" width="100px;" alt="Yuexiang XIE"/><br /><sub><b>Yuexiang XIE</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=xieyxclack" title="Code">💻</a> <a href="#example-xieyxclack" title="Examples">💡</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/cuiyuebing"><img src="https://avatars.githubusercontent.com/u/39703217?v=4?s=100" width="100px;" alt="Yue Cui"/><br /><sub><b>Yue Cui</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=cuiyuebing" title="Code">💻</a> <a href="#example-cuiyuebing" title="Examples">💡</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ZexiLee"><img src="https://avatars.githubusercontent.com/u/49397774?v=4?s=100" width="100px;" alt="Zexi Li"/><br /><sub><b>Zexi Li</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=ZexiLee" title="Code">💻</a> <a href="#example-ZexiLee" title="Examples">💡</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/SSSuperDan"><img src="https://avatars.githubusercontent.com/u/73866152?v=4?s=100" width="100px;" alt="Dandan Liu"/><br /><sub><b>Dandan Liu</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=SSSuperDan" title="Code">💻</a> <a href="#example-SSSuperDan" title="Examples">💡</a></td>
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