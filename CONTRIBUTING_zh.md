# 如何贡献

感谢您对 AgentScope Samples 的关注！AgentScope Samples 提供基于 AgentScope 和 AgentScope Runtime 构建的即用型智能体示例。我们欢迎各种类型的贡献，从新的示例智能体应用到错误修复和文档改进。

## 报告问题

### Bug

报告 bug 前，请先测试最新版本并搜索已有问题。提交 bug 报告时，请包括：

- 清晰的问题描述和复现步骤
- 代码/错误信息
- 环境详情（操作系统、Python 版本、AgentScope 版本）
- 受影响的示例

### 安全问题

通过[阿里巴巴安全响应中心（ASRC）](https://security.alibaba.com/)报告安全问题。

## 请求新功能

如果您希望有一个在 AgentScope Samples 中不存在的功能或新类型的示例，请在 GitHub 上开一个功能请求 issue 来描述：

- 该功能或示例及其目的
- 它应该如何工作
- 它解决了什么问题或演示了什么用例

**注意**：如果您想贡献自己的示例，也请先开一个 issue 讨论您的想法，避免重复工作。



## 贡献代码

### 设置

1. **Fork 并克隆**仓库

2. **创建分支**：
   ```bash
   git checkout -b feature/your-sample-name
   ```

### 创建新示例

#### 选择相关场景

我们鼓励涵盖以下领域的示例（但不限于）：

| 领域 | 示例想法 |
|------|---------|
| **金融** | 智能投顾、风险评估、财务报告分析 |
| **医疗健康** | 症状检查器、病历摘要、用药提醒 |
| **教育** | 个性化辅导、自动评分、知识问答检索 |
| **电商/零售** | 客户服务、产品推荐、库存管理 |
| **游戏/娱乐** | NPC 对话系统、动态故事生成器 |
| **办公自动化** | 会议摘要、自动回复邮件、日程协调 |
| **科研** | 文献综述助手、数据分析智能体 |
| **SRE/运维** | 告警分类、日志异常检测、根因分析、自动修复建议 |
| **通用工具** | 多智能体工作流、工具调用、记忆管理模式 |

**提示**：选择您熟悉或热衷的领域——真实的用例具有最大的影响力！

#### 目录结构

选择合适的类别（`browser_use/`、`conversational_agents/`、`deep_research/`、`evaluation/`、`functionality/`、`games/`）并创建示例目录。如果不存在合适的类别，您可以在 pull request 中提议一个新类别。

**简单示例：**
```
your_sample_name/
├── README.md
├── main.py
├── your_agent.py
└── requirements.txt
```

**全栈示例**（使用 `_fullstack_runtime` 后缀）：
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

#### README.md 要求（强制）

您的 README.md **必须**包含：

1. **标题和描述**：示例演示的内容

2. **项目结构**（强制）：带说明的文件树
   ```markdown
   ## 🌳 项目结构

   \`\`\`
   .
   ├── README.md                 # 文档
   ├── main.py                   # 入口点
   ├── agent.py                  # 智能体实现
   └── requirements.txt          # 依赖项
   \`\`\`
   ```

3. **前置要求**：Python 版本、API 密钥等

4. **安装**：
   ```bash
   pip install -r requirements.txt
   ```

5. **设置**：环境变量或配置步骤

6. **使用方法**：如何运行示例
   ```bash
   python main.py
   ```

#### 独立安装

每个示例需包含独立的 `requirements.txt` 文件，列出所有必需的依赖项，以确保可独立安装和运行，不依赖其他示例。

### 提交您的贡献

1. **提交**时使用清晰的消息：
   ```bash
   git commit -m "Add: new browser automation sample"
   ```
   使用前缀：`Add:`、`Fix:`、`Update:`、`Doc:`

2. **推送**到您的 fork：
   ```bash
   git push origin feature/your-sample-name
   ```

3. **创建 Pull Request**，包含：
   - 示例演示内容的清晰描述
   - 相关问题的引用（例如 "Closes #123"）

4. **代码审查**：处理维护者的反馈

### 贡献者认可

- 您的名字将被添加到贡献者名单中
- 优秀的示例可能会在 AgentScope 网站、文档或社交媒体上展示
- 您将成为塑造智能体 AI 未来的不断增长的社区的一部分！

感谢您为 AgentScope Samples 做出贡献！如有任何问题，欢迎通过以下方式与我们联系：

- **GitHub Discussions**：提问和分享经验（使用**英文**）
- **Discord**：加入我们的 Discord 频道进行实时讨论
- **钉钉**：中国用户可以加入我们的钉钉群

| [Discord](https://discord.gg/eYMpfnkG8h)                     | DingTalk                                                     |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| <img src="https://gw.alicdn.com/imgextra/i1/O1CN01hhD1mu1Dd3BWVUvxN_!!6000000000238-2-tps-400-400.png" width="100" height="100"> | <img src="https://img.alicdn.com/imgextra/i4/O1CN014mhqFq1ZlgNuYjxrz_!!6000000003235-2-tps-400-400.png" width="100" height="100"> |