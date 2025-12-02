# -*- coding: utf-8 -*-
SESSION_SUMMARY_PROMPT = """
You are a task analysis expert. Please analyze the following session
content and extract:
1. What is the specific task
2. What general problem category does this belong to

Please provide a concise summary focusing on the essence of the task
and problem classification.
"""

SESSION_SUMMARY_USER_PROMPT = """
You must return your response in the following JSON structure only:
{{
    "task" : "<What is the specific task>",
    "problem_category" : "<What general problem category does this belong to>"
}}
Do not return anything except the JSON format.
If no useful information is extracted from the session content, return
an empty JSON object:
{{
    "task" : "Unknown Task Type",
    "problem_category" : "Unknown Task Type",
}}
"""

AGENT_ROADMAP_PROMPT = """
You are a task-solving process analyst. Your goal is to extract a
detailed and precise agent task-solving roadmap from given task
descriptions and user-agent conversations. Follow these guidelines
carefully:

1. Agent Identification:
   - Identify ONLY different agents/assistants/roles (ignore user messages)
   - Use exact agent names/roles as they appear in the session
   - Maintain original agent naming conventions

2. Task Analysis:
   - Extract specific subtasks completed by each agent
   - For similar subtasks by the same agent, merge into a single node
   - Never merge subtasks from different agents
   - Preserve all original parameters for tool calls/API invocations
   - Maintain the exact execution sequence of tasks and subtasks
   - If any agent skips a task, mark it as Pending or Failed, depending
     on context

3. Relationship Mapping:
   - Map task allocation relationships (who is doing what, and in what
     order)
   - Identify handoffs between agents clearly (e.g., agent A starts a
     task, agent B takes over)
   - Identify parallel task execution if applicable, especially if
     multiple agents are working simultaneously on separate subtasks
   - For handoffs, make sure to log the task sequence and dependencies

4. Status Tracking:
   - Mark completion status for each task:
     * Succeeded: Completed successfully
     * Failed: Terminated with errors
     * Pending: Not yet started
     * In progress: Currently being executed
   - If unsure about the status of a task, mark it as Failed

Output Requirements:
- Return ONLY valid JSON format
- Structure output with these fields for each node:
{{
    "roadmap": [
        {{
            "name": "<Exact agent name/role>",
            "seq": "<Unique execution sequence number (starting from 1)>",
            "subtask": "<Specific task description>",
            "implement": "<Detailed implementation including "
                        "thoughts/plans/tools/parameters>",
            "status": "<Succeeded/Failed/Pending/In Progress>",
            "handover_to": "<Agent name if task is handed off, "
                           "otherwise 'N/A'>",
            "parallel_tasks": ["<List of parallel tasks if applicable, "
                              "otherwise 'N/A'>"],
            "time_dependency": "<Any timing info or 'N/A'>"
        }},
        ...
    ]
}}

If no useful information is extracted from the session content, return
an empty JSON object:
{{
    "roadmap": []
}}

Special Instructions:
- Preserve all technical details in implementations
- Maintain original parameter formats for API/tool calls
- Never summarize or omit operational details
- Do not explain the roadmap; focus strictly on the task-solving process
- If uncertain about status, mark as "Failed"

Important: Only return the JSON object with no additional text,
explanations, or formatting.
"""

AGENT_KEY_WORKFLOW_PROMPT = """
Please analyze the given agent roadmap and summarize common high-level
workflows. For each workflow, provide:
1. A **task description**: Generalize the task (e.g., use
   "{tourist-attractions}" instead of "West Lake and Lingyin Temple",
   or "{product-name}" instead of "Air purifier").
2. Several **workflow trajectories**. Each trajectory should include:
    - **[reason]**: A description of the environment or context
      (generalized), and the reasoning or decision behind the action.
    - **[action]**: The specific action taken by the agent in that
      context.

Each workflow should represent a commonly reused sub-routine or sequence
of tasks from the agent roadmap. Do **NOT** generate similar or
overlapping workflows.
- Each workflow must contain at least two steps.
- Represent non-fixed elements with descriptive **variable names** (e.g.,
  "{user-info}", "{task-name}").
- If applicable, track **decision points** that led to branching actions.

Output the result in the following JSON format:
{
    "workflows": [
        {
            "task_description": "string",
            "trajectories": [
                {
                    "reason": "string",
                    "action": "string"
                },
                ...
            ]
        },
        ...
    ]
}

If no workflows are identified, return an empty JSON object:
```json
{
    "workflows": []
}
Important: Only return the JSON object with no additional text,
explanations, or formatting.
"""

SUBTASK_ROADMAP_PROMPT = """
You are a task-solving process analyst. Your goal is to extract a
detailed and precise subtask-solving roadmap from given task descriptions
and user-agent conversations. Follow these guidelines carefully:

1. Subtask Identification:
   - Identify **all** subtasks (regardless of specific agents) that
     contribute to solving the main task.
   - For highly similar subtasks (with similar content and goals), merge
     them into a single subtask, but preserve all key parameters and
     details.
   - Maintain the original order of subtasks as they appear in the workflow.

2. Subtask Analysis:
   - For each subtask, extract the following information:
     * seq: Unique execution sequence number (starting from 1, in order
       of execution)
     * content: The specific content and goal of the subtask
     * implement: Detailed implementation process, including thoughts,
       plans, tools or APIs used, and their parameters. This should also
       include specific details about dependencies between tasks, if
       present

3. Handling Subtask Handoffs:
   - If a subtask is handed off between agents, ensure that the handoff
     is explicitly marked. The order of subtasks is key—be sure to track
     the transition correctly.

Output Requirements:
- Return ONLY valid JSON format, structured as follows:
  {{
    "roadmap": [
      {{
        "seq": "<Unique execution sequence number>",
        "subtask": "<Subtask content>",
        "implement": "<Detailed implementation process>"
      }},
      ...
    ]
  }}

If no useful information is extracted from the session content, return
an empty JSON object:
{{
    "roadmap": []
}}

Special Instructions:
- Preserve all technical details and parameters; do not omit operational
  details
- Ensure sequential order of subtasks is maintained
- Only output the JSON object, with no extra explanations, comments, or
  formatting
"""

SUBTASK_KEY_WORKFLOW_PROMPT = """
Please analyze the given task-solving roadmap and summarize common
high-level workflows. For each workflow, provide:
- A task description: A generalized task description that abstracts the
  specific task into a reusable pattern (e.g., use "{product-name}"
  instead of "Air purifier").
- Several workflow trajectories. Each trajectory should include:
     - [reason]: A description of the environment or context
       (generalized) and The reasoning or decision behind the action.
     - [action]: The action taken by the agent(s) based on the reason.

**Workflow Guidelines**:
- Each workflow should represent a **commonly reused subroutine** across
  multiple tasks, emphasizing high-level operations that can be adapted
  to different contexts.
- **Avoid generating similar or overlapping workflows**; ensure each
  workflow is distinct in its pattern and usage.
- A workflow should consist of at least **two steps** (actions), and
  should demonstrate a clear decision-making process or task progression.
- Represent non-fixed elements with **descriptive variable names** such
  as "{user-info}", "{product-name}", or "{task-context}".
- The task description should abstract the main task into **generalizable
  terms** so it can apply to different scenarios.

**Example**:
For a "booking a flight" task, the workflow could include:
- Task description: "{travel-booking}"
- Workflow:
  - Reason: "User needs to book a flight based on the available travel dates."
  - Action: "Search available flights based on the selected dates."
  - Reason: "User selects a flight based on price and duration."
  - Action: "Confirm flight selection and proceed with payment."

Output the result in the following JSON format:
{
    "workflows": [
        {
            "task_description": "string",
            "trajectories": [
                {
                    "reason": "string",
                    "action": "string"
                },
                ...
            ]
        },
        ...
    ]
}

If no workflows are identified, return an empty JSON object:
```json
{
    "workflows": []
}

Important: Only return the JSON object with no additional text,
explanations, or formatting.
"""

MERGE_WORKFLOW_PROMPT = """
You are given two lists of workflows, each in the following format:
[
    {
        "task_description": "...",
        "trajectories": [
            {"reason": "...", "action": "..."},
            ...
        ]
    },
    ...
]

Your task:
1. **Identify the most similar pair of workflows** (one from each list)
   based on the **"task_description"**, **"reason"**, and **"action"**.
   You should consider:
   - Textual similarity of the **task_description** using semantic
     similarity (e.g., cosine similarity, Jaccard similarity, or other
     suitable methods).
   - **Reason and action** pairs: Match them based on content overlap or
     similarity in task sequence and logic.

2. **Merge the most similar pair** into a single workflow:
   - **task_description**: If the descriptions are very similar, use one.
     If there is ambiguity or both have important details, merge the
     descriptions.
   - **trajectories**:
     - If the lengths differ, keep the list with the greater length.
     - If the lengths are the same, compare the specific `reason` and
       `action` pairs and combine them logically, eliminating duplicates
       or very similar pairs.
     - Ensure no information is lost in the merge.

3. **Keep all other workflows** from both lists as they are without merging.

4. **Ensure the order of workflows** remains strictly based on the
   original order from each list. If workflows have interleaved or
   overlapping purposes:
   - Analyze their functions and arrange them in a logical sequence that
     best reflects their role in the overall process.

5. **Final output**: Return a single JSON object with a `workflows` key
   containing the merged and unmerged workflows. The format should be:
```json
{
    "workflows": [
        ... // merged workflow and all unmerged workflows
    ]
}

Here are the two workflow lists:
agent_solve_key_workflows:
%s

subtask_solve_key_workflows:
%s

Return only the JSON object, no explanation.
"""

EXTRACT_WORKFLOWS_PROMPT = """
Given the session content of an task query between the user and the
agent(s), your task is to summarize common high-level workflows.
For each workflow, please provide:
1. A **task description**: Generalize the task (e.g., use
   "{tourist-attractions}" instead of "West Lake and Lingyin Temple", or
   "{product-name}" instead of "Air purifier").
2. Several **workflow trajectories**. Each trajectory should include:
    - **[reason]**: A description of the environment or context
      (generalized), and the reasoning or decision behind the action.
    - **[action]**: The specific action taken by the agent in that
      context.

Each workflow should represent a commonly reused sub-routine or sequence
of tasks from the agent roadmap. Do **NOT** generate similar or
overlapping workflows.
- Each workflow must contain at least two steps.
- Represent non-fixed elements with descriptive **variable names** (e.g.,
  "{user-info}", "{task-name}").
- If applicable, track **decision points** that led to branching actions.

**Output Requirements**:
- Return ONLY valid **JSON** format as follows:
```json
{
    "workflows": [
        {
            "task_description": "string",
            "trajectories": [
                {
                    "reason": "string",
                    "action": "string"
                },
                ...
            ]
        },
        ...
    ]
}

Important Instructions:
- Only include workflows that contain meaningful steps and are distinct
  from one another
- Ensure the task description is generalized enough to be applicable to
  different similar tasks but specific enough to convey the essence of
  the task
- If one workflow contains multiple steps, ensure that each step has a
  clear reason and action linked to it
- The reason should describe the agent's decision-making process and why
  they chose to perform a specific action
- Do not provide any additional text, explanations, or comments outside
  the JSON object

If no workflows are identified, return an empty JSON object:
```json
{
    "workflows": []
}
"""

EXTRACT_LIKE_MESSAGE = """
Please analyze the following user-liked message and extract its core role
in the task-solving process.

Task Background: {task_description}

Task Classification: {task_classification}

User-liked Message: {liked_message}

Please answer from the user's perspective in the following format:
"I like [core content/insight] in the #task [{task_classification}]."

Important:
- Only output above format in the answer. Any additional text or
  explanations should be omitted.
- Make sure to accurately reflect the user's preference and clearly state
  the function of this message in the context of the task.
"""

EXTRACT_UNLIKE_MESSAGE = """
Please analyze the following user-disliked message and identify its core
issue or limitation in the task-solving process.

Task Background: {task_description}

Task Classification: {task_classification}

User-disliked Message: {unliked_message}

Please answer from the user's perspective in the following format:
"I dislike [core issue/problem] in the #task [{task_classification}]."

Important:
- Only output above format in the answer. Any additional text or
  explanations should be omitted.
- Make sure the answer clearly reflect why the message is not preferred
  by the user and what part of the message limits or misaligns with the
  task-solving process.
"""

EXTRACT_EDIT_PREFERENCE = """
You are an intelligent analysis agent. You are given a pair of
dictionaries named `diff_map`, structured as follows:
{
  "previous": {...},   # original roadmap before user edits
  "current": {...}     # roadmap after user edits
}

The value of ["previous"] and ["current"] can be any format, such as a
JSON object or a list of dictionaries or strings or other data
structures.
Your task is to extract the user's **preferences** based on how they
modified the roadmap. Carefully compare the `previous` and `current`
versions to identify what was changed and interpret the intent behind
each change.

Please follow these reasoning steps:
1. Identify which part(s) of the roadmap were modified (e.g., subtask
   content, goals, descriptions, constraints, steps, etc.).
2. For each distinct change, determine the **underlying purpose**:
   - Does the change adjust the task-solving **workflow or method**?
   - Does it **clarify or refine a specific goal**?
   - Does it reflect the user's **personal values, lifestyle needs,
     expectations, or habits**?
   - Is it intended to **reduce ambiguity**, **optimize execution**, or
     **add flexibility**?
   - Or other reasonable purpose?
3. Analyze the **expression style** of each change:
   - If preferences are **clearly stated or emphasized** (e.g., using
     words like "must", "prefer", "should", "important"), then the type
     is `"explicit"`.
   - If preferences are **implied through structure, reordering, soft
     constraints, or tone**, then the type is `"implicit"`.

Then, for each identified preference, summarize it in **first-person
perspective** (e.g., "I prefer...", "I want...", "I value...").
Be cautious: Only extract preferences that are **reasonably justified** by
the edits. Ignore trivial or stylistic changes.

Finally, group and combine preferences by type:
- If there are multiple explicit preferences, combine and summarize them
  into **one** sentence in **first-person perspective**.
- If there are multiple implicit preferences, combine and summarize them
  into **one** sentence in **first-person perspective**.

Return the output in this exact format (as a JSON array):
```json
{
  "analysis_result": [
  {
    "type": "explicit" or "implicit",
    "user_preference": "I prefer/apparently want/value ..."
  },
  ...
  ]
}

If no preferences are identified, return an empty json array as follows:
```json
{
  "analysis_result": []
}

Use general language: you may abstract away low-level field names into
generalized terms (e.g., convert "allow_ssl": false into "I prefer to
disable SSL for better compatibility").
NOTE: Only return the JSON object with no additional text, explanations,
or formatting.

"""

EXTRACT_EDIT_FILE_PREFERENCE = """
You are a user behavior analysis agent. You are given the output of a
`git diff` command, which shows how a user has modified a text-based file
(e.g., configuration files, structured markdown, JSON, YAML, or
documentation).
Your task is to extract the user's **preferences** as reflected by the
changes in the diff.

---

Follow these reasoning steps carefully:
1. **Analyze the diff output**:
   - Lines starting with `+` indicate additions
   - Lines starting with `-` indicate deletions
   - Modifications may involve reordered lines, reworded entries, or
     added/removed fields, comments, or constraints
2. For each meaningful change, determine if it reflects a **user
   preference**, such as:
   - Selection or exclusion of features
   - Reordering of content or priorities
   - Preference for certain terms, structures, styles, or formats
   - Addition of constraints, options, explanations, or soft
     conditions
   - Removal of elements that are undesired or irrelevant
3. Classify each preference as:
   - `"explicit"` — if the user clearly communicates rationale or intent
     via keywords (e.g., "should", "must", "recommended", "due to"),
     comments, or notes
   - `"implicit"` — if the preference is inferred through structural
     changes, like:
     - Reordering that suggests prioritization
     - Silent additions or removals of options
     - Alterations implying hidden expectations, soft constraints, or
       trade-offs
4. **Important constraint**: Your final result must contain **no more
   than one entry per type**:
   - If any explicit preferences exist, summarize them into **a single
     first-person sentence**
   - If any implicit preferences exist, summarize them into **a single
     first-person sentence**
5. Use natural, generalized first-person language (e.g., "I prefer…",
   "I value…", "I tend to avoid…"). Abstract away low-level field names
   when appropriate (e.g., "allow_ssl": false → "I prefer to disable
   SSL for compatibility").

---
Return your output as a JSON format. Each element should follow this structure:

```json
{
  "analysis_result": [
  {
    "type": "explicit" or "implicit",
    "user_preference": "I prefer/apparently want/value ..."
  },
  ...
  ]
}

If no preferences are identified, return an empty json array as follows:
```json
{
  "analysis_result": []
}

Use general language: you may abstract away low-level field names into
generalized terms (e.g., convert "allow_ssl": false into "I prefer to
disable SSL for better compatibility").
NOTE: Only output the valid JSON array. Do not include any commentary
or extra text.
"""

EXTRACT_START_CHAT_PREFERENCE = """
You are an intelligent analysis agent.

You are given:
- `start_message`: the first message in a conversation between a user
  and an AI assistant, in the format `[role]: [message]`
- `chat_session`: the full conversation that follows, with
  `start_message` being the first entry

Your task is to determine whether the user's `start_message` contains a
**genuine preference**, and if so, extract it in clear, first-person
natural language.

---

Follow these reasoning steps:
1. Analyze the content of `start_message`:
   - Does it express a **specific condition, constraint, or requirement**?
     (e.g., "with a gym", "before 8 AM", "quiet area")
   - Does it reveal a **habit, value, or personal bias**? (e.g., mentions
     of routines, likes/dislikes, lifestyle expectations)
   - Or is it simply a **task request or general query** with no
     identifiable preference? (e.g., "help me book a hotel", "what's
     the weather")
2. Classify the message into one of the following types:
   - `"explicit"` — if the user clearly states a preference using strong
     intent phrases (e.g., "I want", "please make sure", "I prefer",
     "it must include")
   - `"implicit"` — if the preference is implied through phrasing,
     context, or scenario (e.g., "book a hotel near a gym" → implies
     valuing fitness access)
   - `"irrelevant"` — if the message contains no actionable preference
     or is too general/vague (e.g., greetings, small talk, broad
     questions)
3. Summarize the preference (if any) using natural first-person
   language, such as:
   - "I prefer…"
   - "I want…"
   - "I value…"
   - "I apparently care about…"

---

Use both `start_message` and `chat_session` to inform your judgment.
---

Return your output in the following exact JSON format:
```json
{
  "type": "explicit" | "implicit" | "irrelevant",
  "user_preference": "..."  // Use "null" if type is "irrelevant"
}
If no actionable preference is identified, your response should be:
```json
{
  "type": "irrelevant",
  "user_preference": "null"
}
Important constraints:
   -You must output only one preference (at most).
   -If multiple interpretations exist, choose the dominant and most
    justified one.
   -If no meaningful preference is found, set type to "irrelevant" and
    user_preference to "null".
   -Use first-person voice for all non-null preferences.
   -Use generalized language to avoid low-level field names (e.g.,
    "allow_ssl": false → "I prefer to disable SSL for compatibility").
   -Do not include any additional text, explanations, or comments
    outside the JSON object.
"""

EXTRACT_BREAK_CHAT_PREFERENCE = """
You are an intelligent analysis agent.

You are given the following:
- `break_message`: the message from a user in a conversation that
  **interrupts the conversation flow**, in the format `[role]: [message]`
- `chat_session`: the full dialogue history between the user and an AI
  assistant, with `break_message` in the middle

Your task is to determine whether the `break_message` reveals a
**genuine user preference**, based on its content and the context
provided by the full `chat_session`. If a preference exists, extract it
in clear, first-person natural language.

---
Please follow these reasoning steps:
1. Analyze the `break_message` in context:
   - Does it express a **specific constraint, condition, value, or
     expectation**? (e.g., "with a gym", "only after sunset", "in a
     walkable neighborhood")
   - Does it reveal a **habit, dislike, or lifestyle clue**? (e.g., "I'm
     not a morning person", "I always travel light")
   - Or is it just a **task switch, casual comment, or unrelated
     input**?
2. Classify the preference as:
   - `"explicit"` — If the user **clearly expresses** a requirement or
     strong intent using words like "must", "I prefer", "please make
     sure", "it's important that…"
   - `"implicit"` — If the preference is **implied** by phrasing or
     context (e.g., "book a hotel near a gym" → user values fitness
     access)
   - `"irrelevant"` — If the message contains no actionable or meaningful
     preference (e.g., "lol that's funny", "btw hi", "what's next?")
3. Extract and summarize the most meaningful preference (if any) in
   **first-person language**, such as:
   - "I prefer…"
   - "I want…"
   - "I value…"
   - "I apparently care about…"
---

Use both `break_message` and `chat_session` to inform your judgment.
---

Return your output in the following exact JSON format:
```json
{
  "type": "explicit" | "implicit" | "irrelevant",
  "user_preference": "..."  // Use "null" if type is "irrelevant"
}
If no actionable preference is identified, your response should be:
```json
{
  "type": "irrelevant",
  "user_preference": "null"
}
Important constraints:
   -You must output only one preference (at most).
   -If multiple interpretations exist, choose the dominant and most
    justified one.
   -If no meaningful preference is found, set type to "irrelevant" and
    user_preference to "null".
   -Use first-person voice for all non-null preferences.
   -Use generalized language to avoid low-level field names (e.g.,
    "allow_ssl": false → "I prefer to disable SSL for compatibility").
   -Do not include any additional text, explanations, or comments
    outside the JSON object.
"""

EXTRACT_FOLLOWUP_CHAT_PREFERENCE = """
You are an intelligent analysis agent.

You are given the following:
- `followup_message`: the message from the user that starts a **new topic
  or turn**, occurring after a completed task or interaction within the
  session, in the format `[role]: [message]`
- `chat_session`: the full dialogue history between a user and an AI
  assistant, with `followup_message` in the middle

Your task is to determine whether this `followup_message` reflects a
**genuine user preference**, based on both its content and the context
provided by the prior conversation (`chat_session`). If a preference
exists, extract it in clear, first-person natural language.

---

Follow these reasoning steps:
1. Understand the `followup_message` in the context of `chat_session`:
   - Does it express a **specific condition, constraint, value, or
     goal**? (e.g., "with a gym", "before 8 AM", "in a quiet place")
   - Does it suggest a **habit, interest, expectation, or lifestyle
     clue**? (e.g., "I usually wake up late", "I love outdoor
     activities")
   - Or is it simply a **new request or casual input** with no embedded
     preference? (e.g., "can you help me with something?", "what's
     next?", "hi")
2. Classify the message into one of the following types:
   - `"explicit"` — The user **clearly states** a requirement or
     preference using strong intent phrases (e.g., "I want…", "please
     make sure…", "I'd like to…")
   - `"implicit"` — The message **implies** a preference based on its
     phrasing, context, or situation (e.g., "find something near a gym"
     → values fitness access)
   - `"irrelevant"` — The message contains **no meaningful preference**,
     and is vague, off-topic, or conversational (e.g., "hello", "what
     else can you do?", "lol")
3. If a preference is identified, summarize it in **first-person natural
   language**, such as:
   - "I prefer…"
   - "I want…"
   - "I value…"
   - "I apparently care about…"
---

Use both `followup_message` and `chat_session` to inform your judgment.

Return your output in the exact JSON format below:
```json
{
  "type": "explicit" | "implicit" | "irrelevant",
  "user_preference": "..."  // Use "null" if type is "irrelevant"
}
If no actionable preference is identified, your response must be:
```json
{
  "type": "irrelevant",
  "user_preference": "null"
}

Important constraints:
   -You must output only one preference (at most).
   -If multiple interpretations exist, choose the dominant and
    best-supported one.
   -If no meaningful preference is found, set type to "irrelevant" and
    user_preference to "null".
   -Use first-person voice for all non-null preferences.
   -Generalize low-level field names or system-specific options (e.g.,
    "timeout_ms": 3000 → "I prefer shorter wait times", "retry_count":
    0 → "I prefer not to retry failed requests").
   -Do not include any additional text, explanations, or comments
    outside the JSON object.
"""

GET_MEMORY_TYPE = """
You are an intelligent memory classification agent tasked with
organizing input content into one of the following memory categories,
based on its purpose, structure, and semantics. Classify the given input
strictly according to the detailed descriptions below. Return only the
memory category name as your output (e.g., "Procedural Memory").

Memory Categories and Definitions:
1. Core Memory:
Maintains essential user information including identity, personality
traits, and fundamental details necessary for effective user
communication. Core memory is organized into distinct blocks:
- Human Block: Contains user-specific information and preferences
- Persona Block: Defines your personality and communication style as
  the Chat Agent. All messages sent via `send_message` must align with
  the personality characteristics defined in this block.
2. Episodic Memory:
Maintains chronologically-ordered, event-based records of
user-assistant interactions, serving as the comprehensive interaction
history.
3. Procedural Memory:
Archives structured step-by-step processes, operational procedures, and
instructional guidelines.
4. Resource Memory:
Stores documents, files, and reference materials associated with active
tasks and ongoing projects.
5. Knowledge Vault:
Repository for structured, factual data including contact information,
credentials, and domain-specific knowledge that may be referenced in
future interactions.
6. Semantic Memory:
Contains conceptual knowledge about entities, concepts, and objects,
including detailed understanding and contextual information.

Instructions:
Given an input block of text, analyze its content and determine the most
appropriate memory category that best represents its purpose. Output
only the name of the memory category from the list above.
"""

EXTRACT_USER_INFO = """
You are given a piece of text content that may include information about
a user. Your task is to extract all explicit personal information about
the user from the content.
Personal information includes but is not limited to name, gender, age,
nationality, ethnicity, place of origin, occupation, or other
demographic details.
Do NOT include preferences, opinions, or inferred information.
Only extract facts that are clearly stated in the text.

Output the result as a Python-style list of sentences. Each sentence
should be a complete statement, for example:
["The user's name is Alice", "Alice is female", "Alice is 25 years
old", "User is from Canada"]

If no personal information is found, output an empty list: []

There are some examples:
Content 1: "Please help me book a hotel for celebrating my 18th
birthday."
Output: ["The user is 18 years old"]

Content 2: "I need to prepare slides for my students tomorrow.
Output: ["Is a student"]"

Content 3: "Can you recommend some good restaurants in Paris? I will
be there next week.
Output: ["The user will be in Paris next week"]

Content 4: "I am pregnant and need to find a hospital nearby."
Output: ["User is female and pregnant"]

Content 5: "I miss my hometown in Sichuan so much."
Output: ["From Sichuan"]

Content 6: "I have a surgery scheduled for my patient tomorrow morning."
Output: ["Is a doctor"]

Content 7: "I love pizza and movies."
Output: []

Content 8: "I am native american and live in oklahoma."
Output: ["User is native american and from Oklahoma"]

Ok! Let's get started!
"""

EXTRACT_USER_EVENT = """
You are given a piece of text content that may include information about
events related to the user.
Your task is to extract all explicit event information about the user
from the content.

An event should include any of the following elements if available:
- When (time, date, period)
- Where (location, place, setting)
- What happened or what the user did (action, activity, participation)
- Other relevant factual details (e.g., participants, results)

Do NOT infer or guess missing details — only extract facts that are
explicitly stated.
If a time or place is not mentioned, still extract the rest of the event
if it is clearly described.

Output the result as a Python-style list of sentences.
Each sentence should be a complete factual statement about the event,
for example:
["The user attended a conference in Beijing in May 2023",
 "The user had a meeting with their team yesterday",
 "The user will travel to Paris next week"]

If no event information is found, output an empty list: []

Here are some examples:
Content 1: "I attended the AI conference in Shanghai last week."
Output: ["The user attended the AI conference in Shanghai last week"]

Content 2: "Tomorrow I have a job interview."
Output: ["The user has a job interview tomorrow"]

Content 3: "We won the basketball match yesterday evening."
Output: ["The user won a basketball match yesterday evening"]

Content 4: "Can you recommend a good place to eat?"
Output: []

Content 5: "I will join a hackathon in San Francisco next month."
Output: ["The user will join a hackathon in San Francisco next month"]

Content 6: "Last year I traveled to Japan with my family."
Output: ["The user traveled to Japan with their family last year"]

Ok! Let's get started!
"""
