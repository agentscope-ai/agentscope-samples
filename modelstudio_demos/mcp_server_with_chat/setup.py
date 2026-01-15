# -*- coding: utf-8 -*-
import os
import uuid

from setuptools import setup

# Read dependencies from requirements.txt
with open("requirements.txt", encoding="utf-8") as requirements_file:
    requirements = requirements_file.read().splitlines()


# Read config.yml file
def read_config():
    config_path = os.path.join(
        os.path.dirname(__file__),
        "deploy_starter",
        "config.yml",
    )
    config_data = {}
    with open(config_path, encoding="utf-8") as config_file:
        for line in config_file:
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
                    config_data[key] = value
    return config_data


# Read README.md file
def read_readme():
    readme_files = ["README.md", "README.rst", "README.txt"]
    for filename in readme_files:
        if os.path.exists(filename):
            with open(filename, encoding="utf-8") as readme_handle:
                return readme_handle.read()
    return "A FastAPI application with AgentScope runtime"


# Read configuration
config = read_config()

# Get configuration values
setup_package_name = config.get("SETUP_PACKAGE_NAME", "deploy_starter")
setup_module_name = config.get("SETUP_MODULE_NAME", "main")
setup_function_name = config.get("SETUP_FUNCTION_NAME", "run_app")
setup_command_name = config.get("SETUP_COMMAND_NAME", "MCP-Server-starter")

# Generate package name with UUID
base_name = config.get("SETUP_NAME", "MCP-Server-starter")
unique_name = f"{base_name}-{uuid.uuid4().hex[:8]}"

# Create package structure
setup(
    name=unique_name,
    version=config.get("SETUP_VERSION", "0.1.0"),
    description=config.get("SETUP_DESCRIPTION", "MCP-Server-starter"),
    long_description=config.get(
        "SETUP_LONG_DESCRIPTION",
        (
            "MCP-Server-starter services, supporting both direct execution "
            "and uvicorn deployment"
        ),
    ),
    packages=[setup_package_name],
    package_dir={setup_package_name: setup_package_name},
    install_requires=requirements,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            (
                f"{setup_command_name}={setup_package_name}."
                f"{setup_module_name}:{setup_function_name}"
            ),
        ],
    },
    include_package_data=True,
    package_data={
        setup_package_name: ["config.yml"],
    },
)
