# AgentScope 示例

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/agentscope-ai/agentscope-samples/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://www.python.org/)
[![DeepWiki](https://img.shields.io/badge/DeepWiki-agentscope--samples-navy.svg?logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAyCAYAAAAnWDnqAAAAAXNSR0IArs4c6QAAA05JREFUaEPtmUtyEzEQhtWTQyQLHNak2AB7ZnyXZMEjXMGeK/AIi+QuHrMnbChYY7MIh8g01fJoopFb0uhhEqqcbWTp06/uv1saEDv4O3n3dV60RfP947Mm9/SQc0ICFQgzfc4CYZoTPAswgSJCCUJUnAAoRHOAUOcATwbmVLWdGoH//PB8mnKqScAhsD0kYP3j/Yt5LPQe2KvcXmGvRHcDnpxfL2zOYJ1mFwrryWTz0advv1Ut4CJgf5uhDuDj5eUcAUoahrdY/56ebRWeraTjMt/00Sh3UDtjgHtQNHwcRGOC98BJEAEymycmYcWwOprTgcB6VZ5JK5TAJ+fXGLBm3FDAmn6oPPjR4rKCAoJCal2eAiQp2x0vxTPB3ALO2CRkwmDy5WohzBDwSEFKRwPbknEggCPB/imwrycgxX2NzoMCHhPkDwqYMr9tRcP5qNrMZHkVnOjRMWwLCcr8ohBVb1OMjxLwGCvjTikrsBOiA6fNyCrm8V1rP93iVPpwaE+gO0SsWmPiXB+jikdf6SizrT5qKasx5j8ABbHpFTx+vFXp9EnYQmLx02h1QTTrl6eDqxLnGjporxl3NL3agEvXdT0WmEost648sQOYAeJS9Q7bfUVoMGnjo4AZdUMQku50McDcMWcBPvr0SzbTAFDfvJqwLzgxwATnCgnp4wDl6Aa+Ax283gghmj+vj7feE2KBBRMW3FzOpLOADl0Isb5587h/U4gGvkt5v60Z1VLG8BhYjbzRwyQZemwAd6cCR5/XFWLYZRIMpX39AR0tjaGGiGzLVyhse5C9RKC6ai42ppWPKiBagOvaYk8lO7DajerabOZP46Lby5wKjw1HCRx7p9sVMOWGzb/vA1hwiWc6jm3MvQDTogQkiqIhJV0nBQBTU+3okKCFDy9WwferkHjtxib7t3xIUQtHxnIwtx4mpg26/HfwVNVDb4oI9RHmx5WGelRVlrtiw43zboCLaxv46AZeB3IlTkwouebTr1y2NjSpHz68WNFjHvupy3q8TFn3Hos2IAk4Ju5dCo8B3wP7VPr/FGaKiG+T+v+TQqIrOqMTL1VdWV1DdmcbO8KXBz6esmYWYKPwDL5b5FA1a0hwapHiom0r/cKaoqr+27/XcrS5UwSMbQAAAABJRU5ErkJggg==)](https://deepwiki.com/agentscope-ai/agentscope-samples)
[![Docs](https://img.shields.io/badge/docs-AgentScope-blue)](https://doc.agentscope.io/)
[![Runtime Docs](https://img.shields.io/badge/docs-AgentScope%20Runtime-red)](https://runtime.agentscope.io/)
[![Last Commit](https://img.shields.io/github/last-commit/agentscope-ai/agentscope-samples)](https://github.com/agentscope-ai/agentscope-samples)

[[README]](README.md)

🎯 **快启动你的智能体之旅！**
这是一个集合了 **各种可直接运行的 Python 智能体示例** 的仓库，涵盖从命令行小工具到 **全栈可部署应用**。

## 🌟 什么是 AgentScope？

**[AgentScope](https://github.com/agentscope-ai/agentscope)** 是一个 **多智能体（Multi-Agent）框架**，让你能快速构建 **基于 LLM 的智能应用**：

> 详情请参考：[AgentScope 文档](https://doc.agentscope.io/)
- 🧠 定义智能体、集成工具
- 📡 管理上下文与对话
- 🤝 编排多个智能体协作完成任务



**[AgentScope-Runtime](https://github.com/agentscope-ai/agentscope-runtime)** 则是智能体运行时框架，让你能将智能体部署成API服务：

> 详情请参考：[AgentScope Runtime 文档](https://runtime.agentscope.io/)
1. 🔄 **多智能体的可伸缩部署管理**
2. 🛡️ **安全工具沙箱执行**

结合两者，你可以从原型 **一键走向生产部署**。

## ⚡ 快速开始

📌 **运行示例之前**，请查看对应的 `README.md` 获取安装与运行说明。

> - 所有示例均基于 **Python**
> - 示例按功能、使用场景组织
> - 有些示例仅使用 **AgentScope**
> - 有些示例同时使用 **AgentScope 和 AgentScope Runtime** 来实现**带前端+后端的可部署全栈应用**。
> - 全栈运行时版本的文件夹名称以：**`_fullstack_runtime`** 结尾

## 🌳 仓库结构

```bash
├── alias/                                  # 解决现实问题的智能体程序
├── browser_use/
│   ├── agent_browser/                      # 纯 Python 浏览器 Agent
│   ├── browser_use_agent_pro/              # 高级纯 Python 浏览器 Agent
│   └── browser_use_fullstack_runtime/      # 全栈运行时版本(前端+后端)
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
├── tuner/                                  # 用 AgentScope Tuner 调优 AgentScope 应用
│   ├── math_agent/                         # 快速入门调优示例
│   ├── frozen_lake/                        # 教一个智能体玩需要多步操作的游戏
│   ├── learn_to_ask/                       # 使用 LLM 作为评委辅助智能体训练
│   ├── email_search/                       # 提升智能体的工具使用能力
│   ├── werewolves/                         # 强化多智能体应用能力
│   └── data_augment/                       # 增强用于调优的数据
├── sample_template/                        # 新样例贡献模板
└── README.md
```

---

## 📌 示例列表

| 分类        | 示例文件夹                                                 | 使用 AgentScope | 使用 AgentScope Runtime | 描述                      |
|-----------|-------------------------------------------------------|---------------|-----------------------|-------------------------|
| **数据处理**            | data_juicer_agent/                                 | ✅               | ❌                       | 基于 Data-Juicer 的多智能体数据处理 |
| **浏览器相关** | browser_use/agent_browser                             | ✅             | ❌                     | 基于 AgentScope 的命令行浏览器自动化 |
|           | browser_use/browser_use_agent_pro                     | ✅             | ❌                     | 基于 AgentScope 的高级命令行浏览器智能体 |
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
| **金融交易**  | evotraders/                                           | ✅             | ❌                     | 自我进化的多智能体交易系统          |

---

## 🌈 特色示例

### 📊 DataJuicer 智能体

一个强大的数据处理多智能体系统，利用 Data-Juicer 的 200+ 算子进行智能数据处理：

- **智能查询**：从 200+ 数据处理算子中找到合适的算子
- **自动化流程**：从自然语言描述生成 Data-Juicer YAML 配置
- **自定义开发**：通过 AI 辅助创建领域特定的算子
- **多种检索模式**：基于 LLM 和向量的算子匹配
- **MCP 集成**：原生模型上下文协议支持

📖 **文档**：[English](data_juicer_agent/README.md) | [中文](data_juicer_agent/README_ZH.md)

### 🕵🏻 Alias 智能体

*Alias-Agent*（简称 *Alias*）旨在作为一个智能助手来处理多样且复杂的真实世界任务，提供三种操作模式以实现灵活的任务执行：
- **Simple React**：采用经典的推理-行动循环来迭代解决问题并执行工具调用。
- **Planner-Worker**：使用智能规划将复杂任务分解为可管理的子任务，并由专门的执行智能体独立处理每个子任务。
- **Built-in Agents**：利用针对特定领域定制的专用智能体，包括用于全面分析的Deep Research Agent和用于基于 Web 交互的Browser-use Agent。

除了作为一个即用型智能体，我们也希望 Alias 能够成为一个基础模板，可以迁移到不同的场景。

📖 **文档**：[English](alias/README.md) | [中文](alias/README_ZH.md)

### 📈 EvoTraders

*EvoTraders* 是一个开源的金融交易智能体框架，通过多智能体协作和记忆系统，构建能够在真实市场中持续学习与进化的交易系统。主要特性包括：

- **多智能体协作交易**：包含基本面、技术面、情绪、估值等专业分析师角色以及基金经理和风控专家的团队协作。
- **记忆增强与进化**：基于 ReMe 记忆框架，智能体在交易后反思总结，形成独特的投资方法论。
- **实盘与回测支持**：支持实时行情接入的实盘模式以及基于历史数据的回测模式。
- **可视化交易大厅**：提供可视化界面实时观察智能体的分析过程、沟通记录和决策演化。

📖 **文档**：[English](evotraders/README.md) | [中文](evotraders/README_zh.md)

---

## 🆘 获取帮助

如果你：

- 需要安装帮助
- 遇到问题
- 想了解某个示例的工作方式

请：

1. 阅读该示例的 `README.md`
2. 提交 [GitHub Issue](https://github.com/agentscope-ai/agentscope-samples/issues)
3. 加入社区讨论：

| [Discord](https://discord.gg/eYMpfnkG8h)                     | 钉钉                                                         |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| <img src="https://gw.alicdn.com/imgextra/i1/O1CN01hhD1mu1Dd3BWVUvxN_!!6000000000238-2-tps-400-400.png" width="100" height="100"> | <img src="https://img.alicdn.com/imgextra/i4/O1CN014mhqFq1ZlgNuYjxrz_!!6000000003235-2-tps-400-400.png" width="100" height="100"> |

---

## 🤝 参与贡献

欢迎提交：

- Bug 报告
- 新功能请求
- 文档改进
- 代码贡献

详情见 [CONTRIBUTING_zh.md](CONTRIBUTING_zh.md) 文档。

## 📄 许可证

本项目基于 **Apache 2.0 License** 授权，详见 [LICENSE](LICENSE) 文件。

## 贡献者 ✨

<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-27-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

感谢这些优秀的贡献者们 ([表情符号说明](https://allcontributors.org/emoji-key/)):

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
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/cuiyuebing"><img src="https://avatars.githubusercontent.com/u/39703217?v=4?s=100" width="100px;" alt="Yue Cui"/><br /><sub><b>Yue Cui</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=cuiyuebing" title="Code">💻</a> <a href="#example-cuiyuebing" title="Examples">💡</a> <a href="#maintenance-cuiyuebing" title="Maintenance">🚧</a> <a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=cuiyuebing" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ZexiLee"><img src="https://avatars.githubusercontent.com/u/49397774?v=4?s=100" width="100px;" alt="Zexi Li"/><br /><sub><b>Zexi Li</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=ZexiLee" title="Code">💻</a> <a href="#example-ZexiLee" title="Examples">💡</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/lalaliat"><img src="https://avatars.githubusercontent.com/u/78087788?v=4?s=100" width="100px;" alt="lalaliat"/><br /><sub><b>lalaliat</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=lalaliat" title="Code">💻</a> <a href="#example-lalaliat" title="Examples">💡</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/SSSuperDan"><img src="https://avatars.githubusercontent.com/u/73866152?v=4?s=100" width="100px;" alt="Dandan Liu"/><br /><sub><b>Dandan Liu</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=SSSuperDan" title="Code">💻</a> <a href="#example-SSSuperDan" title="Examples">💡</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/StCarmen"><img src="https://avatars.githubusercontent.com/u/39507457?v=4?s=100" width="100px;" alt="Tianjing Zeng"/><br /><sub><b>Tianjing Zeng</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=StCarmen" title="Code">💻</a> <a href="#example-StCarmen" title="Examples">💡</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/zhijianma"><img src="https://avatars.githubusercontent.com/u/30956532?v=4?s=100" width="100px;" alt="zhijianma"/><br /><sub><b>zhijianma</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=zhijianma" title="Code">💻</a> <a href="#example-zhijianma" title="Examples">💡</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Dengjiaji"><img src="https://avatars.githubusercontent.com/u/15075186?v=4?s=100" width="100px;" alt="Jiaji"/><br /><sub><b>Jiaji</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=Dengjiaji" title="Code">💻</a> <a href="#example-Dengjiaji" title="Examples">💡</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/duoyw"><img src="https://avatars.githubusercontent.com/u/31238100?v=4?s=100" width="100px;" alt="duoyw"/><br /><sub><b>duoyw</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=duoyw" title="Code">💻</a> <a href="#example-duoyw" title="Examples">💡</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/sleepy-bird-world"><img src="https://avatars.githubusercontent.com/u/166603159?v=4?s=100" width="100px;" alt="JustinDing"/><br /><sub><b>JustinDing</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=sleepy-bird-world" title="Code">💻</a> <a href="#example-sleepy-bird-world" title="Examples">💡</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/jinliyl"><img src="https://avatars.githubusercontent.com/u/6469360?v=4?s=100" width="100px;" alt="jinliyl"/><br /><sub><b>jinliyl</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=jinliyl" title="Code">💻</a> <a href="#example-jinliyl" title="Examples">💡</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/y1y5"><img src="https://avatars.githubusercontent.com/u/105190237?v=4?s=100" width="100px;" alt="y1y5"/><br /><sub><b>y1y5</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=y1y5" title="Code">💻</a> <a href="#example-y1y5" title="Examples">💡</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://luyi256.github.io"><img src="https://avatars.githubusercontent.com/u/50238286?v=4?s=100" width="100px;" alt="LuYi"/><br /><sub><b>LuYi</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=luyi256" title="Code">💻</a> <a href="#example-luyi256" title="Examples">💡</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/1mycell"><img src="https://avatars.githubusercontent.com/u/143110833?v=4?s=100" width="100px;" alt="Wu Yue"/><br /><sub><b>Wu Yue</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=1mycell" title="Code">💻</a> <a href="#example-1mycell" title="Examples">💡</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://www.bruceluo.net"><img src="https://avatars.githubusercontent.com/u/7297307?v=4?s=100" width="100px;" alt="Zhiling (Bruce) Luo"/><br /><sub><b>Zhiling (Bruce) Luo</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=zhilingluo" title="Code">💻</a> <a href="#example-zhilingluo" title="Examples">💡</a> <a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=zhilingluo" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/yuluo1007"><img src="https://avatars.githubusercontent.com/u/16065149?v=4?s=100" width="100px;" alt="sidiluo"/><br /><sub><b>sidiluo</b></sub></a><br /><a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=yuluo1007" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/AttanWu"><img src="https://avatars.githubusercontent.com/u/16112546?v=4?s=100" width="100px;" alt="Attan"/><br /><sub><b>Attan</b></sub></a><br /><a href="#example-AttanWu" title="Examples">💡</a> <a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=AttanWu" title="Code">💻</a> <a href="https://github.com/agentscope-ai/agentscope-samples/commits?author=AttanWu" title="Documentation">📖</a></td>
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