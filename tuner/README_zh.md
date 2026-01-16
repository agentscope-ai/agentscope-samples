# AgentScope Tuner

本目录包含了多个使用 AgentScope Tuner 对 AgentScope 应用进行调优的示例。下表总结了可用的示例：

| 示例名称         | 描述                                                                 | 示例路径                        | 多步交互 | LLM 评审 | 工具使用 | 多智能体 | 数据增强 |
|------------------|-------------------------------------------|---------------------------------|----------|----------|----------|----------|----------|
| 数学智能体         | 快速入门示例，调优数学智能体以提升其能力。     | [math_agent](./math_agent)      | ✅       | ❌       | ❌       | ❌       | ❌       |
| Frozen Lake       | 让智能体在与 frozen lake 环境的多步交互中学习。           | [frozen_lake](./frozen_lake)    | ✅       | ❌       | ❌       | ❌       | ❌       |
| Learn to Ask      | 使用 LLM 作为评审，为智能体调优提供反馈      | [learn_to_ask](./learn_to_ask)  | ✅       | ✅       | ❌       | ❌       | ❌       |
| 邮件搜索         | 在无标准答案任务中提升智能体的工具使用能力。     | [email_search](./email_search)  | ✅       | ✅       | ✅       | ❌       | ❌       |
| 狼人杀游戏       | 提升智能体在多智能体游戏场景下的表现。          | [werewolves](./werewolves)| ✅       | ✅       | ✅       | ✅       | ❌       |
| 数据增强         | 通过数据增强获得更好的调优效果。               | [data_augment](./data_augment)  | ❌       | ❌       | ❌       | ❌       | ✅       |

每个示例目录下均包含详细的 README 文件，介绍了该场景下的调优流程和使用方法。欢迎根据实际需求进行探索和修改！

## 前置要求

AgentScope Tuner 需要：

- Python 3.10 或更高版本
- `agentscope>=1.0.12`
- `trinity-rft>=0.4.1`

AgentScope Tuner 基于 [Trinity-RFT](https://github.com/modelscope/Trinity-RFT) 构建。
请参考 [Trinity-RFT 安装指南](https://modelscope.github.io/Trinity-RFT/zh/main/tutorial/trinity_installation.html)
获取详细的安装方法。
