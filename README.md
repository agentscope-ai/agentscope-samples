# AgentScope Samples

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/agentscope-ai/agentscope-samples/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://www.python.org/)
[![DeepWiki](https://img.shields.io/badge/DeepWiki-agentscope--samples-navy.svg?logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAyCAYAAAAnWDnqAAAAAXNSR0IArs4c6QAAA05JREFUaEPtmUtyEzEQhtWTQyQLHNak2AB7ZnyXZMEjXMGeK/AIi+QuHrMnbChYY7MIh8g01fJoopFb0uhhEqqcbWTp06/uv1saEDv4O3n3dV60RfP947Mm9/SQc0ICFQgzfc4CYZoTPAswgSJCCUJUnAAoRHOAUOcATwbmVLWdGoH//PB8mnKqScAhsD0kYP3j/Yt5LPQe2KvcXmGvRHcDnpxfL2zOYJ1mFwrryWTz0advv1Ut4CJgf5uhDuDj5eUcAUoahrdY/56ebRWeraTjMt/00Sh3UDtjgHtQNHwcRGOC98BJEAEymycmYcWwOprTgcB6VZ5JK5TAJ+fXGLBm3FDAmn6oPPjR4rKCAoJCal2eAiQp2x0vxTPB3ALO2CRkwmDy5WohzBDwSEFKRwPbknEggCPB/imwrycgxX2NzoMCHhPkDwqYMr9tRcP5qNrMZHkVnOjRMWwLCcr8ohBVb1OMjxLwGCvjTikrsBOiA6fNyCrm8V1rP93iVPpwaE+gO0SsWmPiXB+jikdf6SizrT5qKasx5j8ABbHpFTx+vFXp9EnYQmLx02h1QTTrl6eDqxLnGjporxl3NL3agEvXdT0WmEost648sQOYAeJS9Q7bfUVoMGnjo4AZdUMQku50McDcMWcBPvr0SzbTAFDfvJqwLzgxwATnCgnp4wDl6Aa+Ax283gghmj+vj7feE2KBBRMW3FzOpLOADl0Isb5587h/U4gGvkt5v60Z1VLG8BhYjbzRwyQZemwAd6cCR5/XFWLYZRIMpX39AR0tjaGGiGzLVyhse5C9RKC6ai42ppWPKiBagOvaYk8lO7DajerabOZP46Lby5wKjw1HCRx7p9sVMOWGzb/vA1hwiWc6jm3MvQDTogQkiqIhJV0nBQBTU+3okKCFDy9WwferkHjtxib7t3xIUQtHxnIwtx4mpg26/HfwVNVDb4oI9RHmx5WGelRVlrtiw43zboCLaxv46AZeB3IlTkwouebTr1y2NjSpHz68WNFjHvupy3q8TFn3Hos2IAk4Ju5dCo8B3wP7VPr/FGaKiG+T+v+TQqIrOqMTL1VdWV1DdmcbO8KXBz6esmYWYKPwDL5b5FA1a0hwapHiom0r/cKaoqr+27/XcrS5UwSMbQAAAABJRU5ErkJggg==)](https://deepwiki.com/agentscope-ai/agentscope-samples)
[![Docs](https://img.shields.io/badge/docs-AgentScope-blue)](https://doc.agentscope.io/)
[![Runtime Docs](https://img.shields.io/badge/docs-AgentScope%20Runtime-red)](https://runtime.agentscope.io/)
[![Last Commit](https://img.shields.io/github/last-commit/agentscope-ai/agentscope-samples)](https://github.com/agentscope-ai/agentscope-samples)

[[中文README]](README_zh.md)

🎯 **Kickstart Your Agent Journey!**
This is a repository that **brings together a variety of ready-to-run Python agent examples**, ranging from command-line mini-tools to **full-stack deployable applications**.

## 🌟 What is AgentScope?

**[AgentScope](https://github.com/agentscope-ai/agentscope)** is a **multi-agent framework** that lets you rapidly build **LLM-based intelligent applications**:

> Learn more in the [AgentScope Documentation](https://doc.agentscope.io/)

- 🧠 Define agents and integrate tools
- 📡 Manage context and conversations
- 🤝 Orchestrate collaboration among multiple agents to accomplish tasks



**[AgentScope-Runtime](https://github.com/agentscope-ai/agentscope-runtime)** is the runtime framework that enables you to deploy agents as API services:

> Learn more in the [AgentScope Runtime Documentation](https://runtime.agentscope.io/)

1. 🔄 **Scalable deployment management for multiple agents**
2. 🛡️ **Secure sandbox execution for tools**

## ⚡ Getting Started

📌 **Before running an example**, please check the corresponding `README.md` for installation and execution instructions.

> - All examples are built with **Python**.
> - Examples are organized by **functionality** and **usage scenario**.
> - Some examples use **AgentScope** only.
> - Some examples use **both AgentScope and AgentScope Runtime** to implement **deployable full-stack applications with frontend + backend**.
> - Full-stack runtime versions have folder names ending with **`_fullstack_runtime`**.

## 🌳 Repository Structure

```bash
├── alias/                                  # Agent to solve real-world problems
├── browser_use/
│   ├── agent_browser/                      # Pure Python browser agent
│   ├── browser_use_agent_pro/              # Advanced pure python browser agent
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
├── functionality/
│   └── xquik_mcp_discovery/                # Read-only Xquik MCP tool discovery
│
├── data_juicer_agent/                      # Data processing multi-agent system
├── tuner/                                  # Tune AgentScope applications using AgentScope Tuner
│   ├── math_agent/                         # A quick start example for tuning
│   ├── frozen_lake/                        # Teach an agent to play a game requiring multiple steps
│   ├── learn_to_ask/                       # Using LLM-as-a-judge to facilitate agent tuning
│   ├── email_search/                       # Enhance the tool use ability of your agent
│   ├── werewolves/                         # Enhance a multi-agent application
│   └── data_augment/                       # Data augmentation for tuning
├── sample_template/                        # Template for new sample contributions
└── README.md
```

## 📌 Example List

| Category                | Example Folder                                        | Uses AgentScope | Use AgentScope Runtime | Description                                      |
| ----------------------- |-------------------------------------------------------| --------------- | ------------ |--------------------------------------------------|
| **Data Processing**     | data_juicer_agent/                                   | ✅               | ❌            | Multi-agent data processing with Data-Juicer     |
| **Browser Use**         | browser_use/agent_browser                             | ✅               | ❌            | Command-line browser automation using AgentScope |
|                         | browser_use/browser_use_agent_pro                     | ✅               | ❌            | Advanced command-line Python browser agent using AgentScope              |
|                         | browser_use/browser_use_fullstack_runtime             | ✅               | ✅            | Full-stack browser automation with UI & sandbox  |
| **Deep Research**       | deep_research/agent_deep_research                     | ✅               | ❌            | Multi-agent research pipeline                    |
|                         | deep_research/qwen_langgraph_search_fullstack_runtime | ❌               | ✅            | Full-stack deep research app                     |
| **Games**               | games/game_werewolves                                 | ✅               | ❌            | Multi-agent roleplay game                        |
| **Conversational Apps** | conversational_agents/chatbot_fullstack_runtime       | ✅               | ✅            | Chatbot application with frontend/backend        |
|                         | conversational_agents/chatbot                         | ✅               | ❌            |                                                  |
|                         | conversational_agents/multiagent_conversation         | ✅               | ❌            | Multi-agent dialogue scenario                    |
|                         | conversational_agents/multiagent_debate               | ✅               | ❌            | Agents engaging in debates                       |
| **Evaluation**          | evaluation/ace_bench                                  | ✅               | ❌            | Benchmarks with ACE Bench                        |
| **Functionality**       | functionality/xquik_mcp_discovery                     | ✅               | ❌            | Read-only MCP discovery for X workflows          |
| **General AI Agent**               | alias/                                                | ✅               | ✅                      | Agent application running in sandbox to solve diverse real-world problems |
| **Financial Trading**   | evotraders/                                           | ✅               | ❌            | Self-Evolving Multi-Agent Trading System         |

## 🌈 Featured Examples

### 📊 DataJuicer Agent

A powerful multi-agent data processing system that leverages Data-Juicer's 200+ operators for intelligent data processing:

- **Intelligent Query**: Find suitable operators from 200+ data processing operators
- **Automated Pipeline**: Generate Data-Juicer YAML configurations from natural language
- **Custom Development**: Create domain-specific operators with AI assistance
- **Multiple Retrieval Modes**: LLM-based and vector-based operator matching
- **MCP Integration**: Native Model Context Protocol support

📖 **Documentation**: [English](data_juicer_agent/README.md) | [中文](data_juicer_agent/README_ZH.md)

### 🕵🏻 Alias-Agent

*Alias-Agent* (short for *Alias*) is designed to serve as an intelligent assistant for tackle diverse and complicated real-world tasks, providing three operational modes for flexible task execution:
- **Simple React**: Employs vanilla reasoning-acting loops to iteratively solve problems and execute tool calls.
- **Planner-Worker**: Uses intelligent planning to decompose complex tasks into manageable subtasks, with dedicated worker agents handling each subtask independently.
- **Built-in Agents**: Leverages specialized agents tailored for specific domains, including *Deep Research Agent* for comprehensive analysis and *Browser-use Agent* for web-based interactions.

Beyond being a ready-to-use agent, we envision Alias as a foundational template that can be adapted to different scenarios.

📖 **Documentation**: [English](alias/README.md) | [中文](alias/README_ZH.md)

### 📈 EvoTraders

*EvoTraders* is a financial trading agent framework that builds a trading system capable of continuous learning and evolution in real markets through multi-agent collaboration and memory systems. Key features include:

- **Multi-Agent Collaboration**: A team of specialized analysts (Fundamentals, Technical, Sentiment, Valuation) and managers collaborating like a real trading team.
- **Memory Enhancement & Evolution**: Agents reflect and summarize after trades using the ReMe memory framework, evolving their trading styles over time.
- **Real-Time & Backtesting**: Supports both real-time market data integration for live trading and backtesting modes.
- **Visualized Dashboard**: A comprehensive frontend to observe analysis processes, communication, and performance tracking.

📖 **Documentation**: [English](evotraders/README.md) | [中文](evotraders/README_zh.md)

## 🆘 Getting Help

If you:

- Need installation help
- Encounter issues
- Want to understand how a sample works

Please:

1. Read the sample-specific `README.md`.
2. File a [GitHub Issue](https://github.com/agentscope-ai/agentscope-samples/issues).
3. Join the community discussions:

| [Discord](https://discord.gg/eYMpfnkG8h)                     | DingTalk                                                     |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| <img src="https://gw.alicdn.com/imgextra/i1/O1CN01hhD1mu1Dd3BWVUvxN_!!6000000000238-2-tps-400-400.png" width="100" height="100"> | <img src="https://img.alicdn.com/imgextra/i4/O1CN014mhqFq1ZlgNuYjxrz_!!6000000003235-2-tps-400-400.png" width="100" height="100"> |

## 🤝 Contributing

We welcome contributions such as:

- Bug reports
- New feature requests
- Documentation improvements
- Code contributions

See the [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the **Apache 2.0 License** – see the [LICENSE](LICENSE) file for details.

## Contributors ✨

<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-27-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/emoji-key/)):

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

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!
