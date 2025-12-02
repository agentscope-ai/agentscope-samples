<div align="center">

<img src="assets/alias.png" alt="Alias-Agent Logo" width="500" height="250" style="vertical-align: middle; margin-right: 20px;">
<h1 style="text-decoration: none; border-bottom: none; display: inline; vertical-align: middle; margin: 0;">Alias-Agent: Start It Now, Extend It Your Way, Deploy All with Ease</h1>

</div>

<p align="center">
    <a href="https://pypi.org/project/alias-agent/">
        <img
            src="https://img.shields.io/badge/python-3.10+-blue?logo=python"
            alt="python"
        />
    </a>
    <a href="./LICENSE">
        <img
            src="https://img.shields.io/badge/license-Apache--2.0-black"
            alt="license"
        />
    </a>
    <a href="https://github.com/agentscope-ai/agentscope">
        <img
            src="https://img.shields.io/badge/built--on-AgentScope-blue?logo=github"
            alt="agentscope"
        />
    </a>
</p>


*Alias-Agent* (short for *Alias*) is an LLM-empowered agent built on [AgentScope](https://github.com/agentscope-ai/agentscope) and [AgentScope-runtime](https://github.com/agentscope-ai/agentscope-runtime/), designed to serve as a general-purpose intelligent assistant for responding to user queries. Alias excels at decomposing complicated problems, constructing roadmaps, and applying appropriate strategies to tackle diverse real-world tasks.


Alias employs a multi-mode operational mechanism for flexible task execution, including `General`, `Browser Use`, `Deep Research`, `Financial Analysis`, and `Data Science`. When switching between different operational modes, Alias is equipped with tailored instructions, specialized tool sets, and the capability to orchestrate various expert agents. This allows Alias to better adapt to the specific requirements of diverse downstream tasks. For example, when handling financial analysis, Alias employs traceable reasoning chains and generates explainable results to increase user trust in its decision-making, along with optimized report visualizations; When resolving data science tasks, Alias can access user-associated databases and is designed to facilitate efficient data analysis, processing, and prediction.

We aim for Alias to serve as an out-of-the-box solution that users can readily deploy for various tasks, supported by a comprehensive pipeline for agent development, testing, and deployment based on the AgentScope ecosystem. Beyond being a ready-to-use agent, we also envision Alias as a foundational template that can be adapted for diverse scenarios. Developers are encouraged to extend and customize Alias at the tool, prompt, and agent levels to meet specific requirements.

We welcome more developers to join the community and contribute to ongoing innovation.

## Installation

Install the Alias package in development mode:

```bash
pip install -e .

# SETUP SANDBOX
# If you are using colima, then you need to run the following
# export DOCKER_HOST=unix://$HOME/.colima/default/docker.sock
# More details can refer to https://runtime.agentscope.io/en/sandbox.html

# Option 1: Pull from registry
export RUNTIME_SANDBOX_REGISTRY=agentscope-registry.ap-southeast-1.cr.aliyuncs.com
docker pull agentscope-registry.ap-southeast-1.cr.aliyuncs.com/agentscope/runtime-sandbox-alias:latest

# Option 2: pull from docker hub
docker pull agentscope/runtime-sandbox-alias:latest
```

This will install the `alias` command-line tool.

## Basic Usage

The `alias` CLI provides a terminal interface to run AI agents for various tasks.

### Run Command

First of all, set up API keys
```bash
# Model API keys
export DASHSCOPE_API_KEY=your_dashscope_api_key_here

# Using other models: go to src/alias/agent/run.py and add your model to MODEL_FORMATTER_MAPPING, then run the bash to set your model and api key. For example:
#export MODEL=gpt-5
#export OPENAI_API_KEY=your_openai_api_key_here

# Search api key (required for deep research)
export TAVILY_API_KEY=your_tavily_api_key_here
```

Execute an agent task:

```bash
alias_agent run --task "Your task description here"
```

### Examples

#### Run with all agents (Meta Planner with workers):
```bash
alias_agent run --task "Analyze Meta stock performance in Q1 2025"
```

#### Run with only browser agent:

```bash
alias_agent run --mode browser --task "Search five latest research papers about browser-use agent"
```

#### Upload files to sandbox workspace:
```bash
# Upload a single file
alias_agent run --task "Analyze this data" --files data.csv

# Upload multiple files
alias_agent run --task "Process these files and create a summary report" --files report.txt data.csv notes.md

# Using short form (-f)
alias_agent run --task "Review the documents" -f document1.pdf document2.txt

# Combine with other options
alias_agent run --mode all --task "Analyze the data and generate insights" --files dataset.csv --verbose
```

**Note**: Files uploaded with `--files` are automatically copied to the `/workspace` directory in the sandbox with their original filenames, making them immediately accessible to the agent.

### Obtain agent-generated files
In the directory where you ran `alias_agent`, you should find a `sessions_mount_dir` directory with subdirectories, each containing the content from `/workspace` of the sandboxes' mounted file systems. All generated files should be located there.

