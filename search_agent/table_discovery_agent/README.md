# Table Discovery Agent

List tables and columns in a local directory of CSV files or search their columns by schema information or observed values.

## Project structure

```text
table_discovery_agent/
├── README.md                # Setup and demo instructions
├── data_lake.py             # CSV discovery, schema reading, and pandas table loading
├── main.py                  # Command-line schema browser and column search
├── requirements.txt         # Pinned formatting and search dependencies
├── indexing/
│   ├── __init__.py          # Public formatter, index, and statistics APIs
│   ├── column_formatter.py  # Column metadata and content formatting
│   ├── column_index.py      # Metadata and content HNSW indexes
│   ├── sketches.py          # Column statistics and key sketches
│   └── embedding.py         # Text encoder interface and local BGE implementation
└── data/
    └── demo_lake/           # Four synthetic example tables
```

## Run the demo

Use Python 3.11. From the `table_discovery_agent` directory, create a virtual environment and activate it.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

The schema browser uses only the Python standard library.

```bash
python main.py --lake data/demo_lake
```

Expected output

```text
Found 4 tables

product_catalog: product_id, product_name, category
region_demographics: region_id, population, median_income
store_directory: store_id, store_name, region_id
store_sales: store_id, month, revenue
```

Pass the path to another local CSV directory with `--lake` to list its tables and columns.

## Search columns

The available encoder is `bge`, which is the default for `--encoder`. Pass its local Hugging Face model directory with `--embedding-model`. Install the pinned dependencies and set `BGE_MODEL_DIR` to that directory.

```bash
python -m pip install -r requirements.txt
BGE_MODEL_DIR="/path/to/local/bge-model"
```

Use the metadata channel to search by column name or type.

```bash
python main.py --lake data/demo_lake --encoder bge \
    --embedding-model "$BGE_MODEL_DIR" --search "population" --channel metadata --top-k 3
```

Use the content channel to search using a column representation with example values.

```bash
python main.py --lake data/demo_lake --embedding-model "$BGE_MODEL_DIR" \
    --search "Column: store id | Type: Categorical | Content: S01, S02" \
    --channel content --top-k 3
```

Search builds both indexes in memory for the selected lake and returns matches from the selected channel. Each result shows the table and column, the inferred column type, and the cosine similarity score. The default channel is `metadata` and the default maximum is five results.

### Text encoder interface

The CLI selects an implementation with `create_encoder(name, model_path)` in `indexing/embedding.py`. The same encoder handles metadata, content, and queries during a search run. Additional implementations must provide `encode(texts)` that accepts a sequence of strings and returns a contiguous two-dimensional NumPy array of L2-normalized `float32` vectors. Return one row per input string, in input order, with a consistent embedding dimension across calls.

## Format columns

The formatting example uses pandas and the dependencies installed above.

`data_lake.read_table(table)` loads a discovered CSV table into a pandas DataFrame. In `indexing/column_formatter.py`, the `format_columns(tables: Mapping[str, pd.DataFrame]) -> tuple[ColumnRepresentation, ...]` API accepts DataFrames keyed by table ID and returns one record per column. Each record has `table_id`, `column_name`, `column_type`, `metadata`, and `content` fields.

`metadata` describes the column using its schema information. `content` describes the observed values. The TIDE-style formatting uses TF-IDF to select representative values for text columns and summary statistics for numeric columns. This step produces text for later indexing.

```bash
python - <<'PYTHON'
from pathlib import Path

from data_lake import load_data_lake, read_table
from indexing.column_formatter import format_columns

tables = load_data_lake(Path("data/demo_lake"))
frames = {table.id: read_table(table) for table in tables}
columns = {
    (column.table_id, column.column_name): column
    for column in format_columns(frames)
}

for table_id, column_name in (
    ("store_sales", "store_id"),
    ("region_demographics", "population"),
):
    column = columns[table_id, column_name]
    print(f"{table_id}.{column_name}")
    print(f"  Metadata: {column.metadata}")
    print(f"  Content:  {column.content}")
PYTHON
```

## Estimate column frequencies and ranges

`build_column_statistics` builds frequency and range summaries keyed by
`(table_id, column_name)`. It uses a Count-Min sketch over non-null categorical
values and a quantile histogram over finite numeric values. These estimates can
serve as features when ranking candidate columns. The example uses the
dependencies installed above.

```bash
python - <<'PYTHON'
from pathlib import Path

from data_lake import load_data_lake, read_table
from indexing import build_column_statistics

tables = load_data_lake(Path("data/demo_lake"))
frames = {table.id: read_table(table) for table in tables}
stats = build_column_statistics(frames)

sales_ids = stats["store_sales", "store_id"]
population = stats["region_demographics", "population"]
print(sales_ids.frequency("S01"))  # Approximately 2/3
print(population.range_fraction(30000, 40000))  # Approximately 0.5
PYTHON
```

## Estimate key overlap and grouped correlation

Build key sketches separately from column statistics.
`KeySketch(table, key_column, k=256)` builds a bottom-`k` sketch of a pandas
DataFrame's distinct keys, excluding null keys. As in TIDE, keys match by
their string representation. `overlap(other)` estimates Jaccard similarity
from the bottom-`k` sample of the union and is exact when the union fits in
the sample. The examples use the dependencies installed above.

```python
from pathlib import Path

from data_lake import load_data_lake, read_table
from indexing import KeySketch

tables = load_data_lake(Path("data/demo_lake"))
frames = {table.id: read_table(table) for table in tables}

sales = KeySketch(frames["store_sales"], "store_id")
directory = KeySketch(frames["store_directory"], "store_id")
print(sales.overlap(directory))  # 1.0
```

`correlation(other, left_column, right_column)` computes Pearson correlation
between the per-key numeric means for shared sampled keys. Duplicate rows for
a key contribute to its mean. The method returns `None` when the correlation
is undefined.

```python
import pandas as pd

from indexing import KeySketch

left = pd.DataFrame({"key": ["a", "a", "b", "c"], "x": [2, 6, 8, 12]})
right = pd.DataFrame({"key": ["a", "b", "b", "c"], "y": [2, 3, 5, 6]})

left_sketch = KeySketch(left, "key")
right_sketch = KeySketch(right, "key")
correlation = left_sketch.correlation(right_sketch, "x", "y")
print(f"{correlation:.1f}")  # 1.0
```

## Example data

All four CSVs contain synthetic data. The sales rows for store `S01` share a `store_id` with the store directory entry for Maple Market. That entry links to demographics for region `R01` through `region_id`. The product catalog is a separate example table.
