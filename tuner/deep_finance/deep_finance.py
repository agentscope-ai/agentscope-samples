from ajet import AjetTuner, Workflow, WorkflowOutput, WorkflowTask
from agentscope.message import Msg 
from pydantic import Field
import logging
import threading
import time
import copy
from loguru import logger


# 创建信号量，允许同时12个线程运行
sem = threading.Semaphore(30)

class ExampleDeepResearchProtocol(Workflow):


    async def execute(
        self, workflow_task: WorkflowTask, tuner: AjetTuner  
    ) -> WorkflowOutput:
        from agentscope.agent import ReActAgent
        from agentscope.formatter import DashScopeChatFormatter
        from agentscope.memory import InMemoryMemory
        # 1. 初始化消息
        # init_messages 通常是 [System, User]
        init_messages = workflow_task.task.init_messages
        
        # 分离 System Prompt 和 Initial User Input
        if len(init_messages) >= 2:
            first_msg, user_msgs = init_messages[0], init_messages[1:]
        else:
            first_msg = {"content": "You're a helpful assistant."}
            user_msgs = init_messages

        # conversation_history: 维护最原始、最标准的 OpenAI 格式数据 (含 role: tool)
        # 这是"真值"，用于评测和训练保存
        conversation_history = [
            {"role": "system", "content": first_msg["content"]},
        ]
        conversation_history.extend(user_msgs)

        # 2. 初始化 Agent
        agent = ReActAgent(
            name="Qwen",
            sys_prompt=first_msg["content"], # Agent 内部会自动管理 System Prompt
            model=tuner.as_agentscope_model(),
            formatter=DashScopeChatFormatter(),
            memory=InMemoryMemory(),
            toolkit=None,
            print_hint_msg=False,
        )
        agent.set_console_output_enabled(False)
        env = workflow_task.gym_env
        
        # 3. 构造初始 Agent 输入 (List[Msg])
        # 注意：这里只包含 User 消息，不含 System，因为 System 已在 agent init 中设置
        # 必须转换为 Msg 对象
        agent_input = []
        for m in user_msgs:
            agent_input.append(Msg(
                name=m.get("name", "user"),
                content=m.get("content", ""),
                role=m.get("role", "user")
            ))

        # 统计信息缓存
        latest_tool_stats = None
        latest_reward_stats = {}
        cumulative_tool_call_time = 0.0  # 累计工具调用时间
        cumulative_tool_time = {}  # 按工具区分的累计耗时: {tool_name: [time1, time2, ...]}
        step = 0
        for step in range(tuner.config.ajet.rollout.multi_turn.max_steps):
            
            # === Agent 推理 ===
            _llm_start = time.time()
            # 传入增量消息 (agent_input)，Agent 会将其添加到内存并生成回复
            reply_message = await agent(agent_input)
            _llm_elapsed = time.time() - _llm_start
            # 提取纯文本 content（兼容多模态格式）
            if isinstance(reply_message.content, list):
                # 多模态格式: [{'type': 'text', 'text': '...'}]
                content_text = ''.join(item.get('text', '') for item in reply_message.content if isinstance(item, dict) and item.get('type') == 'text')
            else:
                content_text = reply_message.content
            
            content_preview = content_text[:100].replace('\n', ' ')
            
            # === 早期终止检查：在调用 env.step() 前检查 context_overflow ===
            # 修复问题：避免 token_overflow 后还继续调用工具导致阻塞
            if tuner.get_context_tracker().context_overflow:
                logger.warning(f"上下文溢出，跳过 env.step()，在第 {step + 1} 步立即结束")
                # 构造一个默认的结束响应
                conversation_history.append({
                    "role": "assistant",
                    "content": content_text
                })
                break
            
            # === Env 执行 ===
            _env_start = time.time()
            with sem:
                obs, reward, terminate, info = env.step(
                    action={"content": content_text, "role": "assistant"}
                )
            _env_elapsed = time.time() - _env_start

            # === 3. 更新 conversation_history (Full History) ===
            # A. 添加 Assistant 消息 (补全 tool_calls)
            current_assistant_msg = {
                "role": "assistant",
                "content": content_text
            }
            if info and 'generated_tool_calls' in info and info['generated_tool_calls']:
                current_assistant_msg['tool_calls'] = info['generated_tool_calls']
            conversation_history.append(current_assistant_msg)

            # B. 添加 Tool 消息 (直接使用 obs)
            # 注意：obs 可能是 [tool_results_msgs] 套了一层，需要解包
            if isinstance(obs, list):
                actual_msgs = obs[0] if (len(obs) == 1 and isinstance(obs[0], list)) else obs
                conversation_history.extend(actual_msgs)
            else:
                conversation_history.append({"role": "user", "content": obs})

            # === 4. 更新统计信息 ===
            if info:
                if 'tool_stats' in info:
                    latest_tool_stats = info['tool_stats']
                    if latest_tool_stats.get('total_calls', 0) > 0:
                        logger.info(f"步骤 {step + 1} 工具统计: 调用={latest_tool_stats.get('total_calls', 0)}, "
                                    f"成功率={latest_tool_stats.get('success_rate', 0):.1f}%")
                if 'reward_stats' in info:
                    latest_reward_stats = info['reward_stats']
                    # 累加工具调用时间
                    step_tool_call_time = latest_reward_stats.get('tool_call_time', 0.0)
                    cumulative_tool_call_time += step_tool_call_time
                    # 累加按工具区分的耗时
                    step_tool_time = latest_reward_stats.get('tool_time', {})
                    for tool_name, time_list in step_tool_time.items():
                        if tool_name not in cumulative_tool_time:
                            cumulative_tool_time[tool_name] = []
                        if isinstance(time_list, list):
                            cumulative_tool_time[tool_name].extend(time_list)
            
            # === 5. 准备下一轮 Agent 输入 (Incremental) ===
            # 将 Env 返回的 obs 转换为 Msg 对象列表，供下一轮 agent() 调用
            # 关键：这里只放新的 obs，不要放完整的 history
            agent_input = []
            
            if isinstance(obs, list):
                # Standard Mode: obs 是 tool messages 列表
                # 注意：deep_finance_env.step 返回 {"state": [tool_results_msgs]} 套了一层列表
                # BaseGymEnv.step 直接透传，所以 obs = [tool_results_msgs]
                # 需要解包获取实际的消息列表
                actual_msgs = obs[0] if (len(obs) == 1 and isinstance(obs[0], list)) else obs
                
                # 按照 AgentScope 的 ContentBlock 格式转换消息
                # Agent.memory 会自动保存 assistant 的 tool_call 信息
                # 这里只需要传入 tool_result 消息即可
                for idx, m in enumerate(actual_msgs):
                    origin_role = m.get('role', 'user')
                    if origin_role == 'tool':
                        # 使用 ToolResultBlock 格式，作为 user 消息的 content
                        tool_result_block = {
                            "type": "tool_result",
                            "id": m.get('tool_call_id', ''),
                            "output": m.get('content', ''),
                            "name": m.get('name', '')
                        }
                        new_msg = Msg(
                            name="tool",
                            content=[tool_result_block],
                            role="user"
                        )
                        agent_input.append(new_msg)
                    else:
                        # 其他消息（如 user 提示）直接添加
                        content = m.get('content')
                        if content is None: content = ""
                        valid_role = origin_role if origin_role in ['user', 'assistant', 'system'] else 'user'
                        new_msg = Msg(
                            name=m.get('name', valid_role), 
                            content=content,
                            role=valid_role
                        )
                        agent_input.append(new_msg)
            else:
                # Legacy Mode
                agent_input.append(Msg(name="env", content=obs, role="user"))

            # === 6. 终止检查 ===
            if terminate:
                break
                
            if tuner.get_context_tracker().context_overflow:
                logger.warning(f"上下文溢出，在第 {step + 1} 步结束")
                break

        # === 结束处理 ===
        final_tool_stats = latest_tool_stats or {
            'total_calls': 0, 'total_errors': 0, 'success_calls': 0, 'success_rate': 0.0,
            'cache_hits': 0, 'cache_misses': 0
        }
        # 将累计的 tool_time 合并到 tool_stats 中
        final_tool_stats['tool_time'] = cumulative_tool_time
        final_tool_stats['tool_call_time'] = cumulative_tool_call_time
        
        logger.info(f"任务完成统计 (Task ID: {workflow_task.task.task_id}):")
        logger.info(f"  总步骤: {step + 1}")
        logger.info(f"  总调用: {final_tool_stats.get('total_calls', 0)}")
        logger.info(f"  成功率: {final_tool_stats.get('success_rate', 0):.2f}%")
        
        return WorkflowOutput(
            reward=None, 
            metadata={
                "total_step": step,
                "tool_success_rate": round(final_tool_stats.get('success_rate', 0.0), 2),
                "conversation_history": conversation_history, 
                "query": workflow_task.task.main_query,
                "task_id": workflow_task.task.task_id,
            },
            log_metrics={
                "tool_stats": final_tool_stats,
                "reward_stats": latest_reward_stats,
            }
        )