# Table Discovery Agent

Use AgentScope to discover relevant tables in a local CSV lake. The agent follows relationships between tables and ranks candidates against the requirements in a natural-language query.

## Project structure

```text
table_discovery_agent/
├── README.md                   # Setup and demo instructions
├── agent.py                    # Discovery orchestration and planner toolkit
├── config.example.toml         # Example configuration and default values
├── data_lake.py                # CSV discovery, schema reading, and pandas table loading
├── main.py                     # CLI and configuration loading
├── requirements.txt            # Pinned dependencies
├── indexing/
│   ├── __init__.py             # Public formatter, index, and statistics APIs
│   ├── column_formatter.py     # Column metadata and content formatting
│   ├── column_index.py         # Metadata and content HNSW indexes
│   ├── column_matcher.py       # Column-name matching
│   ├── embedding.py            # Text encoder interface and local BGE implementation
│   ├── sketches.py             # Column statistics and key sketches
│   └── vdb.py                  # Build and load persisted lake indexes
├── discovery/
│   ├── __init__.py             # Public discovery state and relationship graph APIs
│   ├── constraints.py          # Query constraint extraction, checks, and result ranking
│   ├── prompts.py              # Prompt templates and retry instructions
│   ├── relationship_graph.py   # Join and union graph construction and path search
│   └── state.py                # Discovery tree and branch state
├── tools/
│   ├── __init__.py             # Toolkit factory for standalone operators
│   ├── combiner.py             # Candidate set operations by table ID
│   ├── composite_seeker.py     # TableOperators and relationship search
│   ├── ranker.py               # Value and relationship scoring
│   ├── seeker.py               # Text search and metadata filtering
│   └── termination.py          # Branch completion signal
└── data/
    └── demo_lake/              # Four synthetic example tables
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

## Run on your CSVs

Place comma-delimited UTF-8 `.csv` files directly inside a lake directory.
A UTF-8 byte order mark is accepted. Each table needs a header with nonempty,
unique column names. Rows with missing fields are read as missing values.

On CPU-only Linux, you can install the CPU build of PyTorch first.

```bash
python -m pip install --index-url https://download.pytorch.org/whl/cpu 'torch==2.8.0+cpu'
```

Install the pinned dependencies and copy the example configuration.

```bash
python -m pip install -r requirements.txt
cp config.example.toml config.toml
```

Set `data.lake_dir` to your CSV directory. Uncomment `data.vdb_dir` and
set it to an index directory. Point `model.embedding.model_dir` at a local copy of the model
weights and tokenizer. The example uses [BAAI/bge-large-en-v1.5](https://huggingface.co/BAAI/bge-large-en-v1.5).
Use `data/demo_lake` as the lake to try the bundled example.
Export `DEEPSEEK_API_KEY` before running `--ask`.

```bash
python main.py --config config.toml --validate
python main.py --config config.toml --build-index
python main.py --config config.toml --search "population" --top-k 3
python main.py --config config.toml --output ./results/answer.txt \
    --ask "Find tables with population data"
```

Replace the query text with a question about your CSVs.
Each result identifies a `table.column`. The table ID is the CSV filename
without its `.csv` extension, so `region_demographics.population` refers to
the `population` column in `region_demographics.csv` under `data.lake_dir`.

The schema browser checks headers. `--validate` reads every file using the
same CSV reader as queries and reports each file that fails.
It returns a nonzero exit code if any file fails.

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

Search returns matches from the selected channel. Each result shows the table and column, the inferred column type, and the cosine similarity score. The default channel is `metadata` and the default maximum is five results.

### Text encoder interface

The CLI selects an implementation with `create_encoder(name, model_path)` in `indexing/embedding.py`. The same encoder handles metadata, content, and queries during a search run. Additional implementations must provide `encode(texts)` that accepts a sequence of strings and returns a contiguous two-dimensional NumPy array of L2-normalized `float32` vectors. Return one row per input string, in input order, with a consistent embedding dimension across calls.

## Ask the discovery agent

Install the pinned dependencies and set `BGE_MODEL_DIR` as shown above. Export your DeepSeek API key as `DEEPSEEK_API_KEY`. In Bash or Zsh, you can enter the key without displaying it or putting it in the command history.

```bash
read -rs DEEPSEEK_API_KEY
export DEEPSEEK_API_KEY

query="Find tables with population between 30,000 and 40,000 for regions where stores report sales. Start from sales records with store_id, month, and revenue. Use store_id to find the store directory, then use region_id from the directory to find population data. Apply the population range to the tables found in the last step."

python main.py --lake data/demo_lake --embedding-model "$BGE_MODEL_DIR" \
    --ask "$query"
```

In a DeepSeek Flash run, the first join found `store_directory` through
`store_id`. The next join used `region_id` to find `region_demographics`.
The agent then ranked the candidates by the population range and ended the
search. The CLI returned

```text
region_demographics.population
```

`--ask` uses DeepSeek Flash (`deepseek-flash`) by default. Pass `--chat-model MODEL` to select another DeepSeek model with tool calling. The agent extracts column constraints from the question, then observes candidate tables and their relationships, plans tool calls, and executes them against the local lake. A search can retrieve columns by metadata, explore join or union paths, rank candidates by values, and preserve results with `end_search`. The CLI prints each match on its own line as `table.column`, such as `region_demographics.population`.

Indexing and tool execution run locally. DeepSeek receives the query and discovery context, which can include candidate table names and schemas, relationship evidence, and prior tool actions.

Use `--search` for direct column retrieval with `--channel` and `--top-k`. Run `--ask` and `--search` in separate commands.

### Toolkit entry points

- `agent.create_planner_toolkit()` powers `--ask`. The planner passes discovery node IDs, and the toolkit resolves them to candidate tables.
- `tools.create_toolkit()` registers standalone operators for direct Python calls. Callers pass column queries, candidate columns, or reference tables explicitly.

The `--search` CLI queries the column index directly.

## Build and reuse a VDB

Set `data.vdb_dir` in your configuration, or pass `--vdb-dir` on the CLI.
Build once with `--build-index` before querying that directory.

Each build saves two FAISS indexes, the table and column catalog, SQLite
sketches, and the relationship graph. The source CSVs stay in the lake.
Queries reuse the published build and read candidate CSVs as needed.
Rebuild after changing the CSVs or the embedding model.
A rebuild publishes a new generation after all its files are ready.
Previous generations remain available to queries that already opened them.

FAISS loads each selected HNSW index into memory. Direct search loads one
channel, while the discovery agent uses both. Leave `data.vdb_dir` unset to
build indexes in memory for a small lake.

## Configure the CLI

Copy `config.example.toml` to `config.toml` and set
`model.embedding.model_dir` to your local BGE model directory.
Set `data.lake_dir` to the directory with your CSVs.

CLI options override TOML values, which override built-in defaults.
Relative paths in TOML are resolved from the configuration file's directory.
Relative CLI paths are resolved from the working directory.
Both accept `~` for the home directory.

| TOML key | CLI option | Requirement or default |
| --- | --- | --- |
| `data.lake_dir` | `--lake` | Required to browse, build, or query tables |
| `data.vdb_dir` | `--vdb-dir` | Required for `--build-index`. Set to reuse saved indexes |
| `output.path` | `--output` | Optional. Query results default to the terminal |
| `model.embedding.encoder` | `--encoder` | `bge` |
| `model.embedding.model_dir` | `--embedding-model` | Required for building and querying indexes |
| `model.chat.name` | `--chat-model` | `deepseek-flash` |
| `search.max_rounds` | `--max-rounds` | `6` rounds per `--ask` query |
| `search.stagnation_limit` | `--stagnation-limit` | `3` rounds without progress |
| `search.candidate_limit` | `--candidate-limit` | `10` candidate tables per round |

```bash
python main.py --config ./config.toml
python main.py --config ./config.toml --ask "Find population data"
python main.py --config ./config.toml --max-rounds 8 \
    --output ./results/answer.txt --ask "Find population data"
```

Supply `DEEPSEEK_API_KEY` in the environment for `--ask`.
Use `--channel` and `--top-k` to tune `--search`.
An output file uses the same UTF-8 text as the terminal.
Choose a new file path for each saved result.

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
