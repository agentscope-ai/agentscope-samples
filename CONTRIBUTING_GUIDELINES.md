# 🤝 Contributing Guide

Welcome to contribute to the AgentScope Sample Agents project! Please follow this guide to ensure efficient collaboration.


---

# 📁 Directory Structure Requirements
All examples must be organized by functionality. The structure follows the root README.md layout:
```bash
agentscope-samples/
├── browser_use/                      # Browser automation examples
│   ├── agent_browser/                # Pure Python browser agent
│   └── browser_use_fullstack_runtime/ # Full-stack runtime version
├── deep_research/                    # Deep research examples
│   ├── agent_deep_research/
│   └── qwen_langgraph_search_fullstack_runtime/
├── games/
│   └── game_werewolves/              # Werewolf game
├── conversational_agents/            # Conversational applications
│   ├── chatbot/
│   └── multiagent_conversation/
├── functionality/                    # Functional examples
│   ├── long_term_memory_mem0/
│   └── stream_printing_messages/
└── CONTRIBUTING_GUIDELINES.md
```


---

# 📥 Submitting a Pull Request (PR)

### 1. **Directory Placement**
- **Location**:
  Choose an existing subdirectory (e.g., `browser_use/`、`games/`), or create a new one (update the **Example List** table in the root `README.md`)
- **File Naming**:  
  - Example files: `feature_description.py`(如 `chatbot_multi_turn.py`)  
  - Test files: `test_feature_description.py`

### 2. **Write a Detailed README**
- **Subdirectory `README.md`**:  
  Include the following to ensure reproducibility:
  ```markdown
  ## Example Name (e.g., Multi-turn Chatbot)

  ### 📌 Description
  Demonstrates the implementation of multi-turn conversations.

  ### 📦 Dependencies
  ```bash
  pip install -r requirements.txt
  ```
  
### 🚀 Run Command
```bash
python chatbot_multi_turn.py
```


- **Root `README.md`**:  
Update the **Example List** table with links to new examples.

### 3. **Dependency Management**
- **Each Subdirectory Requires `requirements.txt`**:  
List only dependencies needed for that example:

```txt
openai==0.27.0
pandas==2.0.0
```

### 4. **Code Formatting**
- **Install `pre-commit`**:  
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
# Fix any formatting errors (e.g., indentation, line length)
```


### PR Checklist
- [ ] Example placed in the correct subdirectory (e.g., `browser_use/`、`games/`)
- [ ] Subdirectory includes `README.md` and `requirements.txt`
- [ ] Code formatted with `pre-commit`
- [ ] New test cases cover core functionality
- [ ] Root `README.md` updated with the new example
- [ ] PR title is clear (e.g.,  `Add multi-turn chatbot example`)

---
