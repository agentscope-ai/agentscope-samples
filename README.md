# AgentScope Sample Agents

<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-4-orange.svg?style=flat-square)](#contributors-)
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
├── functionality/
│   ├── long_term_memory_mem0/              # Long-term memory integration
│   ├── mcp/                                # Memory/Context Protocol demo
│   ├── plan/                               # Plan with ReAct Agent
│   ├── rag/                                # RAG in AgentScope
│   ├── session_with_sqlite/                # Persistent conversation with SQLite
│   ├── stream_printing_messages/           # Streaming and printing messages
│   ├── structured_output/                  # Structured output parsing and validation
│   ├── multiagent_concurrent/              # Concurrent multi-agent task execution
│   └── meta_planner_agent/                  # Planning agent with tool orchestration
│
└── README.md
```

------

## 📌 Example List

| Category                | Example Folder                                        | Uses AgentScope | Use AgentScope Runtime | Description                                      |
| ----------------------- |-------------------------------------------------------| --------------- | ------------ |--------------------------------------------------|
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
| **Functionality Demos** | functionality/long_term_memory_mem0                   | ✅               | ❌            | Long-term memory with mem0 support               |
|                         | functionality/mcp                                     | ✅               | ❌            | Memory/Context Protocol demo                     |
|                         | functionality/session_with_sqlite                     | ✅               | ❌            | Persistent context with SQLite                   |
|                         | functionality/structured_output                       | ✅               | ❌            | Structured data extraction and validation        |
|                         | functionality/multiagent_concurrent                   | ✅               | ❌            | Concurrent task execution by multiple agents     |
|                         | functionality/meta_planner_agent                      | ✅               | ❌            | Planning agent with tool orchestration           |
|                         | functionality/plan                                    | ✅               | ❌            | Task planning with ReAct agent                   |
|                         | functionality/rag                                     | ✅               | ❌            | Retrieval-Augmented Generation (RAG) integration |
|                         | functionality/stream_printing_messages                | ✅               | ❌            | Real-time message streaming and printing         |

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