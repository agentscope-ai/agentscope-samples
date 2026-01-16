# AgentScope Tuner

This directory contains several examples of how to use the AgentScope Tuner for tuning AgentScope applications. The table below summarizes the available examples:

| Example Name      | Description                                                                        | Example Path                    | Multi-step Interaction  |  LLM-as-a-Judge | Tool-use | Multi-Agent | Data Augmentation |
|-------------------|------------------------------------------------------------------------------------|---------------------------------|-------------------------|-----------------|----------|-------------|-------------------|
| Math Agent        | A quick start example for tuning a math-solving agent to enhance its capabilities. | [math_agent](./math_agent)      | ✅ | ❌ | ❌ | ❌ | ❌ |
| Frozen Lake       | Make an agent to navigate the Frozen Lake environment in multi-step interactions.  | [frozen_lake](./frozen_lake)    | ✅ | ❌ | ❌ | ❌ | ❌ |
| Learn to Ask      | Using LLM as a judge to provide feedback to facilitate agent tuning.               | [learn_to_ask](./learn_to_ask)  | ✅ | ✅ | ❌ | ❌ | ❌ |
| Email Search      | Enhance the tool use ability of your agent on tasks without ground truth.          | [email_search](./email_search)  | ✅ | ✅ | ✅ | ❌ | ❌ |
| Werewolf Game     | Enhance the agent's performance in a multi-agent game setting.                     | [werewolves](./werewolves)| ✅ | ✅ | ✅ | ✅ | ❌ |
| Data Augment      | Data augmentation for better tuning results.                                       | [data_augment](./data_augment)  | ❌ | ❌ | ❌ | ❌ | ✅ |

Each example contains a README file with detailed instructions on how to set up and run the tuning process for that specific scenario. Feel free to explore and modify the examples to suit your needs!


## Prerequisites

AgentScope Tuner requires:

- Python 3.10 or higher
- `agentscope>=1.0.12`
- `trinity-rft>=0.4.1`

AgentScope Tuner is built on top of [Trinity-RFT](https://github.com/modelscope/Trinity-RFT).
Please refer to the [Trinity-RFT installation guide](https://modelscope.github.io/Trinity-RFT/en/main/tutorial/trinity_installation.html)
for detailed instructions on how to set up the environment.
