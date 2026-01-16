# -*- coding: utf-8 -*-
# pylint: skip-file
"""Example of training a ReAct agent on learn-to-ask with Trinity-RFT."""
import os
import re
import time
from typing import Dict, List, Union

from agentscope.tuner import (
    tune,
    DatasetConfig,
    WorkflowOutput,
    JudgeOutput,
    TunerModelConfig,
)
from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter
from agentscope.message import Msg
from agentscope.tuner import AlgorithmConfig
from agentscope.memory import InMemoryMemory
from agentscope.model import OpenAIChatModel


AUXILIARY_MODEL_NAME = "auxiliary_model"
TRAIN_MODE = "Ra+Rs"
FUSION_MODE = "default"


def format_messages(
    task_desc: Union[List, str],
) -> List[Dict[str, str]]:
    """Format messages for the instruct model."""
    if isinstance(task_desc, list):
        messages = task_desc
    elif isinstance(task_desc, str):
        messages = [
            {"role": "user", "content": task_desc},
        ]
    else:
        raise ValueError("`task_desc` must be a list or a string")
    return messages


async def run_react_agent(
    task: Dict,
    model: OpenAIChatModel,
    auxiliary_models: Dict[str, OpenAIChatModel],
) -> WorkflowOutput:
    """A simple workflow function using the ReAct agent to solve tasks.

    Args:
        task (Dict): The task to be solved.
        model (OpenAIChatModel): The language model to use.
        auxiliary_models (Dict[str, OpenAIChatModel]):
            A dictionary of additional chat models available for
            LLM-as-a-Judge. Exactly one auxiliary model must be provided.

    Returns:
        WorkflowOutput: The workflow output containing the agent's response.
    """
    assert (
        len(auxiliary_models) == 1
    ), "Please provide only one `auxiliary_models` for `learn_to_ask`."

    import importlib

    spec = importlib.util.spec_from_file_location(
        "prompt",
        os.path.join(os.path.dirname(__file__), "prompt.py"),
    )
    module = importlib.util.module_from_spec(spec)  # type: ignore
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


def parse_tag_string(text: str) -> Dict:
    pattern = r"<(\w+)>(.*?)</\1>"
    matches = re.findall(pattern, text)
    result = {}
    for tag, value in matches:
        result[tag] = value
    return result


def merge_msg_list(msg_list: List) -> str:
    result_str = ""
    for msg in msg_list:
        if msg["role"] == "user":
            result_str += f"patient: {msg['content']}\n"
        if msg["role"] == "assistant":
            result_str += f"doctor: {msg['content']}\n"
    return result_str


async def llm_reward(
    task: Dict,
    response: str,
    auxiliary_models: Dict[str, OpenAIChatModel],
) -> Dict:
    from agentscope import logger
    import importlib

    spec = importlib.util.spec_from_file_location(
        "prompt",
        os.path.join(os.path.dirname(__file__), "prompt.py"),
    )
    module = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(module)
    reward_prompt = module.reward_prompt_med

    task_desc = task["messages"]
    info_truth = task["info_truth"] if "info_truth" in task else "None"

    history = merge_msg_list(
        task_desc + [{"role": "assistant", "content": response}],
    )
    messages = [
        {"role": "system", "content": reward_prompt.format(info_truth)},
        {"role": "user", "content": history},
    ]

    try_count, max_retries = 0, 5
    while try_count <= max_retries:
        try:
            client = auxiliary_models[AUXILIARY_MODEL_NAME]
            res = await client(messages)
            msg = Msg(
                name="assistant",
                content=list(res.content),
                role="assistant",
            )
            content = msg.get_text_content()
            score_dict = parse_tag_string(content)
            return score_dict
        except Exception as e:
            try_count += 1
            if try_count > max_retries:
                logger.warning("retried too many times, abort task.")
                return {}
            else:
                logger.warning(
                    f"error: {e}, response:{response}, retries: {try_count}",
                )
            time.sleep(try_count * 1)
    return {}


async def learn2ask_judge(
    task: Dict,
    response: Msg,
    auxiliary_models: Dict[str, OpenAIChatModel],
) -> JudgeOutput:
    """A simple judge function to calculate reward based on agent's response.

    Args:
        task (Dict): The task information for the corresponding workflow.
        response (Msg): The response generated by the corresponding workflow.
        auxiliary_models (Dict[str, OpenAIChatModel]):
            A dictionary of additional chat models available for LLM-as-a-Judge
            usage. The keys are model names, and the values are the
            corresponding OpenAIChatModel instances.

    Returns:
        JudgeOutput: The reward value assigned by the judge function.
    """
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
                auxiliary_models=auxiliary_models,
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


if __name__ == "__main__":
    config_path = os.path.join(
        os.path.dirname(__file__),
        "config.yaml",
    )
    dataset = DatasetConfig(
        path=os.path.join(os.path.dirname(__file__), "data"),
        split="train",
        total_epochs=4,
    )
    tuner_model = TunerModelConfig(
        model_path="Qwen/Qwen2.5-7B-Instruct",
        max_model_len=8192,
        max_tokens=1024,
        temperature=1.0,
        tensor_parallel_size=1,
        inference_engine_num=4,
        reasoning_parser=None,
    )
    aux_models = {
        AUXILIARY_MODEL_NAME: TunerModelConfig(
            model_path="Qwen/Qwen2.5-32B-Instruct",
            max_model_len=8192,
            max_tokens=1024,
            temperature=0.7,
            tensor_parallel_size=2,
            inference_engine_num=1,
            reasoning_parser=None,
        ),
    }
    algorithm = AlgorithmConfig(
        algorithm_type="grpo",
        group_size=5,
        learning_rate=5.0e-07,
        batch_size=64,
    )
    tune(
        workflow_func=run_react_agent,
        judge_func=learn2ask_judge,
        train_dataset=dataset,
        model=tuner_model,
        auxiliary_models=aux_models,
        algorithm=algorithm,
        config_path=config_path,
    )
