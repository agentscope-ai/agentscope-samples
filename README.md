# AgentScope Sample Agents

<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-20-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/agentscope-ai/agentscope-samples/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://www.python.org/)
[![Docs](https://img.shields.io/badge/docs-AgentScope-blue)](https://doc.agentscope.io/)
[![Runtime Docs](https://img.shields.io/badge/docs-AgentScope%20Runtime-red)](https://runtime.agentscope.io/)
[![Last Commit](https://img.shields.io/github/last-commit/agentscope-ai/agentscope-samples)](https://github.com/agentscope-ai/agentscope-samples)

[[中文README]](README_zh.md)

Welcome to the **AgentScope Sample Agents** repository! 🎯
This repository provides **ready-to-use Python sample agents** built on top of:

- [AgentScope](https://github.com/agentscope-ai/agentscope)
- [AgentScope Runtime](https://github.com/agentscope-ai/agentscope-runtime)

The examples cover a wide range of use cases — from lightweight command-line agents to **full-stack deployable applications** with both backend and frontend.

------

## 📖 About AgentScope & AgentScope Runtime

### **AgentScope**

AgentScope is a multi-agent framework designed to provide a **simple and efficient** way to build **LLM-powered agent applications**. It offers abstractions for defining agents, integrating tools, managing conversations, and orchestrating multi-agent workflows.

### **AgentScope Runtime**

AgentScope Runtime is a **comprehensive runtime framework** that addresses two key challenges in deploying and operating agents:

1. **Effective Agent Deployment** – Scalable deployment and management of agents across environments.
2. **Sandboxed Tool Execution** – Secure, isolated execution of tools and external actions.

It includes **agent deployment** and **secure sandboxed tool execution**, and can be used with **AgentScope** or other agent frameworks.

------

## ✨ Getting Started

- All samples are **Python-based**.
- Samples are organized **by functional use case**.
- Some samples use only **AgentScope** (pure Python agents).
- Others use **both AgentScope and AgentScope Runtime** to implement **full-stack deployable applications** with frontend + backend.
- Full-stack runtime versions have folder names ending with:
  **`_fullstack_runtime`**

> 📌 **Before running** any example, check its `README.md` for installation and execution instructions.

### Install Requirements

- [AgentScope Documentation](https://doc.agentscope.io/)
- [AgentScope Runtime Documentation](https://runtime.agentscope.io/)

------

## 🌳 Repository Structure

```bash
├── alias/                                  # Agent to solve real-world problems
├── browser_use/
│   ├── agent_browser/                      # Pure Python browser agent
│   └── browser_use_fullstack_runtime/      # Full-stack runtime version with frontend/backend
│
├── deep_research/
│   ├── agent_deep_research/                # Pure Python multi-agent research
│   └── qwen_langgraph_search_fullstack_runtime/    # Full-stack runtime-enabled research app
│
├── games/
│   └── game_werewolves/                    # Role-based social deduction game
│
├── conversational_agents/
│   ├── chatbot/                            # Chatbot application
│   ├── chatbot_fullstack_runtime/          # Runtime-powered chatbot with UI
│   ├── multiagent_conversation/            # Multi-agent dialogue scenario
│   └── multiagent_debate/                  # Agents engaging in debates
│
├── evaluation/
│   └── ace_bench/                          # Benchmarks and evaluation tools
│
├── data_juicer_agent/                      # Data processing multi-agent system
├── sample_template/                        # Template for new sample contributions
└── README.md
```

------

## 📌 Example List

| Category                | Example Folder                                        | Uses AgentScope | Use AgentScope Runtime | Description                                      |
| ----------------------- |-------------------------------------------------------| --------------- | ------------ |--------------------------------------------------|
| **Data Processing**     | data_juicer_agent/                                   | ✅               | ❌            | Multi-agent data processing with Data-Juicer     |
| **Browser Use**         | browser_use/agent_browser                             | ✅               | ❌            | Command-line browser automation using AgentScope |
|                         | browser_use/browser_use_fullstack_runtime             | ✅               | ✅            | Full-stack browser automation with UI & sandbox  |
| **Deep Research**       | deep_research/agent_deep_research                     | ✅               | ❌            | Multi-agent research pipeline                    |
|                         | deep_research/qwen_langgraph_search_fullstack_runtime | ❌               | ✅            | Full-stack deep research app                     |
| **Games**               | games/game_werewolves                                 | ✅               | ❌            | Multi-agent roleplay game                        |
| **Conversational Apps** | conversational_agents/chatbot_fullstack_runtime       | ✅               | ✅            | Chatbot application with frontend/backend        |
|                         | conversational_agents/chatbot                         | ✅               | ❌            |                                                  |
|                         | conversational_agents/multiagent_conversation         | ✅               | ❌            | Multi-agent dialogue scenario                    |
|                         | conversational_agents/multiagent_debate               | ✅               | ❌            | Agents engaging in debates                       |
| **Evaluation**          | evaluation/ace_bench                                  | ✅               | ❌            | Benchmarks with ACE Bench                        |
| **General AI Agent**               | alias/                                                | ✅               | ✅                      | Agent application running in sandbox to solve diverse real-world problems |

------

## 🌟 Featured Examples

### DataJuicer Agent

A powerful multi-agent data processing system that leverages Data-Juicer's 200+ operators for intelligent data processing:

- **Intelligent Query**: Find suitable operators from 200+ data processing operators
- **Automated Pipeline**: Generate Data-Juicer YAML configurations from natural language
- **Custom Development**: Create domain-specific operators with AI assistance
- **Multiple Retrieval Modes**: LLM-based and vector-based operator matching
- **MCP Integration**: Native Model Context Protocol support

📖 **Documentation**: [English](data_juicer_agent/README.md) | [中文](data_juicer_agent/README_ZH.md)


### Alias-Agent

*Alias-Agent* (short for *Alias*) is designed to serve as an intelligent assistant for tackle diverse and complicated real-world tasks, providing three operational modes for flexible task execution:
- **Simple React**: Employs vanilla reasoning-acting loops to iteratively solve problems and execute tool calls.
- **Planner-Worker**: Uses intelligent planning to decompose complex tasks into manageable subtasks, with dedicated worker agents handling each subtask independently.
- **Built-in Agents**: Leverages specialized agents tailored for specific domains, including *Deep Research Agent* for comprehensive analysis and *Browser-use Agent* for web-based interactions.

Beyond being a ready-to-use agent, we envision Alias as a foundational template that can be adapted to different scenarios.

📖 **Documentation**: [English](alias/README.md) | [中文](alias/README_ZH.md)

------

## ℹ️ Getting Help

If you:

- Need installation help
- Encounter issues
- Want to understand how a sample works

Please:

1. Read the sample-specific `README.md`.
2. File a [GitHub Issue](https://github.com/agentscope-ai/agentscope-samples/issues).
3. Join the community discussions:

| [Discord](https://discord.gg/eYMpfnkG8h)                                                                                         | DingTalk                                                                                                                          |
|----------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| <img src="https://gw.alicdn.com/imgextra/i1/O1CN01hhD1mu1Dd3BWVUvxN_!!6000000000238-2-tps-400-400.png" width="100" height="100"> | <img src="https://img.alicdn.com/imgextra/i1/O1CN01LxzZha1thpIN2cc2E_!!6000000005934-2-tps-497-477.png" width="100" height="100"> |

------

## 🤝 Contributing

We welcome contributions such as:

- Bug reports
- New feature requests
- Documentation improvements
- Code contributions

See the [Contributing](https://github.com/agentscope-ai/agentscope-samples/blob/main/CONTRIBUTING.md) for details.

------

## 📄 License

This project is licensed under the **Apache 2.0 License** – see the [LICENSE](https://github.com/agentscope-ai/agentscope-samples/blob/main/LICENSE) file for details.


------

## 🔗 Resources

- [AgentScope Documentation](https://doc.agentscope.io/)
- [AgentScope Runtime Documentation](https://runtime.agentscope.io/)
- [AgentScope GitHub Repository](https://github.com/agentscope-ai/agentscope)
- [AgentScope Runtime GitHub Repository](https://github.com/agentscope-ai/agentscope-runtime)

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

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

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!