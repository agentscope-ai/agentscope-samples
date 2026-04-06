# -*- coding: utf-8 -*-
import logging

# Set up logger
logger = logging.getLogger(__name__)


def replace_placeholders(obj, source_config):
    if isinstance(obj, str):
        import re

        pattern = r"\$\{([^}]+)\}"
        matches = re.finditer(pattern, obj)
        result = obj
        for match in matches:
            var_name = match.group(1)
            if var_name in source_config:
                result = result.replace(
                    match.group(0),
                    str(source_config[var_name]),
                )
        return result
    elif isinstance(obj, dict):
        return {
            k: replace_placeholders(v, source_config) for k, v in obj.items()
        }
    elif isinstance(obj, list):
        return [replace_placeholders(item, source_config) for item in obj]
    else:
        return obj
