# -*- coding: utf-8 -*-

from enum import Enum


class SourceAccessType(str, Enum):
    """Simple source access type classification"""

    DIRECT = "direct"
    VIA_MCP = "via_mcp"

    def __str__(self):
        return self.value


class SourceType(str, Enum):
    """Simple source type classification"""

    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"
    TEXT = "text"
    IMAGE = "image"

    # Database sources
    RELATIONAL_DB = "relational_db"

    OTHER = "other"

    def __str__(self):
        return self.value

    @staticmethod
    def is_valid_source_type(value: str) -> bool:
        try:
            SourceType(value)
            return True
        except ValueError:
            return False


# Define mapping between SourceType and SourceAccessType
SOURCE_TYPE_TO_ACCESS_TYPE = {
    # File types -> LOCAL_FILE
    SourceType.CSV: SourceAccessType.DIRECT,
    SourceType.JSON: SourceAccessType.DIRECT,
    SourceType.EXCEL: SourceAccessType.DIRECT,
    SourceType.TEXT: SourceAccessType.DIRECT,
    SourceType.IMAGE: SourceAccessType.DIRECT,
    # Database types -> MCP_TOOL
    SourceType.RELATIONAL_DB: SourceAccessType.VIA_MCP,
    # Unknown type -> depends on endpoint
    SourceType.OTHER: None,
}
