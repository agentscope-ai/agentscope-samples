# -*- coding: utf-8 -*-
# pylint: disable=R1702,R0912,R0915

import os
import json
from abc import ABC, abstractmethod
from typing import Any, Dict

from loguru import logger
import pandas as pd
from sqlalchemy import inspect, text, create_engine
from agentscope.message import Msg

from alias.agent.agents.data_source._typing import SourceType
from alias.agent.agents.ds_agent_utils import (
    get_prompt_from_file,
)
from alias.agent.utils.llm_call_manager import (
    LLMCallManager,
)


class BaseDataProfiler(ABC):
    """Abstract base class for data profilers that analyze different data
    sources like csv, excel, db, etc.
    """

    _PROFILE_PROMPT_BASE_PATH = os.path.join(
        os.path.dirname(__file__),
        "built_in_prompt",
    )

    def __init__(
        self,
        path: str,
        source_type: SourceType,
        llm_call_manager: LLMCallManager,
    ):
        """Initialize the data profiler with data path, type and LLM manager.

        Args:
            path: Path to the data source file or connection string
            source_type: Enum indicating the type of data source
            llm_call_manager: Manager for handling LLM calls
        """
        self.path = path
        self.file_name = os.path.basename(path)
        self.source_type = source_type
        self.llm_call_manager = llm_call_manager

        self.source_types_2_prompts = {
            SourceType.CSV: "_profile_csv_prompt.md",
            SourceType.EXCEL: "_profile_xlsx_prompt.md",
            SourceType.IMAGE: "_profile_image_prompt.md",
            SourceType.RELATIONAL_DB: "_profile_relationdb_prompt.md",
            "IRREGULAR": "_profile_irregular_xlsx_prompt.md",
        }
        if source_type not in self.source_types_2_prompts:
            raise ValueError(f"Unsupported source type: {source_type}")
        self.prompt = self._load_prompt(source_type)

        base_model_name = self.llm_call_manager.get_base_model_name()
        vl_model_name = self.llm_call_manager.get_vl_model_name()

        self.source_types_2_models = {
            SourceType.CSV: base_model_name,
            SourceType.EXCEL: base_model_name,
            SourceType.IMAGE: vl_model_name,
            SourceType.RELATIONAL_DB: base_model_name,
        }
        self.model_name = self.source_types_2_models[source_type]

    def _load_prompt(self, source_type: Any = None):
        """Load the appropriate prompt template based on the source type.

        Args:
            source_type: Type of data source (CSV, EXCEL, IMAGE, etc.)

        Returns:
            Loaded prompt template as string
        """
        prompt_file_name = self.source_types_2_prompts[source_type]
        prompt = get_prompt_from_file(
            os.path.join(
                self._PROFILE_PROMPT_BASE_PATH,
                prompt_file_name,
            ),
            False,
        )
        return prompt

    async def generate_profile(self) -> Dict[str, Any]:
        """Generate a complete data profile
        by reading data, generating content,
        calling the LLM, and wrapping the response.

        Returns:
            Dictionary containing the complete data profile
        """
        try:
            self.data = await self._read_data()
            # different source types have different data building methods
            content = self._build_content_with_prompt_and_data(
                self.prompt,
                self.data,
            )
            # content = self.prompt.format(data=self.data)
            res = await self._generate_profile_by_llm(content)
            self.profile = self._wrap_data_response(res)
        except Exception as e:
            logger.warning(f"Error generating profile: {e}")
            self.profile = {}
        return self.profile

    @staticmethod
    def tool_clean_json(raw_response: str):
        """Clean and parse JSON response from LLM by removing markdown
        markers.

        Args:
            raw_response: Raw string response from LLM

        Returns:
            Parsed JSON object from the cleaned response
        """
        cleaned_response = raw_response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[len("```json") :].lstrip()
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[len("```") :].lstrip()
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3].rstrip()
        return json.loads(cleaned_response)

    @abstractmethod
    def _build_content_with_prompt_and_data(
        self,
        prompt: str,
        data: Any,
    ) -> str:
        """Abstract method to build content for LLM based on prompt
        and data.

        This method should be implemented by subclasses to format
        content appropriately for different data types.

        Args:
            prompt: Prompt template to use
            data: Processed data to include in the prompt

        Returns:
            Formatted content for LLM call
        """

    @abstractmethod
    async def _read_data(self):
        """Abstract method to read and process data from the source path.

        This method should be implemented by subclasses to handle
        specific
        data source types (CSV, Excel, DB, etc.).

        Returns:
            Processed data in appropriate format for the data type
        """

    async def _generate_profile_by_llm(
        self,
        content: Any,
    ) -> Dict[str, Any]:
        """Generate profile by calling LLM with prepared content.

        Args:
            content: Content to send to the LLM (text or multimodal)

        Returns:
            Dictionary response parsed from LLM output
        """
        sys_prompt = "You are a helpful AI assistant for database management."
        msgs = [
            Msg("system", sys_prompt, "system"),
            Msg("user", content, "user"),
        ]
        response = await self.llm_call_manager(
            model_name=self.model_name,
            messages=msgs,
        )
        response = BaseDataProfiler.tool_clean_json(response)
        return response

    @abstractmethod
    def _wrap_data_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Abstract method to combine LLM response with original schema.

        This method should be implemented by subclasses to properly
        merge
        LLM-generated descriptions with original data structure.

        Args:
            response: Dictionary response from LLM

        Returns:
            Combined dictionary with original schema and LLM response
        """


class StructuredDataProfiler(BaseDataProfiler):
    """Base class for profilers that work with structured data sources
    like CSV, Excel, and relational databases.
    """

    @staticmethod
    def is_irregular(cols: list[str]):
        """Determine if a table has irregular column names (many unnamed).

        Args:
            cols: List of column names from the dataset

        Returns:
            Boolean indicating whether the dataset is irregular
        """
        # any(col.startswith('Unnamed') for col in df.columns.astype(str))?
        unnamed_columns_ratio = sum(
            col.startswith("Unnamed") for col in cols.astype(str)
        ) / len(cols)
        return unnamed_columns_ratio >= 0.5

    @staticmethod
    def _extract_schema_from_table(df: pd.DataFrame, df_name: str) -> dict:
        """Analyzes a single DataFrame to extract metadata and samples.

        Extracts column names, data types, and sample values to provide a
        comprehensive view of the table structure for the LLM.

        Args:
            df: The dataframe to analyze
            df_name: Name of the table (or sheet/filename)

        Returns:
            Dictionary containing schema metadata for the table
        """
        col_list = []
        for col in df.columns:
            dtype_name = str(df[col].dtype).upper()
            # Get random samples to help LLM understand the data content
            # sample(frac=1): shuffle the data
            # head(n_samples): get the first n_samples,
            # if less than n_samples, retrieved here without any errors.
            candidates = (
                df[col]
                .drop_duplicates()
                .sample(frac=1, random_state=42)
                .head(5)
                .astype(str)
                .tolist()
            )
            # Limit the size not to exceed 1000 characters.
            # TODO: dynamic size control? 1000 is too small?
            samples = []
            length = 0
            for s in candidates:
                if (length := length + len(s)) <= 1000:
                    samples.append(s)
            col_list.append(
                {
                    "column name": col,
                    "data type": dtype_name,
                    "data samples": samples,
                },
            )
        # Create a CSV snippet of the first few rows
        raw_data_snippet = df.head(5).to_csv(index=True)

        table_schema = {
            "name": df_name,
            "raw_data_snippet": raw_data_snippet,
            # Note: Row count logic might need optimization for large files
            # TODO: how to get the row count more efficiently, openpyxl.
            "row_count": len(df) if len(df) < 100 else None,
            "col_count": len(df.columns),
            "columns": col_list,
        }
        return table_schema

    def _build_content_with_prompt_and_data(
        self,
        prompt: str,
        data: Any,
    ) -> str:
        """Format the prompt with data for structured data sources.

        Args:
            prompt: Template prompt string
            data: Processed data structure

        Returns:
            Formatted content string ready for LLM
        """
        return prompt.format(data=data)

    def _wrap_data_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Merges the original schema with the LLM-generated response.

        Combines the structural information from the original data with
        semantic descriptions generated by the LLM.

        Args:
            response: Dictionary response from LLM with descriptions

        Returns:
            Combined schema with both structural and semantic info
        """
        new_schema = {}
        new_schema["name"] = self.data["name"]
        new_schema["description"] = response["description"]
        #  # For flat files like CSV, they contain columns
        if "columns" in self.data:
            new_schema["columns"] = self.data["columns"]
        # # For multi-table sources like Excel/Database,
        # they contain tables. Each table contains columns and description
        if "tables" in self.data and "tables" in response:
            new_schema["tables"] = []
            # Build a map for response tables and descriptions
            res_des_map = {
                table["name"]: table["description"]
                for table in response["tables"]
            }
            for table in self.data["tables"]:
                table_name = table["name"]
                if table_name not in res_des_map:
                    continue
                new_table = {}
                new_table["name"] = table_name
                # Retain the desrciption from the LLM response
                new_table["description"] = res_des_map[table_name]
                if "columns" in table:
                    new_table["columns"] = table["columns"]
                if "irregular_judgment" in table:
                    new_table["irregular_judgment"] = table[
                        "irregular_judgment"
                    ]
                new_schema["tables"].append(new_table)
        return new_schema


class ExcelProfiler(StructuredDataProfiler):
    async def _extract_irregular_table(
        self,
        path: str,
        raw_data_snippet: str,
        sheet_name: str,
    ):
        """Extract structure from irregular Excel sheets with unnamed
        columns. Uses a special LLM call to identify the actual data in
        sheets with headers or other content above the main data table.

        Args:
            path: Path to the Excel file
            raw_data_snippet: Raw text snippet of the sheet content
            sheet_name: Name of the sheet being processed

        Returns:
            Schema dictionary for the irregular table structure
        """
        prompt = self._load_prompt("IRREGULAR")
        content = prompt.format(raw_snippet_data=raw_data_snippet)
        res = await self._generate_profile_by_llm(content=content)

        if "is_extractable_table" in res and res["is_extractable_table"]:
            logger.debug(res["reasoning"])
            skiprows = res["row_start_index"] + 1
            cols_range = res["col_ranges"]
            df = pd.read_excel(
                path,
                sheet_name=sheet_name,
                nrows=100,
                skiprows=skiprows,
                usecols=range(cols_range[0], cols_range[1] + 1),
            ).convert_dtypes()
            if StructuredDataProfiler.is_irregular(df.columns):
                schema = {
                    "name": sheet_name,
                    "raw_data_snippet": raw_data_snippet,
                    "irregular_judgment": "UNSTRUCTURED",
                }
            else:
                schema = self._extract_schema_from_table(df, sheet_name)
                schema["irregular_judgment"] = res
        else:
            schema = {
                "name": sheet_name,
                "raw_data_snippet": raw_data_snippet,
                "irregular_judgment": "UNSTRUCTURED",
            }

        return schema

    async def _read_data(self):
        """Read and process Excel file data including all sheets.

        Handles both regular and irregular Excel files by using pandas
        for regular files and openpyxl for files with unnamed columns.

        Returns:
            Dictionary containing metadata for all sheets in the Excel file
        """
        excel_file = pd.ExcelFile(self.path)
        table_schemas = []
        schema = {}
        schema["name"] = self.file_name
        for sheet_name in excel_file.sheet_names:
            # TODO: use openpyxl to read excel to avoid irregular excel.
            # Read a subset of each sheet
            df = pd.read_excel(
                self.path,
                sheet_name=sheet_name,
                nrows=100,
            ).convert_dtypes()
            if not StructuredDataProfiler.is_irregular(df.columns):
                table_schema = (
                    StructuredDataProfiler._extract_schema_from_table(
                        df,
                        sheet_name,
                    )
                )
            else:
                # if unnamed columns, use openpyxl to extract top 100 rows.
                import openpyxl

                wb = openpyxl.load_workbook(
                    self.path,
                    read_only=True,
                    data_only=True,
                )
                ws = wb[sheet_name]
                rows_data = []
                for i, row in enumerate(
                    ws.iter_rows(values_only=True),
                    start=1,
                ):
                    if i > 100:
                        break
                    rows_data.append(
                        ",".join(
                            "" if cell is None else str(cell) for cell in row
                        ),
                    )
                wb.close()
                raw_data_snippet = "\n".join(rows_data)

                table_schema = await self._extract_irregular_table(
                    self.path,
                    raw_data_snippet,
                    sheet_name,
                )
                # table_schema = {
                #     "name": sheet_name,
                #     "raw_data_snippet":  "\n".join(rows_data),
                # }
            table_schemas.append(table_schema)
        schema["tables"] = table_schemas
        return schema


class RelationalDatabaseProfiler(StructuredDataProfiler):
    async def _read_data(self):
        """
        Extracts metadata (schema) for all tables in a relational db.

        path (str): The Database Source Name (connection string).
        eg. postgresql://user:passward@ip:port/db_name

        Returns:
            Dictionary containing database metadata for all tables
        """
        options = {
            "isolation_level": "AUTOCOMMIT",
            # Test conns before use (handles MySQL 8hr timeout, network drops)
            "pool_pre_ping": True,
            # Keep minimal conns (MCP typically handles 1 request at a time)
            "pool_size": 1,
            # Allow temporary burst capacity for edge cases
            "max_overflow": 2,
            # Force refresh conns older than 1hr (under MySQL's 8hr default)
            "pool_recycle": 3600,
        }
        engine = create_engine(self.path, **options)
        try:
            connection = engine.connect()
        except Exception as e:
            logger.error(f"Connection to {self.path} failed: {e}")
            raise ConnectionError(f"Failed to connect to database: {e}") from e

        # Use DSN as the db identifier (can parsed cleaner)
        database_name = self.path
        inspector = inspect(connection)
        table_names = inspector.get_table_names()

        tables_data = []
        for table_name in table_names:
            try:
                # 1. Get column information
                columns = inspector.get_columns(table_name)
                col_count = len(columns)

                # 2. Get row count
                row_count_result = connection.execute(
                    text(f"SELECT COUNT(*) FROM {table_name}"),
                ).fetchone()
                row_count = row_count_result[0] if row_count_result else 0

                # 3. Get raw data snippet (first 5 rows)
                raw_data_snippet = ""
                try:
                    result = connection.execute(
                        text(f"SELECT * FROM {table_name} LIMIT 5"),
                    )
                    rows = result.fetchall()
                    if rows:
                        column_names = [col["name"] for col in columns]
                        lines = []
                        # Add header
                        lines.append(", ".join(column_names))
                        # Add data rows
                        for row in rows:
                            row_values = []
                            for value in row:
                                if value is None:
                                    row_values.append("NULL")
                                else:
                                    # Escape commas and newlines
                                    val_str = str(value)
                                    if "," in val_str or "\n" in val_str:
                                        val_str = f'"{val_str}"'
                                    row_values.append(val_str)
                            lines.append(", ".join(row_values))
                        raw_data_snippet = "\n".join(lines)
                except Exception as e:
                    logger.warning(
                        f"Error fetching {table_name} data: {str(e)}",
                    )
                    raw_data_snippet = None
                # 4. detailed column info (types and samples)
                column_details = []
                if rows:
                    for i, col in enumerate(columns):
                        col_name = col["name"]
                        col_type = str(col["type"])
                        # Extract samples for this column from the fetched rows
                        sample_values = []
                        for row in rows:
                            if i < len(row):
                                val = row[i]
                                sample_values.append(
                                    str(val) if val is not None else "NULL",
                                )

                        column_details.append(
                            {
                                "column name": col_name,
                                "data type": col_type,
                                "data sample": sample_values[:3],
                            },
                        )

                table_info = {
                    "name": table_name,
                    "row_count": row_count,
                    "col_count": col_count,
                    "raw_data_snippet": raw_data_snippet,
                    "columns": column_details,
                }

                tables_data.append(table_info)

            except Exception as e:
                # If one table fails, log it and continue to the next
                logger.warning(f"Error processing {table_name}: {str(e)}")
                continue
        # Contruct the final schema
        schema = {
            "name": database_name,
            "tables": tables_data,
        }
        self.data = schema
        return schema


class CsvProfiler(ExcelProfiler):
    async def _read_data(self):
        """Handles schema extraction for CSV as single-table sources.

        Uses Polars for efficient row counting on large files and
        pandas for detailed schema analysis of the first 100 rows.

        Returns:
            Schema dictionary for the CSV file
        """
        import polars as pl

        # Use Polars for efficient row counting on large files
        df = pl.scan_csv(self.path, ignore_errors=True)
        row_count = df.select(pl.len()).collect().item()
        # Read a subset with Pandas for detailed schema analysis
        df = pd.read_csv(self.path, nrows=100).convert_dtypes()
        schema = self._extract_schema_from_table(df, self.file_name)
        schema["row_count"] = row_count
        # if StructuredDataProfiler.is_irregular(df.columns):
        #   self._extract_irregular_table(...)
        return schema


class ImageProfiler(BaseDataProfiler):
    """Profiler for image data sources that uses multimodal LLMs."""

    async def _read_data(self):
        """
        For images, this simply returns the path since the LLM API
        handles loading the image directly.

        Returns:
            Path to the image file
        """
        return self.path

    def _build_content_with_prompt_and_data(self, prompt, data):
        """build multimodal content for image analysis.

        Creates content in the format required by multimodal LLM APIs
        with both image and text components.

        Args:
            prompt: Text prompt template for image analysis
            data: Path to the image file

        Returns:
            List containing image and text components for the LLM call
        """
        # Convert image paths according to the model requirements
        contents = [
            {
                "text": prompt,
                "type": "text",
            },
            {
                "source": {
                    "url": data,
                    "type": "url",
                },
                "type": "image",
            },
        ]
        return contents

    def _wrap_data_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Format the LLM response for image data into dict.

        Args:
            response: Dictionary response from multimodal LLM

        Returns:
            Profile dictionary with image name, description and details
        """
        profile = {
            "name": self.file_name,
            "description": response["description"],
            "details": response["details"],
        }
        return profile


class DataProfilerFactory:
    """Factory class to create appropriate data profiler instances based
    on source type.
    """

    @staticmethod
    def get_profiler(
        llm_call_manager: LLMCallManager,
        path: str,
        source_type: SourceType,
    ) -> BaseDataProfiler:
        """Factory method to get the appropriate profiler instance.
        Generate the correct profile result for the source.

        Args:
            path: Path to the data source or connection string
            source_type: Enum indicating the type of data source
            llm_call_manager: Manager for handling LLM calls

        Returns:
            Instance of the appropriate profiler subclass

        Raises:
            ValueError: If the source_type is unsupported
        """
        if source_type == SourceType.IMAGE:
            return ImageProfiler(
                path=path,
                source_type=source_type,
                llm_call_manager=llm_call_manager,
            )
        elif source_type == SourceType.CSV:
            return CsvProfiler(
                path=path,
                source_type=source_type,
                llm_call_manager=llm_call_manager,
            )
        elif source_type == SourceType.EXCEL:
            return ExcelProfiler(
                path=path,
                source_type=source_type,
                llm_call_manager=llm_call_manager,
            )
        elif source_type == SourceType.RELATIONAL_DB:
            return RelationalDatabaseProfiler(
                path=path,
                source_type=source_type,
                llm_call_manager=llm_call_manager,
            )
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
