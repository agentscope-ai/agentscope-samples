# DataJuicer 智能体

基于 [AgentScope](https://github.com/modelscope/agentscope) 和 [Data-Juicer (DJ)](https://github.com/modelscope/data-juicer) 构建的数据处理多智能体系统。该项目展示了如何利用大模型的自然语言理解能力，让非专家用户也能轻松使用 Data-Juicer 的强大数据处理能力。

## 📋 目录

- [📋 目录](#-目录)
- [这个智能体做了什么？](#这个智能体做了什么)
- [架构](#架构)
- [快速开始](#快速开始)
  - [系统要求](#系统要求)
  - [安装](#安装)
  - [配置](#配置)
  - [使用](#使用)
- [智能体介绍](#智能体介绍)
  - [数据处理智能体](#数据处理智能体)
  - [代码开发智能体](#代码开发智能体)
- [高级功能](#高级功能)
  - [算子检索](#算子检索)
    - [检索模式](#检索模式)
    - [使用](#使用-1)
  - [MCP 智能体](#mcp-智能体)
    - [MCP 服务器类型](#mcp-服务器类型)
    - [配置](#配置-1)
    - [使用方法](#使用方法)
- [功能预览](#功能预览)
  - [Data-Juicer 问答智能体 (演示可用)](#data-juicer-问答智能体-演示可用)
  - [数据分析与可视化智能体 (开发中)](#数据分析与可视化智能体-开发中)
  - [常见问题](#常见问题)
  - [优化建议](#优化建议)

## 这个智能体做了什么？

Data-Juicer (DJ) 是一个一站式系统，面向大模型的文本及多模态数据处理。它提供了近200个核心数据处理算子，覆盖文本、图像、视频等多模态数据，支持数据分析、清洗、合成等全流程。

运行本示例后，您可以：
- **智能查询**：从近200个数据处理算子中找到适合您数据场景的算子
- **自动化流程**：描述数据处理需求，自动生成 Data-Juicer YAML 配置并执行
- **自定义扩展**：为特定场景快速开发自定义算子

## 架构

```
用户查询
    ↓
路由智能体 ──┐
            ├── 数据处理智能体 (DJ 智能体)
            |   ├── 通用文件读写工具
            │   ├── query_dj_operators (查询DataJuicer算子)
            │   └── execute_safe_command (执行包含dj-process, dj-analyze在内的安全命令)
            │
            └── 代码开发智能体 (DJ Dev 智能体)
                ├── 通用文件读写工具
                ├── get_basic_files (获取基础的开发知识)
                ├── get_operator_example (获取与需求相关的算子源码示例)
                └── configure_data_juicer_path (配置DataJuicer路径)
```

## 快速开始

### 系统要求

- Python 3.8+
- 有效的 DashScope API 密钥
- 可选：Data-Juicer 源码（用于自定义算子开发）

### 安装

```bash
uv pip install -e .
```

### 配置

1. **设置 API 密钥**

```bash
export DASHSCOPE_API_KEY="your-dashscope-key"
```

2. **可选：配置 Data-Juicer 路径（用于自定义算子开发）**

```bash
export DATA_JUICER_PATH="your-data-juicer-path"
```

> **提示**：也可以在运行时通过对话设置，例如：
> - "帮我设置 DataJuicer 路径：/path/to/data-juicer"
> - "帮我更新 DataJuicer 路径：/path/to/data-juicer"

### 使用

通过 `-u` 或 `--use_studio` 参数选择运行方式：

```bash
# 使用 AgentScope Studio（提供交互式界面）
python main.py --use_studio true

# 或使用命令行模式（默认）
python main.py
```

## 智能体介绍

### 数据处理智能体

负责与 Data-Juicer 交互，执行实际的数据处理任务。支持从自然语言描述自动推荐算子、生成配置并执行。

**典型用途：**
- **数据清洗**：去重、移除低质量样本、格式标准化
- **多模态处理**：同时处理文本、图像、视频数据
- **批量转换**：格式转换、数据增强、特征提取

<details>
<summary>查看完整示例日志（from AgentScope Studio）</summary>
<img src="assets/dj_agent_image.png" width="100%">
</details>

### 代码开发智能体

辅助开发自定义数据处理算子，默认使用 `qwen3-coder-480b-a35b-instruct` 模型驱动。

**典型用途：**
- **开发领域特定的过滤或转换算子**
- **集成自有的数据处理逻辑**
- **为特定场景扩展 Data-Juicer 能力**

<details>
<summary>查看完整示例日志（from AgentScope Studio）</summary>
<img src="assets/dj_dev_agent_image.png" width="100%">
</details>

## 高级功能

### 算子检索

DJ 智能体实现了一个智能算子检索工具，通过独立的 LLM 查询环节从 Data-Juicer 的近200个算子中快速找到最相关的算子。这是数据处理智能体和代码开发智能体能够准确运行的关键组件。

我们提供了三种检索模式，可根据不同场景选用：

#### 检索模式

**LLM 检索 (默认)**
- 使用 Qwen-Turbo 模型匹配最相关算子
- 提供详细的匹配理由和相关性评分
- 适合需要高精度匹配的场景，但消耗更多 Token

**向量检索 (vector)**
- 基于 DashScope 文本嵌入和 FAISS 相似度搜索
- 快速且高效，适合大规模检索场景

**自动模式 (auto)**
- 优先尝试 LLM 检索，失败时自动降级到向量检索

#### 使用

通过 `-r` 或 `--retrieve_mode` 参数指定检索模式：

```bash
python main.py --retrieve_mode vector
```

更多参数说明见 `python main.py --help`

### MCP 智能体

Data-Juicer 提供了 MCP (Model Context Protocol) 服务，可直接通过原生接口获取算子信息、执行数据处理，易于迁移和集成，无需单独的 LLM 查询和命令行调用。

#### MCP 服务器类型

Data-Juicer 提供两种 MCP 服务器模式：

**Recipe-Flow（数据菜谱）**
- 根据算子类型和标签进行筛选
- 支持将多个算子组合成数据菜谱运行
  
**Granular-Operators（细粒度算子）**
- 将每个算子作为独立工具提供
- 通过环境变量灵活指定算子列表
- 构建完全定制化的数据处理管道

详细信息请参考：[Data-Juicer MCP 服务文档](https://modelscope.github.io/data-juicer/en/main/docs/DJ_service.html#mcp-server)

> **注意**：Data-Juicer MCP 服务器目前处于早期开发阶段，功能和工具可能会随着持续开发而变化。

#### 配置

在 `configs/mcp_config.json` 中配置服务地址：

```json
{
    "mcpServers": {
        "DJ_recipe_flow": {
            "url": "http://127.0.0.1:8080/sse"
        }
    }
}
```

#### 使用方法

启用 MCP 智能体替代 DJ 智能体：

```bash
# 启用 MCP 智能体和开发智能体
python main.py --available_agents [dj_mcp, dj_dev]

# 或使用简写
python main.py -a [dj_mcp, dj_dev]
```


## 功能预览

Data-Juicer 智能体生态系统正在快速扩展，以下是当前正在开发或计划中的新智能体：

### Data-Juicer 问答智能体 (演示可用)

为用户提供关于 Data-Juicer 算子、概念和最佳实践的详细解答。

<video controls width="100%" height="auto" playsinline>
    <source src="https://github.com/user-attachments/assets/a8392691-81cf-4a25-94da-967dcf92c685" type="video/mp4">
    您的浏览器不支持视频标签。
</video>

### 数据分析与可视化智能体 (开发中)

生成数据分析和可视化结果，预计近期发布。

### 常见问题

**Q: 如何获取 DashScope API 密钥？**
A: 访问 [DashScope 官网](https://dashscope.aliyun.com/) 注册账号并申请 API 密钥。

**Q: 为什么算子检索失败？**
A: 请检查网络连接和 API 密钥配置，或尝试切换到向量检索模式。

**Q: 如何调试自定义算子？**
A: 确保 Data-Juicer 路径配置正确，并查看代码开发智能体提供的示例代码。

**Q: MCP 服务连接失败怎么办？**
A: 检查 MCP 服务器是否正在运行，确认配置文件中的 URL 地址正确。

### 优化建议

- 对于大规模数据处理，建议使用DataJuicer提供的分布式模式
- 合理设置批处理大小以平衡内存使用和处理速度
- 更多进阶数据处理（合成、Data-Model Co-Development）等特性能力请参考DataJuicer[文档页](https://modelscope.github.io/data-juicer/zh_CN/main/index_ZH)


---

**贡献指南**：欢迎提交 Issue 和 Pull Request 来改进agentscope、DataJuicer Agent及[DataJuicer](https://modelscope.github.io/data-juicer/zh_CN/main/index_ZH#id4)。如果您在使用过程中遇到问题或有功能建议，请随时联系我们。
