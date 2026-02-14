# -*- coding: utf-8 -*-
"""Configuration management for Local Deep Research API.

This module loads configuration from:
1. Environment variables (.env file)
2. YAML configuration file (config.yaml)
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


# Find project root directory
def find_project_root() -> Path:
    """Find the project root directory containing config.yaml.

    Returns:
        Path: Project root directory.
    """
    current = Path(__file__).resolve().parent  # api/

    # Try to find config.yaml by going up directories
    for _ in range(3):  # Search up to 3 levels
        config_path = current.parent / "config.yaml"
        if config_path.exists():
            return current.parent
        current = current.parent

    # Fallback to cwd
    return Path.cwd()


# Project root
PROJECT_ROOT = find_project_root()

# Load environment variables from .env file (search in project root and cwd)
env_paths = [
    PROJECT_ROOT / ".env",
    Path.cwd() / ".env",
    Path(__file__).parent.parent / ".env",
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break
else:
    # Try default load_dotenv() which searches cwd
    load_dotenv()


class LLMConfig(BaseModel):
    """LLM configuration."""

    provider: str = Field(..., description="LLM provider name")
    model: str = Field(..., description="Model name")
    base_url: Optional[str] = Field(None, description="API base URL")
    api_key: Optional[str] = Field(None, description="API key")
    enable_thinking: bool = Field(False, description="Enable thinking mode")


class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""

    provider: str = Field(..., description="Embedding provider name")
    model: str = Field(..., description="Model name")
    base_url: Optional[str] = Field(None, description="API base URL")
    api_key: Optional[str] = Field(None, description="API key")


class VectorDBConfig(BaseModel):
    """Vector database configuration."""

    provider: str = Field(..., description="Vector DB provider name")
    default_collection: str = Field("deepsearcher", description="Default collection name")
    uri: str = Field(..., description="Database URI")
    token: Optional[str] = Field(None, description="Authentication token")
    db: str = Field("default", description="Database name")
    hybrid: bool = Field(False, description="Enable hybrid search")


class AgentConfig(BaseModel):
    """Agent configuration."""

    max_iters: int = Field(30, description="Maximum iterations")
    max_depth: int = Field(3, description="Maximum search depth")


class LoadSettings(BaseModel):
    """Document loading settings."""

    chunk_size: int = Field(1500, description="Chunk size for splitting")
    chunk_overlap: int = Field(100, description="Chunk overlap")


class Settings(BaseModel):
    """Application settings."""

    # API Settings
    api_host: str = Field("0.0.0.0", description="API host")
    api_port: int = Field(8000, description="API port")
    api_reload: bool = Field(True, description="Enable auto-reload")

    # Component Configurations
    llm: LLMConfig
    embedding: EmbeddingConfig
    vector_db: VectorDBConfig
    agent: AgentConfig
    load_settings: LoadSettings

    # Working directories
    tmp_file_storage_dir: str = Field("./tmp", description="Temporary file storage directory")
    upload_dir: str = Field("./uploads", description="Upload directory")

    class Config:
        """Pydantic config."""

        env_prefix = "APP_"


def load_config_from_yaml(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_path (str): Path to YAML config file.

    Returns:
        Dict[str, Any]: Configuration dictionary.
    """
    # Try to find config.yaml in multiple locations
    possible_paths = [
        Path(config_path),  # Absolute path if provided
        PROJECT_ROOT / config_path,  # Project root
        Path.cwd() / config_path,  # Current working directory
        Path(__file__).parent.parent / config_path,  # local_deep_research/
    ]

    for path in possible_paths:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
                print(f"✓ Loaded config from: {path}")
                return config

    raise FileNotFoundError(
        f"Config file not found. Searched in:\n" + "\n".join(f"  - {p}" for p in possible_paths)
    )


def merge_config_with_env(yaml_config: Dict[str, Any]) -> Dict[str, Any]:
    """Merge YAML config with environment variables.

    Environment variables take precedence over YAML config.

    Args:
        yaml_config (Dict[str, Any]): Configuration from YAML.

    Returns:
        Dict[str, Any]: Merged configuration.
    """
    # API keys from environment variables
    if "provide_settings" in yaml_config:
        # LLM
        if "llm" in yaml_config["provide_settings"]:
            llm_config = yaml_config["provide_settings"]["llm"]["config"]
            llm_config["api_key"] = os.getenv("DASHSCOPE_API_KEY", llm_config.get("api_key"))

        # Embedding
        if "embedding" in yaml_config["provide_settings"]:
            embed_config = yaml_config["provide_settings"]["embedding"]["config"]
            embed_config["api_key"] = os.getenv("SILICONFLOW_API_KEY", embed_config.get("api_key"))

    return yaml_config


def create_settings() -> Settings:
    """Create application settings by loading and merging configurations.

    Returns:
        Settings: Application settings object.
    """
    # Load YAML configuration
    yaml_config = load_config_from_yaml()

    # Merge with environment variables
    yaml_config = merge_config_with_env(yaml_config)

    # Extract provide_settings
    provide_settings = yaml_config.get("provide_settings", {})
    query_settings = yaml_config.get("query_settings", {})
    load_settings = yaml_config.get("load_settings", {})

    # Build settings dict
    settings_dict = {
        # API settings from env
        "api_host": os.getenv("API_HOST", "0.0.0.0"),
        "api_port": int(os.getenv("API_PORT", "8000")),
        "api_reload": os.getenv("API_RELOAD", "true").lower() == "true",
        # LLM config
        "llm": LLMConfig(
            provider=provide_settings["llm"]["provider"],
            model=provide_settings["llm"]["config"]["model"],
            base_url=provide_settings["llm"]["config"].get("base_url"),
            api_key=provide_settings["llm"]["config"].get("api_key"),
            enable_thinking=provide_settings["llm"]["config"].get("enable_thinking", False),
        ),
        # Embedding config
        "embedding": EmbeddingConfig(
            provider=provide_settings["embedding"]["provider"],
            model=provide_settings["embedding"]["config"]["model"],
            base_url=provide_settings["embedding"]["config"].get("base_url"),
            api_key=provide_settings["embedding"]["config"].get("api_key"),
        ),
        # Vector DB config
        "vector_db": VectorDBConfig(
            provider=provide_settings["vector_db"]["provider"],
            default_collection=provide_settings["vector_db"]["config"].get(
                "default_collection", "deepsearcher"
            ),
            uri=provide_settings["vector_db"]["config"]["uri"],
            token=provide_settings["vector_db"]["config"].get("token"),
            db=provide_settings["vector_db"]["config"].get("db", "default"),
            hybrid=provide_settings["vector_db"]["config"].get("hybrid", False),
        ),
        # Agent config
        "agent": AgentConfig(
            max_iters=query_settings.get("max_iter", 30),
            max_depth=query_settings.get("max_depth", 3),
        ),
        # Load settings
        "load_settings": LoadSettings(
            chunk_size=load_settings.get("chunk_size", 1500),
            chunk_overlap=load_settings.get("chunk_overlap", 100),
        ),
        # Directories (relative to project root)
        "tmp_file_storage_dir": os.getenv(
            "TMP_FILE_STORAGE_DIR", str(PROJECT_ROOT / "tmp")
        ),
        "upload_dir": os.getenv("UPLOAD_DIR", str(PROJECT_ROOT / "uploads")),
    }

    return Settings(**settings_dict)


# Global settings instance
settings = create_settings()

# Create necessary directories
os.makedirs(settings.tmp_file_storage_dir, exist_ok=True)
os.makedirs(settings.upload_dir, exist_ok=True)

# Print configuration info
print(f"✓ Project root: {PROJECT_ROOT}")
print(f"✓ Temp directory: {settings.tmp_file_storage_dir}")
print(f"✓ Upload directory: {settings.upload_dir}")
