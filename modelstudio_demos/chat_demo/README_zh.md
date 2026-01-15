# 阿里云百炼高代码Agent Starter

## 项目简介

这是一个基于FastAPI Web框架和AgentScope的启动项目，能给到你通过本地或者阿里云百炼高代码云端部署Agent的初始模版代码包。
支持直接本地运行测试和通过 uvicorn 部署到阿里云百炼，自由代码编写组装阿里云百炼&AgentScope中的LLM、MCP、RAG、记忆、搜索等原子能力。

## 安装依赖

首先确保你已经安装了 Python 3.10 或更高版本。

## 本地启动测试

```bash
pip install -r requirements.txt
```

### 依赖说明

- `fastapi`: 用于构建 Web API
- `uvicorn`: 用于运行 FastAPI 应用
- `agentscope-runtime`: AgentScope 运行时环境
- `PyYAML`: PyYAML解析包

## 配置

### DashScope API 配置

要使用 LLM 功能，你需要配置阿里云百炼 DashScope API KEY，后续云端部署也可以添加到部署机器环境变量中：
1. 在 `deploy_starter/config.yml` 文件中设置 `DASHSCOPE_API_KEY`：
   ```yaml
   DASHSCOPE_API_KEY: "your-api-key-here,sk-xxx"
   ```

2. 或者设置环境变量：
   ```bash
   export DASHSCOPE_API_KEY="your-api-key-here,sk-xxx"
   ```

## 运行项目

### 切换到项目根目录 直接运行

```bash
cd 当前项目根目录,setup.py 文件所在的目录
```

```bash
python -m deploy_starter.main
```

### 使用 uvicorn 运行

```bash
uvicorn deploy_starter.main:app --host 127.0.0.1 --port 8080 --reload
```

## API 接口

### 健康检查

检查应用是否正常运行：

```bash
curl http://127.0.0.1:8080/health
```

预期响应：
```
"OK"
```

### 聊天接口

与 LLM 进行对话（需要配置 DashScope API 密钥）：

```bash
curl -X POST http://127.0.0.1:8080/process \
  -H "Content-Type: application/json" \
  -d '{"message": "你好，世界！"}'
```

预期响应：
```json
{
  "response": "你好！有什么我可以帮助你的吗？"
}
```

## 注意事项

1. 如果未配置 `DASHSCOPE_API_KEY`，聊天功能将不可用。
2. 默认使用 `qwen-turbo` 模型，可以在 `config.yml` 中修改 `DASHSCOPE_MODEL_NAME` 来切换模型。

## 阿里云百炼高代码 云端部署

### 优先可以选择阿里云百炼高代码控制台直接上传代码包
[创建应用-高代码应用](https://bailian.console.aliyun.com//app-center?tab=app#/app-center)

![img_1.png](deploy_by_ui.png)

### 命令行console方式进行代码上传部署-更适合快速修改代码进行更新部署
#### 1. 安装依赖

```bash
pip install agentscope-runtime==1.0.0
pip install "agentscope-runtime[deployment]==1.0.0"
```

#### 2. 设置环境变量

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=...            # 你的阿里云账号AccessKey（必填）
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=...        # 你的阿里云账号SecurityKey（必填）

# 可选：如果你希望使用单独的 OSS AK/SK，可设置如下（未设置时将使用到上面的账号 AK/SK），请确保账号有 OSS 的读写权限
export MODELSTUDIO_WORKSPACE_ID=...               # 你的百炼业务空间id
export OSS_ACCESS_KEY_ID=...
export OSS_ACCESS_KEY_SECRET=...
export OSS_REGION=cn-beijing
```

#### 3. 打包和部署

##### 方式 A：手动构建 wheel 文件

确保你的项目可以被构建为 wheel 文件。你可以使用 setup.py、setup.cfg 或 pyproject.toml。

构建 wheel 文件：
```bash
python setup.py bdist_wheel
```

部署：
```bash
runtime-fc-deploy \
  --deploy-name [你的应用名称] \
  --whl-path [到你的wheel文件的相对路径 如"/dist/your_app.whl"]
```

![img.png](deploy_by_cli.png)

具体请查看阿里云百炼高代码部署文档：[阿里云百炼高代码部署文档](https://bailian.console.aliyun.com/?tab=api#/api/?type=app&url=2983030)
