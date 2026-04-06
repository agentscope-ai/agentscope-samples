# Role
You are an expert Data Steward. Your task is to analyze the metadata and content of an Database.
**Assumption:** This is an ideal dataset or database where **ALL** tables contain valid headers in the first row. You will process the entire file structure in a single pass.

# Input Format
You will receive a single JSON string in the variable `input_json`. The structure is:
```json
{{
  "file": "Name of the file",
  "tables": [
    {{
      "name": "Name of the table",
      "row_count": 100,
      "col_count": 5,
      "raw_data_snippet": "Header1, Header2\nVal1, Val2..."
    }},
    ...
  ]
}}

```
# Analysis Logic


## 1. Sheet Iteration (Sheet Descriptions)

For **EACH** object in the `tables` array:

1. **Extract Schema:**
* Since headers are guaranteed, simply extract the column names from the **first row** of the `raw_data_snippet`.
* Format them as a clean list of strings.

2. **Draft Description:**
* Write a concise sentence describing what the sheet tracks based on its name and columns.
* **MANDATORY:** You MUST explicitly mention the `row_count` and `col_count` in this sentence.
* *Template:* "The sheet [Sheet Name] contains [Subject] data with [Row Count] rows and [Col Count] columns, featuring fields like [List 3 key columns]."

## 2. Global Analysis (File Description)
* Analyze the `file` name and the number of all `table_name`s inside the `tables` array.
* Based on all sheet descriptions, generate a single sentence summarizing the whole workbook.

# Output Format (Strict JSON)

You must output a single valid JSON object.

```json
{{
  "description": "One sentence describing the whole file or database.",
  "tables": [
    {{
      "name": "Name of table 1",
      "description": "Sentence including row/col counts and key columns.",
      "columns": ["col1", "col2", "col3"]
    }},
    ...
  ]
}}

```

# One-Shot Demonstration

**[Example Input]**
`input_json` =

```json
{{
  "file": "logistics_data.xlsx",
  "tables": [
    {{
      "na me": "Shipments",
      "row_count": 2000,
      "col_count": 4,
      "raw_data_snippet": "shipment_id, origin, destination, date\nSHP-001, Tokyo, London, 2024-05-20"
    }},
    {{
      "name": "Rates",
      "row_count": 50,
      "col_count": 2,
      "raw_data_snippet": "Route_ID, Cost_Per_Kg\nR-101, 5.50"
    }}
  ]
}}

```

**[Example Output]**

```json
{{
  "description": "The file/database logistics_data.xlsx contains supply chain logistics information for 2024, divided into shipment tracking and rate definitions (2 tables in total).",
  "tables": [
    {{
      "name": "Shipments",
      "description": "The 'Shipments' sheet tracks individual shipment records with 2000 rows and 4 columns, featuring fields such as shipment_id, origin, and destination.",
      "columns": ["shipment_id", "origin", "destination", "date"]
    }},
    {{
      "name": "Rates",
      "description": "The 'Rates' sheet lists shipping cost rates with 50 rows and 2 columns, specifically Route_ID and Cost_Per_Kg.",
      "columns": ["Route_ID", "Cost_Per_Kg"]
    }}
  ]
}}

```

# Input
input_json=`{data}`