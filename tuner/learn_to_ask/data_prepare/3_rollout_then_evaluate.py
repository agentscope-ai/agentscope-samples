# -*- coding: utf-8 -*-
# pylint: skip-file
"""
This script is used to use VLLM to generate rollout samples from the converted
checkpoints.
"""

import argparse
import copy
import gc
import json
import math
import os
import re
import time
from typing import List

import torch
from transformers import Any, AutoTokenizer
from vllm import LLM, SamplingParams


def init_llm(model_path: str) -> tuple:
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    device_count = torch.cuda.device_count()
    print(f"device_count={device_count}")
    if device_count < 1:
        raise RuntimeError("No GPU available for multi-card inference.")
    print(f"Loading model from: {model_path}")
    llm = LLM(model=model_path, tensor_parallel_size=device_count)
    print("Model loaded successfully!")
    sampling_params = SamplingParams(
        temperature=1.0,
        top_p=0.95,
        max_tokens=512,
        repetition_penalty=1.2,
    )
    return llm, tokenizer, sampling_params


def rollout(
    llm: Any,
    tokenizer: Any,
    sampling_params: Any,
    input_file_path: str,
    output_file_path: str,
    rollout_repeat: int = 3,
) -> None:
    import importlib

    spec = importlib.util.spec_from_file_location(
        "prompt",
        os.path.join(os.path.dirname(__file__), "..", "prompt.py"),
    )
    module = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(module)
    rollout_prompt = module.rollout_prompt_med

    with open(input_file_path, "r", encoding="utf-8") as lines:
        sample_list = [json.loads(line.strip()) for line in lines]
    print(f"loaded samples: {len(sample_list)}")

    for index, sample in enumerate(sample_list):
        record = copy.deepcopy(sample)
        print(f"index: {index}, session_id: {sample['session_id']}")
        messages = [{"role": "system", "content": rollout_prompt}] + sample[
            "messages"
        ]

        # Some tokenizers (e.g., Qwen) support the `enable_thinking` argument,
        # but others do not. Try with the argument first, and fall back if
        # it is not accepted.
        try:
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )

        response_list = []
        for i in range(rollout_repeat):
            time_probe = time.perf_counter()
            outputs = llm.generate([prompt], sampling_params=sampling_params)
            print(f"time cost: {time.perf_counter() - time_probe}")
            for output in outputs:
                response = output.outputs[0].text
                response_list.append(response)
                print(f"rollout #{i}: {response}\n")
        record["rollouts"] = response_list

        # append to output file
        with open(output_file_path, "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def eval_sample(
    llm: Any,
    tokenizer: Any,
    sampling_params: Any,
    input_file_path: str,
    output_file_path: str,
) -> None:
    import importlib

    spec = importlib.util.spec_from_file_location(
        "prompt",
        os.path.join(os.path.dirname(__file__), "..", "prompt.py"),
    )
    module = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(module)
    grader_prompt = module.reward_prompt_med

    print(f"input_file_path: {input_file_path}")
    print(f"output_file_path: {output_file_path}")

    with open(input_file_path, "r", encoding="utf-8") as lines:
        sample_list = [json.loads(line.strip()) for line in lines]
    print(f"Total records: {len(sample_list)}")

    def res_formatter(res_content: str) -> dict:
        pattern = r"<(\w+)>(.*?)</\1>"
        matches = re.findall(pattern, res_content)
        result = {}
        for tag_name, content in matches:
            result[tag_name] = content
        return result

    def msg2str(msg_list: List) -> str:
        result_str = ""
        for msg in msg_list:
            if msg["role"] == "user":
                result_str += f"patient: {msg['content']}\n"
            if msg["role"] == "assistant":
                result_str += f"doctor: {msg['content']}\n"
        return result_str

    for index, sample in enumerate(sample_list):
        print(f"index: {index}, cid: {sample['cid']}")
        action_truth = sample["decision_truth"]
        info_truth = sample["info_truth"] if sample["info_truth"] else "None."
        print(f"action_truth: {action_truth}, info_truth:{info_truth}")

        sys_prompt = grader_prompt.format(info_truth)
        history = msg2str(sample["messages"])

        sample["grades"] = []
        for rollout in sample["rollouts"]:
            time_probe = time.perf_counter()
            action_score, content_score, format_score, res_think = (
                0,
                0,
                0,
                "NA",
            )
            if "<stop />" in rollout:
                action_rollout = "stop"
            else:
                action_rollout = "continue"
            if action_truth == action_rollout:
                action_score = 1
                if action_truth == "continue":
                    user_content = history + f"doctor: {rollout}"
                    messages = [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_content},
                    ]
                    try:
                        prompt = tokenizer.apply_chat_template(
                            messages,
                            tokenize=False,
                            add_generation_prompt=True,
                            enable_thinking=False,
                        )
                    except TypeError:
                        # Fallback for tokenizers that do not support the
                        # Qwen-specific `enable_thinking` argument.
                        prompt = tokenizer.apply_chat_template(
                            messages,
                            tokenize=False,
                            add_generation_prompt=True,
                        )
                    outputs = llm.generate(
                        [prompt],
                        sampling_params=sampling_params,
                    )
                    for output in outputs:
                        response = output.outputs[0].text
                        print(f"Response: {response}\n")
                    res_dict = res_formatter(response)
                    try:
                        format_score = float(res_dict.get("format_score", 0.0))
                        content_score = float(
                            res_dict.get("content_score", 0.0),
                        )
                        res_think = res_dict.get("think", "None")
                    except Exception as e:
                        print(e)
                else:
                    content_score = 1.0
                    format_score = 1.0 if rollout == "<stop />" else 0.0
            else:
                action_score, format_score, content_score = 0, 0, 0
            grade_result = {
                "think": res_think,
                "action_score": action_score,
                "format_score": format_score,
                "content_score": content_score,
            }
            sample["grades"].append(grade_result)
            json_str = json.dumps(grade_result, ensure_ascii=False, indent=2)
            print(
                f"grade_result:{json_str}",
            )
            print(f"time_cost:{time.perf_counter() - time_probe}")
        # append sample to output file
        with open(output_file_path, "a") as f:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
        print("\n======================\n")


def compute_score(input_file_path: str) -> None:
    with open(input_file_path, "r", encoding="utf-8") as lines:
        sample_list = [json.loads(line.strip()) for line in lines]
    continue_count, continue_content_score, continue_content_full = 0, 0, 0
    continue_decision_score = 0
    stop_count, stop_decision_score = 0, 0
    total_reward, total_format = 0, 0
    (
        continue_count_correct,
        continue_content_score_correct,
        continue_content_full_correct,
    ) = (0, 0, 0)
    for sample in sample_list:
        for rollout, grade in zip(sample["rollouts"], sample["grades"]):
            if math.isnan(grade["content_score"]) or math.isnan(
                grade["format_score"],
            ):
                continue
            if sample["decision_truth"] == "continue":
                continue_count += 1
                continue_content_score += grade["content_score"]
                continue_content_full += (
                    1 if grade["content_score"] == 1 else 0
                )
                continue_decision_score += grade["action_score"]
                if "<stop />" not in rollout:
                    continue_count_correct += 1
                    continue_content_score_correct += grade["content_score"]
                    continue_content_full_correct += (
                        1 if grade["content_score"] == 1 else 0
                    )

            else:
                stop_count += 1
                stop_decision_score += grade["action_score"]
            total_reward += (
                grade["action_score"] * (1 + 2 * grade["content_score"])
                + grade["format_score"]
            )
            total_format += grade["format_score"]

    result = {
        "ave_continue_content": continue_content_score
        / max(1, continue_count),
        "win_continue_content": continue_content_full / max(1, continue_count),
        "ave_continue_content if correct": continue_content_score_correct
        / max(1, continue_count_correct),
        "win_continue_content if correct": continue_content_full_correct
        / max(1, continue_count_correct),
        "ave_continue_decision": continue_decision_score
        / max(1, continue_count),
        "ave_stop_decision": stop_decision_score / max(1, stop_count),
        "ave_total_decision": (continue_decision_score + stop_decision_score)
        / max(1, continue_count + stop_count),
        "ave_total_format": total_format / max(1, continue_count + stop_count),
        "ave_total_reward": total_reward / max(1, continue_count + stop_count),
    }

    print(f"total count: {continue_count + stop_count}")
    print(json.dumps(result, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rollout_repeat", type=int, default=3)

    # Ckpt for testing
    parser.add_argument("--eval_model_path", type=str, required=True)

    # Model to empower the grading, Qwen2.5-32b-instruct is recommended
    parser.add_argument("--grader_model_path", type=str, required=True)

    # Your test sample path [input]
    parser.add_argument("--test_file_path", type=str, required=True)

    # Rollout results given test samples [output]
    parser.add_argument("--rollout_file_path", type=str, required=True)

    # Final output given rollout results [output]
    parser.add_argument("--eval_file_path", type=str, required=True)

    args = parser.parse_args()

    # rollout stage
    llm, tokenizer, sampling_params = init_llm(args.eval_model_path)
    rollout(
        llm,
        tokenizer,
        sampling_params,
        args.test_file_path,
        args.rollout_file_path,
        args.rollout_repeat,
    )
    del llm  # clean up the memory after the inference
    gc.collect()
    torch.cuda.empty_cache()  # release gpu memory

    # eval stage
    llm2, tokenizer2, sampling_params2 = init_llm(args.grader_model_path)
    eval_sample(
        llm2,
        tokenizer2,
        sampling_params2,
        args.rollout_file_path,
        args.eval_file_path,
    )
    compute_score(args.eval_file_path)
