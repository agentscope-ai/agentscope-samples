# 如何贡献

感谢您对 AgentScope Samples 的关注！AgentScope Samples 提供基于 AgentScope 和 AgentScope Runtime 构建的即用型智能体示例。我们欢迎各种类型的贡献，从新的示例智能体应用到错误修复和文档改进。

## 社区

通过以下方式与我们联系：

- **GitHub Discussions**：提问和分享经验（使用**英文**）
- **Discord**：加入我们的 Discord 频道进行实时讨论
- **钉钉**：中国用户可以加入我们的钉钉群

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
2. **安装 pre-commit**：
   ```bash
   pip install pre-commit
   pre-commit install
   ```
3. **创建分支**：
   ```bash
   git checkout -b feature/your-sample-name
   ```

### 创建新示例

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

#### 代码质量

我们使用 pre-commit hooks 强制执行：

- **Black**：代码格式化（行长度 79）
- **flake8** 和 **pylint**：代码检查
- **mypy**：类型检查

编写示例代码时：
- 添加清晰的注释，遵循现有代码风格
- 为函数签名添加类型提示
- 保持代码简单，专注于演示特定功能

确保通过所有检查：
```bash
pre-commit run --all-files
```

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

感谢您为 AgentScope Samples 做出贡献！