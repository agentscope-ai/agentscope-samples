# -*- coding: utf-8 -*-
# pylint: disable=R1702,R0912,R0911

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml
from loguru import logger

from agentscope.mcp import StdIOStatefulClient
from agentscope_runtime.sandbox.box.sandbox import Sandbox

from alias.agent.agents.data_source.data_skill import DataSkillManager
from alias.agent.agents.data_source._typing import (
    SOURCE_TYPE_TO_ACCESS_TYPE,
    SourceAccessType,
    SourceType,
)
from alias.agent.agents.data_source.data_profile import data_profile
from alias.agent.agents.data_source.utils import replace_placeholders
from alias.agent.tools.toolkit_hooks.text_post_hook import TextPostHook
from alias.agent.tools.alias_toolkit import AliasToolkit
from alias.agent.tools.sandbox_util import (
    copy_local_file_to_workspace,
)
from alias.agent.utils.llm_call_manager import (
    LLMCallManager,
)


class DataSource:
    """
    Unified data source class representing any data source.
    """

    def __init__(
        self,
        endpoint: str,
        source_type: SourceType,
        name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a data source.

        Args:
            source_access_type: Type of the data source access \
                (SourceAccessType enum)
            source_type: Type of the data source (SourceType enum)
            name: Name/identifier of the data source
            endpoint: Address/DNS/URL/path to access the data source
            description: Optional description of the data source
            config: Configuration for this data source
        """

        self.endpoint = endpoint
        self.name = name

        source_access_type = SOURCE_TYPE_TO_ACCESS_TYPE.get(
            source_type,
            SourceAccessType.DIRECT,
        )

        self.source_access_type = source_access_type
        self.source_type = source_type

        self.config = config or {}
        self.profile = {}
        self.source_desc = None
        self.source_access_desc = None

    async def prepare(self, toolkit: AliasToolkit):
        """
        Prepare data source.
        For LOCAL_FILE: Upload file to sandbox workspace
        For MCP_TOOL: Register corresponding MCP server

        Args:
            sandbox: Sandbox instance
        """

        logger.info(f"Preparing data source {self.name}...")

        if self.source_access_type == SourceAccessType.DIRECT:
            # Get the filename and construct target path in workspace
            filename = os.path.basename(self.endpoint)
            target_path = f"/workspace/{filename}"

            if os.getenv("LINK_FILE_TO_WORKSPACE", "off").lower() == "on":
                logger.info(
                    f"Creating symlink for {self.endpoint} "
                    f"to {target_path}",
                )
                # Build ln -s command
                command = f"ln -s '{self.endpoint}' '{target_path}'"
                result = toolkit.sandbox.call_tool(
                    name="run_shell_command",
                    arguments={"command": command},
                )
                if result.get("isError"):
                    raise ValueError(
                        "Failed to create symlink for "
                        f"{self.endpoint}: {result}",
                    )
            else:
                logger.info(f"Uploading {self.endpoint} to {target_path}")
                result = copy_local_file_to_workspace(
                    sandbox=toolkit.sandbox,
                    local_path=self.endpoint,
                    target_path=target_path,
                )

                if result.get("isError"):
                    raise ValueError(
                        f"Failed to upload {self.endpoint}: " f"{result}",
                    )

            self.source_access = target_path
            self.source_desc = "Local file"
            self.source_access_desc = f"Access at path: `{target_path}`"

            logger.info(f"Successfully loaded to {result}")

        # Check if this is an MCP tool source
        elif self.source_access_type == SourceAccessType.VIA_MCP:
            server_config = self.config.get("mcp_server", {})
            mcp_server_name = server_config.keys()

            if len(mcp_server_name) != 1:
                raise ValueError("Register server one by one!")

            mcp_server_name = list(mcp_server_name)[0]
            server_config = server_config[mcp_server_name]

            cmd = server_config.get("command")
            args = server_config.get("args")
            if cmd is None or args is None:
                raise ValueError(
                    "MCP server configuration requires non-empty "
                    "`command` and `args` fields to start!",
                )

            client = StdIOStatefulClient(
                self.name,
                command=cmd,
                args=args,
                env=server_config.get("env"),
            )

            text_hook = TextPostHook(
                toolkit.sandbox,
                budget=5000,
                auto_save=True,
            )
            await toolkit.add_and_connect_mcp_client(
                client,
                postprocess_func=text_hook.truncate_and_save_response,
            )
            registered_tools = [
                t.name
                for t in list(
                    await toolkit.additional_mcp_clients[-1].list_tools(),
                )
            ]

            self.source_access = self.endpoint
            self.source_desc = f"{self.source_type}"
            self.source_access_desc = (
                f"Access via MCP tools: [{', '.join(registered_tools)}]"
            )

            logger.info(f"Successfully connected to {self.name}")

        else:
            logger.info(
                f"Skipping preparation for source type: {self.source_type}",
            )

    def get_coarse_desc(self):
        return (
            f"{self.source_desc}. {self.source_access_desc}: "
            + f"{self._general_profile()}"
        )

    async def prepare_profile(
        self,
        sandbox: Sandbox,
        llm_call_manager: LLMCallManager,
    ) -> Optional[Dict[str, Any]]:
        """Run type-specific profiling."""
        if llm_call_manager and not self.profile:
            try:
                self.profile = await data_profile(
                    sandbox=sandbox,
                    sandbox_path=self.source_access,
                    source_type=self.source_type,
                    llm_call_manager=llm_call_manager,
                )
                logger.info(
                    "Profiling successfully: "
                    + f"{self._general_profile()[:100]}...",
                )
            except ValueError as e:
                self.profile = None
                logger.warning(f"Warning when profile data: {e}")
            except Exception as e:
                self.profile = None
                logger.error(f"Error when profile data: {e}")

        return self.profile

    def _refined_profile(self) -> str:
        if self.profile:
            return yaml.dump(
                self.profile,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False
                if self.source_type == SourceType.IMAGE
                else None,
                width=float("inf"),
            )
        else:
            return ""

    def _general_profile(self) -> str:
        return self.profile["description"] if self.profile else ""

    def __str__(self) -> str:
        return (
            f"DataSource(name='{self.name}', type='{self.source_type}', "
            f"endpoint='{self.endpoint}')"
        )

    def __repr__(self) -> str:
        return self.__str__()


class DataSourceManager:
    """
    Manager class for handling multiple data sources.
    Provides methods to add, retrieve, and manage data sources.
    Also manages data source configurations with hierarchical lookup.
    """

    _default_data_source_config = os.path.join(
        Path(__file__).resolve().parent,
        "_default_config.json",
    )

    def __init__(
        self,
        sandbox: Sandbox,
        llm_call_manager: LLMCallManager,
    ):
        """Initialize an empty data source manager."""
        self._data_sources: Dict[str, DataSource] = {}
        self._type_defaults = {}

        self._load_default_config()

        self.skill_manager = DataSkillManager()
        self.selected_skills = None

        self.toolkit = AliasToolkit(sandbox=sandbox)

        self.llm_call_manager = llm_call_manager

    def add_data_source(
        self,
        config: str | Dict = None,
    ):
        """
        Add a new data source (or multiple sources) to the manager.

        Args:
            config: endpoint(Address/DNS/URL/path to the data source) or
                    configuration for data source conection
        """

        if isinstance(config, str):
            endpoint = config
            conn_config = None
        else:
            if "endpoint" not in config:
                logger.error(
                    f"Missing 'endpoint' in config for source '{config}'",
                )

            endpoint = config["endpoint"]
            conn_config = config

        sources = set()
        if os.path.isdir(endpoint):
            # Add all files in directory
            for filename in os.listdir(endpoint):
                file_path = os.path.join(endpoint, filename)
                sources.add(file_path)
        else:
            sources.add(endpoint)

        for endpoint in sources:
            # Auto-detect source type
            source_type = self._detect_source_type(endpoint)

            # Auto-generate name
            name = self._generate_name(endpoint)

            # Get configuration for this data source
            if not conn_config:
                conn_config = self.get_default_config(source_type)

            if conn_config:
                conn_config = replace_placeholders(
                    conn_config,
                    {
                        "endpoint": endpoint,
                    },
                )

            # Create data source with configuration
            data_source = DataSource(endpoint, source_type, name, conn_config)
            self._data_sources[endpoint] = data_source

    async def prepare_data_sources(self) -> None:
        """
        Prepare all data sources.

        Args:
            sandbox: Optional sandbox instance for file uploads and startup \
                MCP servers
        """
        logger.info(f"Preparing {len(self._data_sources)} data source(s)...")

        all_data_sources = self._data_sources.values()
        for data_source in all_data_sources:
            await data_source.prepare(self.toolkit)
            await data_source.prepare_profile(
                self.toolkit.sandbox,
                self.llm_call_manager,
            )

    def _generate_name(self, endpoint: str) -> str:
        """
        Generate an name based on the endpoint.
        For databases, removes passwords and uses scheme + database name.
        For files, uses filename.
        For URLs, uses domain or last part of path.
        """
        from urllib.parse import urlparse

        try:
            # For file paths
            if os.path.isfile(endpoint):
                filename = os.path.basename(endpoint)
                # Remove extension and sanitize
                name_without_ext = os.path.splitext(filename)[0]
                return self._sanitize_name(name_without_ext)

            # For database connections
            db_indicators = [
                "://",
                ".db",
                ".sqlite",
                "mongodb://",
                "mongodb+srv://",
                "neo4j://",
                "bolt://",
            ]
            if any(
                indicator in endpoint.lower() for indicator in db_indicators
            ):
                if "://" in endpoint:
                    try:
                        # Split by :// to get scheme and rest
                        scheme, rest = endpoint.split("://", 1)
                        scheme = scheme.lower()

                        # Handle authentication (user:password@host)
                        if "@" in rest:
                            auth_part, host_part = rest.split("@", 1)
                            if ":" in auth_part:
                                # Has user:password format, keep only username
                                username = auth_part.split(":")[0]
                                rest = f"{username}@{host_part}"
                            # If no colon, it's just username@host, keep as is

                        # Extract database name
                        db_name = "unknown"
                        if "/" in rest:
                            # Split by / and take last part before
                            # query parameters
                            path_parts = rest.split("/")
                            if len(path_parts) > 1:
                                db_name = (
                                    path_parts[-1].split("?")[0].split("#")[0]
                                )
                                if not db_name:  # If empty, try second to last
                                    db_name = (
                                        path_parts[-2]
                                        if len(path_parts) > 2
                                        else "unknown"
                                    )
                        else:
                            # Use host name if no database name in path
                            host = (
                                rest.split(":")[0].split("/")[0].split("@")[-1]
                            )
                            db_name = host

                        # Create name: scheme_dbname
                        return self._sanitize_name(f"{scheme}_{db_name}")
                    except Exception as e:
                        logger.warning(
                            f"Error parsing database URL {endpoint}: {e}",
                        )
                        # Fall through to URL handling

                elif "." in endpoint:
                    # Use filename without extension for .db/.sqlite files
                    filename = os.path.basename(endpoint)
                    name_without_ext = os.path.splitext(filename)[0]
                    return self._sanitize_name(name_without_ext)

            # For URLs (including database URLs that failed to parse)
            if "://" in endpoint:
                try:
                    parsed = urlparse(endpoint)
                    if parsed.netloc:
                        # Use domain name (without port)
                        domain = parsed.netloc.split(":")[0].split("@")[
                            -1
                        ]  # Remove username if present
                        # If path exists, use last part of path
                        if parsed.path and parsed.path != "/":
                            path_parts = parsed.path.strip("/").split("/")
                            if path_parts:
                                return self._sanitize_name(path_parts[-1])
                        return self._sanitize_name(domain)
                    elif parsed.path:
                        # Use last part of path
                        path_parts = parsed.path.strip("/").split("/")
                        if path_parts:
                            return self._sanitize_name(path_parts[-1])
                except Exception as e:
                    logger.warning(f"Error parsing URL {endpoint}: {e}")

            # Fallback: use a sanitized version of the endpoint
            return self._sanitize_name(endpoint[:50])

        except Exception as e:
            logger.error(f"Error generating default name for {endpoint}: {e}")
            # Ultimate fallback
            return self._sanitize_name("unknown_source")

    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name to be used as a data source identifier."""
        import re

        # Keep only alphanumeric and underscore characters
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)

        # Ensure it starts with a letter or underscore
        if sanitized and not sanitized[0].isalpha() and sanitized[0] != "_":
            sanitized = "_" + sanitized

        # Truncate if too long
        sanitized = sanitized[:50]

        # Ensure it's not empty
        if not sanitized:
            sanitized = "unknown"

        return sanitized

    def _detect_source_type(self, endpoint: str) -> SourceType:
        """Auto-detect source type based on endpoint."""
        endpoint_lower = endpoint.lower()

        # Check for file extensions
        if endpoint_lower.endswith(".csv"):
            source_type = SourceType.CSV
        elif endpoint_lower.endswith((".xls", ".xlsx", "xlsm")):
            source_type = SourceType.EXCEL
        elif endpoint_lower.endswith(".json"):
            source_type = SourceType.JSON
        elif endpoint_lower.endswith((".txt", ".log", ".md")):
            source_type = SourceType.TEXT
        elif endpoint_lower.endswith(
            (".jpg", ".jpeg", ".png", ".gif", ".bmp"),
        ):
            source_type = SourceType.IMAGE

        # Check for database connection strings/patterns
        # Relational databases
        elif any(
            keyword in endpoint_lower
            for keyword in [
                "postgresql://",
                "postgres://",
                "pg://",
                "mysql://",
                "mariadb://",
                "sqlserver://",
            ]
        ):
            source_type = SourceType.RELATIONAL_DB
        elif (
            "sqlite://" in endpoint_lower
            or endpoint_lower.endswith(".db")
            or endpoint_lower.endswith(".sqlite")
        ):
            source_type = SourceType.RELATIONAL_DB

        else:
            source_type = SourceType.OTHER

        return source_type

    def get_all_data_sources_desc(self) -> str:
        """
        Get descriptions of all data sources.

        Returns:
            List of data source descriptions
        """
        return "Available data sources: \n" + "\n".join(
            [
                f"[{idx}] " + ds.get_coarse_desc()
                for idx, ds in enumerate(self._data_sources.values())
            ],
        )

    def get_local_data_sources(self) -> List[str]:
        """
        Get list of local data source endpoints
        """

        return [
            ds.endpoint
            for ds in self._data_sources.values()
            if ds.source_access_type == SourceAccessType.DIRECT
        ]

    def get_all_data_sources_name(self) -> List[str]:
        """
        Get a list of all data source names.

        Returns:
            List of all data source names
        """
        return list(self._data_sources.keys())

    def remove_data_source(self, name: str) -> bool:
        """
        Remove a data source by name.

        Args:
            name: Name of the data source to remove

        Returns:
            True if successfully removed, False if not found
        """
        if name in self._data_sources:
            del self._data_sources[name]
            return True
        return False

    def get_default_config(self, source_type: SourceType) -> Dict[str, Any]:
        """
        Get the default configuration for a source type.

        Args:
            source_type: The SourceType to get default config for

        Returns:
            Default configuration dictionary, empty dict if not registered
        """
        return self._type_defaults.get(source_type, {})

    def _load_default_config(self) -> None:
        """Load default type to configuration."""
        try:
            with open(
                self._default_data_source_config,
                "r",
                encoding="utf-8",
            ) as f:
                config = json.load(f)

            # Load type defaults
            for type_name, type_config in config.items():
                try:
                    source_type = SourceType(type_name)
                    self._type_defaults[source_type] = type_config
                except ValueError:
                    # Skip invalid source types
                    continue

        except FileNotFoundError:
            # If config file doesn't exist, initialize with empty configs
            pass
        except json.JSONDecodeError:
            # If config file is invalid JSON, initialize with empty configs
            pass

    def __len__(self) -> int:
        """Return the number of data sources managed."""
        return len(self._data_sources)

    def get_data_skills(self):
        # TODO: update when data source changed
        if self.selected_skills is None:
            source_types = [
                data.source_type for data in self._data_sources.values()
            ]
            self.selected_skills = self.skill_manager.load(source_types)

        return "\n".join(self.selected_skills)
