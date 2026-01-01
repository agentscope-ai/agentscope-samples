import os
import uuid

from setuptools import setup

# 读取requirements.txt中的依赖
with open("requirements.txt") as f:
    requirements = f.read().splitlines()


# 读取config.yml文件
def read_config():
    config_path = os.path.join(
        os.path.dirname(__file__), "deploy_starter", "config.yml"
    )
    config = {}
    with open(config_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip().strip("\"'")
                    if value.lower() == "true":
                        value = True
                    elif value.lower() == "false":
                        value = False
                    elif value.isdigit():
                        value = int(value)
                    config[key] = value
    return config


# 读取README.md文件
def read_readme():
    readme_files = ["README.md", "README.rst", "README.txt"]
    for filename in readme_files:
        if os.path.exists(filename):
            with open(filename, "r") as fh:
                return fh.read()
    return "A FastAPI application with AgentScope runtime"


# 读取配置
config = read_config()

# 获取配置值
setup_package_name = config.get("SETUP_PACKAGE_NAME", "deploy_starter")
setup_module_name = config.get("SETUP_MODULE_NAME", "main")
setup_function_name = config.get("SETUP_FUNCTION_NAME", "run_app")
setup_command_name = config.get("SETUP_COMMAND_NAME", "ModelStudio-Agent-starter")

# 生成带UUID的包名
base_name = config.get("SETUP_NAME", "ModelStudio-Agent-starter")
unique_name = f"{base_name}-{uuid.uuid4().hex[:8]}"

# 创建包结构
setup(
    name=unique_name,
    version=config.get("SETUP_VERSION", "0.1.0"),
    description=config.get("SETUP_DESCRIPTION", "ModelStudio-Agent-starter"),
    long_description=config.get(
        "SETUP_LONG_DESCRIPTION",
        "ModelStudio-Agent-starter services, supporting both direct execution and uvicorn deployment",
    ),
    packages=[setup_package_name],
    package_dir={setup_package_name: setup_package_name},
    install_requires=requirements,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            f"{setup_command_name}={setup_package_name}.{setup_module_name}:{setup_function_name}",
        ],
    },
    include_package_data=True,
    package_data={
        setup_package_name: ["config.yml"],
    },
)
