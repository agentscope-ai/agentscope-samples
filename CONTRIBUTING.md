# How to Contribute

Thank you for your interest in AgentScope Samples! AgentScope Samples provides ready-to-use agent examples built on AgentScope and AgentScope Runtime. We welcome all types of contributions, from new sample agent applications to bug fixes and documentation improvements.

## Reporting Issues

### Bugs

Before reporting a bug, please test with the latest version and search existing issues. When submitting a bug report, include:

- Clear description of the issue and reproduction steps
- Code/error messages
- Environment details (OS, Python version, AgentScope version)
- Affected examples

### Security Issues

Report security issues through [Alibaba Security Response Center (ASRC)](https://security.alibaba.com/).

## Requesting New Features

If you'd like a feature or new type of example that doesn't exist in AgentScope Samples, please open a feature request issue on GitHub describing:

- The feature or example and its purpose
- How it should work
- What problem it solves or what use case it demonstrates

**Note**: If you want to contribute your own example, please also open an issue first to discuss your idea and avoid duplicate work.



## Contributing Code

### Setup

1. **Fork and clone** the repository

2. **Create a branch**:
   ```bash
   git checkout -b feature/your-sample-name
   ```

### Creating New Examples

#### Choose a Relevant Scenario

We encourage examples across various domains including (but not limited to):

| Domain | Example Ideas |
|--------|---------------|
| **Finance** | Robo-advisors, risk assessment, financial report analysis |
| **Healthcare** | Symptom checker, medical record summarization, medication reminders |
| **Education** | Personalized tutoring, auto-grading, Q&A knowledge retrieval |
| **E-commerce / Retail** | Customer service, product recommendation, inventory management |
| **Gaming / Entertainment** | NPC dialogue systems, dynamic story generators |
| **Office Automation** | Meeting summarizers, auto-reply email agents, scheduling coordinators |
| **Research** | Literature review assistants, data analysis agents |
| **SRE / DevOps** | Alert triage, log anomaly detection, root cause analysis, automated remediation |
| **General Utilities** | Multi-agent workflows, tool calling, memory management patterns |

**Tip**: Pick a domain you know well or are passionate about—realistic use cases have the greatest impact!

#### Directory Structure

Choose an appropriate category (`browser_use/`, `conversational_agents/`, `deep_research/`, `evaluation/`, `functionality/`, `games/`) and create your example directory. If a suitable category doesn't exist, you can propose a new one in your pull request.

**Simple example:**
```
your_sample_name/
├── README.md
├── main.py
├── your_agent.py
└── requirements.txt
```

**Full-stack example** (use `_fullstack_runtime` suffix):
```
your_sample_fullstack_runtime/
├── README.md
├── backend/
│   ├── requirements.txt
│   └── ...
└── frontend/
    ├── package.json
    └── ...
```

#### README.md Requirements (Mandatory)

Your README.md **must** include:

1. **Title and Description**: What the example demonstrates

2. **Project Structure** (mandatory): File tree with descriptions
   ```markdown
   ## 🌳 Project Structure

   \`\`\`
   .
   ├── README.md                 # Documentation
   ├── main.py                   # Entry point
   ├── agent.py                  # Agent implementation
   └── requirements.txt          # Dependencies
   \`\`\`
   ```

3. **Prerequisites**: Python version, API keys, etc.

4. **Installation**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Setup**: Environment variables or configuration steps

6. **Usage**: How to run the example
   ```bash
   python main.py
   ```

#### Standalone Installation

Each example must include a standalone `requirements.txt` file listing all necessary dependencies to ensure it can be installed and run independently without relying on other examples.


### Submitting Your Contribution

1. **Commit** with clear messages:
   ```bash
   git commit -m "Add: new browser automation sample"
   ```
   Use prefixes: `Add:`, `Fix:`, `Update:`, `Doc:`

2. **Push** to your fork:
   ```bash
   git push origin feature/your-sample-name
   ```

3. **Create a Pull Request** including:
   - Clear description of what the example demonstrates
   - References to related issues (e.g., "Closes #123")

4. **Code Review**: Address feedback from maintainers

### Recognition for Contributors

- Your name will be added to the contributors list
- Outstanding examples may be featured on the AgentScope website, documentation, or social media
- You'll be part of a growing community shaping the future of agentic AI!

Thank you for contributing to AgentScope Samples! If you have any questions, feel free to reach out through:

- **GitHub Discussions**: Ask questions and share experiences (use **English**)
- **Discord**: Join our Discord channel for real-time discussions
- **DingTalk**: Chinese users can join our DingTalk group

| [Discord](https://discord.gg/eYMpfnkG8h)                     | DingTalk                                                     |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| <img src="https://gw.alicdn.com/imgextra/i1/O1CN01hhD1mu1Dd3BWVUvxN_!!6000000000238-2-tps-400-400.png" width="100" height="100"> | <img src="https://img.alicdn.com/imgextra/i4/O1CN014mhqFq1ZlgNuYjxrz_!!6000000003235-2-tps-400-400.png" width="100" height="100"> |

