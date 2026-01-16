# Training Learn2Ask with AgentScope-Tuner

This guide demonstrates how to train a proactive LLM using the **Learn2Ask** framework from [Grounded in Reality: Learning and Deploying Proactive LLM from Offline Logs](https://arxiv.org/abs/2510.25441).

---

## Task Setting

In this example, given a user's chief complaint, the medical assistant agent proactively asks targeted questions to gather sufficient symptom information for a comprehensive assessment of the user's health condition. The querying process should be efficient: the agent must optimize question quality, and terminate the interview as soon as the collected information is adequate for subsequent clinical assessment or decision-making.
Here we use the `ReActAgent` for this task and no tools are required.

---

## Hardware Requirements

- **Training with GPUs**: At least **8 H20 GPUs** (or equivalent).
- **Training without GPUs**: You can use the **[Tinker](https://thinkingmachines.ai/tinker/)** without any GPUs.

> 💡 All code and configuration files are located in:
> `tuner/learn_to_ask/`

Key files:
- Workflow & Training: `tuner/learn_to_ask/main.py`
- Prompts: `tuner/learn_to_ask/prompt.py`
- Training config: `tuner/learn_to_ask/config.yaml`
- Data preparation scripts: `tuner/learn_to_ask/data_prepare/`

---

## Dataset Preparation

> [!NOTE]
> In this example, we use an open-source dataset directly for training. In practice, however, you would typically start by collecting interaction logs between your deployed agent and users. After filtering these raw logs to curate a high-quality dataset, you can follow the same pipeline to enhance your agent’s proactive capabilities using AgentTune. Happy tuning!

### 1.1 Download the Dataset
Download the **[RealMedConv](https://huggingface.co/datasets/datajuicer/RealMedConv)** dataset (in `.jsonl` format).
You can use the following python scripts to download the dataset:

```python
from huggingface_hub import snapshot_download

# Download to local directory, e.g., `./tuner/learn_to_ask/data`
local_dir = "./tuner/learn_to_ask/data"
snapshot_download(
    repo_id="datajuicer/RealMedConv",
    repo_type="dataset",
    local_dir=local_dir,
)
```

Each line in `train_origin.jsonl` (or `test_origin.jsonl`) represents a complete doctor-patient conversation log, like this:

```json
{
  "session_id": 35310,
  "diagn": "Upper Respiratory Tract Infection",
  "messages": [
    {"role": "user", "content": "Sore throat, phlegm, red eyes, cough, hoarse voice"},
    {"role": "user", "content": "I took Amoxicillin"},
    ...
    {"role": "assistant", "content": "<med_search>"}
  ]
}
```

### 1.2 Preprocess the Data
You need to convert raw conversation logs into training samples. This involves two steps:

#### 🔹 Step A: Segment Conversations & Extract Labels
Split each conversation into **context–future pairs**, and extract ground-truth symptom information (`info_truth`) from what happens next.

```bash
python tuner/learn_to_ask/data_prepare/1_info_extract_pipeline.py \
  --input_file /path/to/RealMedConv/train.jsonl \
  --output_file tuner/learn_to_ask/data_raw/train_processed.jsonl \
  --model_path Qwen/Qwen2.5-32B-Instruct
```

#### 🔹 Step B: Build Final Training Dataset
Convert the processed samples into the final format used for training/testing.

```bash
python tuner/learn_to_ask/data_prepare/2_build_dataset.py \
  --input_file tuner/learn_to_ask/data_raw/train_processed.jsonl \
  --output_file tuner/learn_to_ask/data/train.jsonl
```

---

### How It Works: Context–Future Segmentation

For every turn in a conversation, we create a sample with:
- `messages`: The **observed dialogue history** up to that point (the *context*).
- `remaining_chat`: Everything that happens **after** that point (the *future*).
- A unique ID: `cid = {session_id}_{turn_index}`

Example output:
```json
{
  "cid": "35310_7",
  "session_id": "35310",
  "diagn": "Upper Respiratory Tract Infection",
  "messages": [ ... up to turn 7 ... ],
  "remaining_chat": [ ... all future messages ... ]
}
```

### Extract Ground-Truth Labels

From `remaining_chat`, we automatically derive two key labels:
- `decision_truth`: Should the assistant **continue asking questions** (`"continue"`) or **stop** (`"stop"`)?
- `info_truth`: Structured list of symptoms mentioned later (used to compute reward signals during training).

Example:
```json
{
  "decision_truth": "continue",
  "info_truth": "Symptom: sore throat, Symptom quality: thick discharge, Symptom quality: yellowish discharge, ..."
}
```

These labels power the reward functions $R_a$ (action accuracy) and $R_s$ (symptom coverage) during training.

---

## Code Implementation

### Agent Workflow

The workflow function `run_react_agent` implements how the `ReActAgent` works.

```python
async def run_react_agent(
    task: Dict,
    model: OpenAIChatModel,
    auxiliary_models: Dict[str, OpenAIChatModel],
) -> WorkflowOutput:
    assert (
        len(auxiliary_models) == 1
    ), "Please provide only one `auxiliary_models` for `learn_to_ask`."

    import importlib

    spec = importlib.util.spec_from_file_location(
        "prompt",
        os.path.join(os.path.dirname(__file__), "prompt.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if TRAIN_MODE == "Ra":
        sys_prompt = module.rollout_prompt_med_Ra
    else:
        sys_prompt = module.rollout_prompt_med

    agent = ReActAgent(
        name="react_agent",
        sys_prompt=sys_prompt,
        model=model,
        formatter=OpenAIChatFormatter(),
        toolkit=None,
        memory=InMemoryMemory(),
        max_iters=1,
    )
    messages = format_messages(task["messages"])
    response = await agent.reply(
        [
            Msg(name=x["role"], content=x["content"], role=x["role"])
            for x in messages
        ],
    )
    return WorkflowOutput(
        response=response,
    )
```

### Judge Function

The judge function `learn2ask_judge` implements reward calculation using LLM-as-a-Judge:

```python
async def learn2ask_judge(
    task: Dict,
    response: Msg,
    auxiliary_models: Dict[str, OpenAIChatModel],
) -> JudgeOutput:
    assert (
        len(auxiliary_models) == 1
    ), "Please provide only one `auxiliary_models` for `learn_to_ask`."

    response_text = response.get_text_content()
    action_truth = (
        task["decision_truth"] if "decision_truth" in task else "continue"
    )

    action_response = "stop" if "<stop />" in response_text else "continue"
    if action_truth == action_response:
        action_score = 1.0
        if action_truth == "continue":
            score_dict = await llm_reward(
                task=task,
                response=response_text,
                auxiliary_models=auxiliary_models,  # LLM-as-a-Judge
            )
            if score_dict != {}:
                format_score = float(score_dict.get("format_score", 0.0))
                content_score = float(score_dict.get("content_score", 0.0))
            else:
                format_score, content_score = 0.0, 0.0
        else:
            content_score = 1.0
            format_score = 1.0 if response_text == "<stop />" else 0.0
    else:
        action_score, format_score, content_score = 0.0, 0.0, 0.0

    if TRAIN_MODE == "Ra+Rs":  # the default setting
        final_reward = (
            action_score * (1 + 2 * content_score) + format_score
            if FUSION_MODE != "sum"
            else action_score + content_score + format_score
        )
    elif TRAIN_MODE == "Ra":  # for Ra only (without Rs)
        final_reward = 2 * content_score + format_score
    else:  # for Rs only (without Ra)
        final_reward = action_score * 3 + format_score

    return JudgeOutput(
        reward=final_reward,
        metrics={"reward": final_reward},
    )
```

This reward function considers:
- Action accuracy: `action_score`
- Question quality (Symptom coverage): `content_score`
- Format score: `format_score`

See [main.py](./main.py) for implementation details.

---

## Configure and Train the Model

### Option A: Edit Python Script (Simple)
Open `tuner/learn_to_ask/main.py` and adjust settings:

```python
if __name__ == "__main__":
    train_mode = "Ra+Rs"     # Use both action and symptom rewards
    fusion_mode = "default"  # How to combine rewards
    dataset = DatasetConfig(path="tuner/learn_to_ask/data", split="train")

    tuner_model = OpenAIChatModel(
        model_path="Qwen/Qwen2.5-7B-Instruct",
        max_model_len=8192,
        tensor_parallel_size=1,  # Adjust based on your GPU setup
        ...
    )

    auxiliary_models = {
        AUXILIARY_MODEL_NAME: OpenAIChatModel(
            model_path="Qwen/Qwen2.5-32B-Instruct",  # Larger model for evaluation
            tensor_parallel_size=2,
            ...
        )
    }

    algorithm = AlgorithmConfig(
        algorithm_type="grpo",
        learning_rate=5e-7,
        batch_size=64,
    )

    tune(...)  # Starts training
```

### Option B: Use YAML Config (Advanced)
Edit `tuner/learn_to_ask/config.yaml` for more control.

#### 🌐 No GPU? Use Tinker!
If you don’t have GPUs, enable the **Tinker backend** by setting:

```yaml
model:
  tinker:
    enable: true  # ← Set this to true
```

Also, make sure to update the `model_path` in `tuner/learn_to_ask/main.py` to point to a model that’s compatible with Tinker.

> 🔗 Learn more about Tinker Backend: [Tinker Backend Documentation](https://agentscope-ai.github.io/Trinity-RFT/en/main/tutorial/example_tinker_backend.html)

### Launch Training
```bash
python tuner/learn_to_ask/main.py
```

---

## Evaluation

Use the **rollout-and-evaluate pipeline**:
1. Generate responses on the test set.
2. Score them using a powerful evaluator model (`Qwen2.5-32B-Instruct`).

Run evaluation:
```bash
python tuner/learn_to_ask/data_prepare/3_rollout_then_evaluate.py \
  --eval_model_path path/to/your/trained/model \
  --grader_model_path Qwen/Qwen2.5-32B-Instruct \
  --test_file_path tuner/learn_to_ask/data/test.jsonl \
  --rollout_file_path path/to/rollout.jsonl \
  --eval_file_path path/to/output.jsonl
```

> ⚠️ **Note**: Your trained model must be converted to **Hugging Face format** first.
> See: [Converting FSDP Checkpoints Guide](https://modelscope.github.io/Trinity-RFT/en/main/tutorial/faq.html)

---

## Experimental Results

We compared three approaches:
- **Base model**: `Qwen2.5-7B-Instruct` (no fine-tuning)
- **Trinity**: Direct response generation
- **As-tune (Learn2Ask)**: Uses a ReAct agent for proactive questioning

| Metric                               | Base Model | Trinity | As-tune (Learn2Ask) |
|--------------------------------------|-----------:|--------:|--------------------:|
| Avg. continue content                |      0.436 |   0.496 |               0.509 |
| Win rate (continue content)          |      0.122 |   0.246 |               0.224 |
| Avg. continue decision accuracy      |      0.963 |   0.909 |               0.922 |
| Avg. stop decision accuracy          |      0.024 |   0.927 |               0.909 |
| **Total decision accuracy**          |      0.467 |   0.918 |               0.915 |
| **Response format quality**          |      0.376 |   0.713 |               0.882 |
| **Total reward**                     |      1.281 |   3.078 |               3.237 |

![Training Curves](./learn2ask.png)

> ✅ **Key insight**: Learn2Ask (As-tune) achieves the highest overall performance by teaching the model **when and what to ask**—making it truly proactive.

### Concrete Example

An example of the agent's behavior on evaluation data is shown below:

```json
{
  "cid": "206_1",
  "session_id": 206,
  "diagn": "Common cold",
  "messages": [
    {
      "role": "assistant",
      "content": "Hello, currently there are many people consulting, please wait patiently."
    },
    {
      "role": "user",
      "content": "Hello, this morning around 10 o'clock, I suddenly felt a bit feverish and had a heavy head. I took my temperature and it was 38.5°C. I took one tablet of paracetamol at 1 o'clock, which helped a lot. By 6 or 7 in the evening, I felt cold and feverish again, so I took another tablet of paracetamol. I'm not sure if it's a side effect of the medication, but I feel a bit nauseous and my stomach keeps producing gas. Now, I feel cold again, have a stuffy nose with clear runny nose, an itchy throat with coughing, a heavy head, and can't sleep."
    }
  ],
  "decision_truth": "continue",
  "info_truth": "symptom: needle-like sensation, symptom location: ear, symptom nature: sharp pain, symptom severity: occurred twice",
  "rollouts": [
    "Do you also experience body aches along with your symptoms?  \nA) Yes B) No C) Not Sure",
    "Do you experience these symptoms every time after taking paracetamol? (A) Yes, definitely. (B) Sometimes. (C) No, never before.",
    "Do you have a history of allergies? A) Yes B) No C) Not Sure"
  ],
  "grades": [
    {
      "think": "The doctor's last message asks about body aches using multiple choice options rather than a single direct open-ended question, which deviates from the typical questioning style indicated by the grading policy. However, since it is framed in the form of \"Do you...\", it counts as one question despite being presented with choices. Thus, it satisfies the criteria for 'contains exactly one question'. For the content score, the query does not pertain directly to the details listed in the reference information such as the specific symptom ('needle-like' sharp pain in the ear that has occurred twice), thereby making it highly relevant yet indirectly related due to its focus on comprehensive assessment of flu-related discomforts without addressing specifics noted in the patient’s primary concern documented earlier.",
      "action_score": 1,
      "format_score": 1.0,
      "content_score": 0.5
    },
    {
      "think": "The doctor's last message includes just one multiple-choice question regarding whether the patient experiences those mentioned symptoms each time they take paracetamol. This does relate highly to understanding possible drug-related symptoms; however, none of them aligns perfectly with \"needle-like\" sensations occurring specifically in ears according to the reference information given.",
      "action_score": 1,
      "format_score": 1.0,
      "content_score": 0.5
    },
    {
      "think": "The doctor’s last statement does contain just one question pertaining to allergy history, which is highly relevant when trying to diagnose symptoms such as those described by the patient (fever, nausea). However, none of these concerns specifically relate back to the reference information detailing \"needle-like sensation\", \"sharp pain\" related to the ears occurring twice. Therefore, while highly pertinent medically, they do not pertain to the exact points outlined in the Ref Info section about the patient experience according to that specific prompt context.",
      "action_score": 1,
      "format_score": 1.0,
      "content_score": 0.5
    }
  ]
}
```

---

## 📚 Citation

If you use this code or framework, please cite our work:

```bibtex
@misc{learn2ask,
      title={Grounded in Reality: Learning and Deploying Proactive LLM from Offline Logs},
      author={Fei Wei and Daoyuan Chen and Ce Wang and Yilun Huang and Yushuo Chen and Xuchen Pan and Yaliang Li and Bolin Ding},
      year={2025},
      eprint={2510.25441},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2510.25441}
}
```
