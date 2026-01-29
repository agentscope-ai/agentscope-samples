GROUNDING_SYSTEM_PROMPT = """你是一位“引用审计员”，负责审计金融研究报告是否遵守引用规范，并输出用于训练的 JSON 结果（只输出 JSON）。

========================
一、引用规范（以此为准）
========================
1) 关键事实句必须引用：
   - 关键事实句包括：数字（金额/比例/增速/同比环比/份额/排名等）、日期/期间、财务指标、估值倍数、明确事实结论、具体事件、具体公司/行业的可验证陈述、政策/条款等。
   - 不确定或推断性表述必须显式写“推测/可能/假设/预计/或有风险”等，不得用引用把推断包装成既定事实。

2) 引用位置规则（严格执行）：
   - 关键事实句必须在“句末”出现引用编号：[1] 或 [1][2]（可以多个，但必须紧贴句末）。
   - 若引用出现在句中但句末没有引用编号，则该句仍按“缺引用（missing）”处理。

3) References 必须存在且可追溯：
   - 报告末尾必须包含标题 `## References`（大小写/空格差异可容忍，但必须是一个清晰的 References 区块）。
   - 正文出现的每个 [n] 必须能在 References 中找到对应条目。

4) References 条目两种合法形式（必须满足其一）：
   A) URL 形式：`[n] 标题或简述 - https://...`
      - URL 必须为可用的 http/https 链接，不能为空，也不能是 `javascript:void(0)` 之类的伪链接。
   B) no-url 形式：`[n] 简述，工具：<tool_name>，参数：<k=v; ...>，数据日期/报告期：<date> - (no-url)`
      - no-url 必须同时包含：工具名、参数、日期/报告期 三者（缺一即不合规）。
   - `javascript:void(0)` 等无效链接视为无效 URL（会进入 invalid_reference_nums），若要合规应改为 no-url 记录来源。

========================
二、输入
========================
你会收到：
- User Query
- Evidence（从完整 trajectory 提取的工具调用/工具返回/用户补充信息）
- AI Report（待审计报告，含正文与 References）

真实性核对原则：
- 以 Evidence 为准：只有在“明显矛盾”或“Evidence 明显找不到任何依据且该句仍把内容写成确定事实”时，才判 fake。
- 无法确认/证据缺失/证据不充分时，不要判 fake（宁可不判）。

========================
三、统计与判定口径（严格遵守）
========================
【文本范围】
- 只审计 AI Report 的“正文部分”（不包含 References 区块内部的文字）。
- References 区块仅用于校验编号是否存在、格式是否合规、URL 是否有效。

【句子/条目如何计数】
- “句子/条目”包括：普通句号/分号/换行分点（如列表项、段落中的 bullet）、表格中的单元格陈述（若表达了关键事实，也算关键事实句）。
- 一句包含多个数字/多个事实点：仍按 1 条关键事实句计数（不要过度拆分）。
- 同一句若重复出现多次（复制粘贴重复段落）：按出现次数计数。

【关键事实句识别（务求稳定）】
- 满足任一条件可视为关键事实句：
  (a) 含具体数值/比例/排名/区间/估值倍数/财务指标；
  (b) 含具体日期或期间（如 “2024Q3/2025年/截至XX日”）；
  (c) 对具体公司/行业/政策做了可验证的确定性陈述；
  (d) 给出明确结论且呈确定口吻并可被证据支持/反驳。

【引用是否“句末”】【重要】
- 句末引用指：该句最后的可见字符为一个或多个连续的 [n]（允许中间无空格或有极少空格），例如：
  - “……增长 20%[3]”
  - “……增长 20% [3][4]”
- 若 [n] 后面仍有正文内容（哪怕很短），则不算句末引用。

【invalid_reference_nums 的定义】
- 统计“正文中出现过”的编号 n（去重），若满足任一条件则判为 invalid：
  (a) References 中不存在该编号条目；
  (b) 该编号条目为 URL 形式但 URL 无效（空/非 http(s)/javascript:void(0) 等）；
  (c) 该编号条目为 no-url 形式但缺少 工具名/参数/日期(报告期) 任意之一。
- invalid_reference_nums 输出按数字升序；最多 5 个，超出截断。

【missing_count 的定义】
- 关键事实句中“句末没有任何 [n]”的数量（即使句中出现 [n] 也算 missing）。

【cited_key_facts 的定义】
- 关键事实句中“句末包含至少一个 [n]”的数量（不要求该引用有效）。

【fake_count 的定义（只在明显时计数）】
- 关键事实句若“句末带引用”，但与 Evidence 明显矛盾，或 Evidence 明显找不到任何依据且该句仍用确定口吻陈述为事实，计为 fake。
- 若只是 Evidence 未覆盖/不充分/不确定，不计 fake。

【good_citations 的定义】
- 从报告原文中抽取最多 2 条“引用做得正确”的关键事实句，要求同时满足：
  - 是关键事实句；
  - 句末有 [n]；
  - 所有句末 [n] 在 References 中均存在且条目合法（URL 有效或 no-url 字段齐全）。
- good_citations 是原文截取，不要加解释；最多 2 条，超出截断。

========================
四、输出（只输出 JSON，字段固定）
========================
{
  "total_key_facts": <int>,
  "cited_key_facts": <int>,
  "good_citations": ["...", "..."],
  "missing_count": <int>,
  "fake_count": <int>,
  "invalid_reference_nums": [<int>, ...]
}

只输出 JSON，不要输出解释文字或 Markdown。确保 JSON 可被严格解析（双引号、逗号、方括号等格式正确）。
"""



import json
import re
from typing import Dict, Any, List


def _extract_text_content(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                out.append(item.get("text", ""))
            elif isinstance(item, str):
                out.append(item)
        return "\n".join(out)
    return str(content)

def _strip_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.S).strip()

def _normalize_traj(trajectory):
    # 兼容 [[...]] :contentReference[oaicite:1]{index=1}
    if isinstance(trajectory, list) and trajectory and isinstance(trajectory[0], list):
        return trajectory[0]
    return trajectory

def _extract_tool_call_json(text: str) -> str:
    m = re.search(r"```json\s*(\[[\s\S]*?\])\s*```", text)
    if m:
        return m.group(1).strip()
    l, r = text.find("["), text.rfind("]")
    if l != -1 and r != -1 and r > l:
        cand = text[l:r+1].strip()
        if ("tool_name" in cand) and ("tool_args" in cand):
            return cand
    return ""

def _looks_like_tool_result(text: str) -> bool:
    t = text.strip()
    if t.startswith("Tool:") or t.startswith("Result:"):
        return True
    if t.startswith("{") and ("query" in t) and ("search_results" in t or "response_content" in t):
        return True
    if ("股票代码 |" in t) or ("单位：" in t) or t.startswith("### "):
        return True
    return False

def _is_probably_final_report(text: str) -> bool:
    t = text.strip()
    return ("## References" in t) or ("[TASK_COMPLETED]" in t) or t.lstrip().startswith("# ")

def construct_reward_prompt(trajectory: List[Dict[str, Any]]) -> str:
    traj = _normalize_traj(trajectory)

    user_query = ""
    tool_calls: List[str] = []
    evidence: List[str] = []
    final_report = ""

    # final report
    for i in range(len(traj) - 1, -1, -1):
        step = traj[i]
        if step.get("role") == "assistant":
            txt = _strip_think(_extract_text_content(step.get("content")))
            if _is_probably_final_report(txt):
                final_report = txt
                break
    if not final_report:
        for i in range(len(traj) - 1, -1, -1):
            if traj[i].get("role") == "assistant":
                final_report = _strip_think(_extract_text_content(traj[i].get("content")))
                break

    # iterate
    for idx, step in enumerate(traj):
        role = step.get("role")
        raw = _extract_text_content(step.get("content"))
        txt = _strip_think(raw)
        if not raw:
            continue

        if role == "user" and not user_query and (not _looks_like_tool_result(raw)):
            user_query = txt
            continue

        if role == "assistant":
            call_json = _extract_tool_call_json(raw)
            if call_json:
                tool_calls.append(f"[Step {idx}] TOOL_CALL:\n{call_json}")

        if role in ("tool", "user"):
            if _looks_like_tool_result(raw):
                evidence.append(f"[Step {idx}] EVIDENCE_TOOL_RESULT:\n{raw}")
            else:
                # query 之后的用户补充也保留为 evidence（有些系统会把 tool_result 注入到 user）
                if user_query:
                    evidence.append(f"[Step {idx}] EVIDENCE_USER_CONTEXT:\n{txt}")

    evidence_text = "\n\n".join(tool_calls + evidence)

    return f"""请审计以下 AI 研究报告的引用规范性，只输出 JSON。

### User Query
{user_query}

### Evidence（来自完整 trajectory）
{evidence_text}

### AI Report（待审计报告）
{final_report}
""".strip()


class RefJudgeEvaluator:
    """
    引用规范性评估器
    
    使用 LLM 评估报告的引用覆盖率和引用真实性。
    """
    
    def __init__(self, llm_client):
        """
        初始化评估器
        
        Args:
            llm_client: LLMJudgeClient 实例
        """
        self.llm_client = llm_client
        print("✓ RefJudgeEvaluator: Initialized")
    
    def build_messages(self, conversation_history: List[Dict]) -> List[Dict[str, str]]:
        """
        从对话历史构建 LLM 评估消息
        
        Args:
            conversation_history: 对话历史 [{"role": "...", "content": "..."}]
            
        Returns:
            LLM 消息列表
        """
        print(f"\n[RefJudgeEvaluator] 构建评估消息...")
        print(f"  - 对话历史轮数: {len(conversation_history)}")
        
        # 调用现有的 prompt 构建函数
        user_prompt = construct_reward_prompt(conversation_history)
        
        messages = [
            {"role": "system", "content": GROUNDING_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        print(f"  ✓ 消息构建完成，system prompt 长度: {len(GROUNDING_SYSTEM_PROMPT)}")
        print(f"  ✓ user prompt 长度: {len(user_prompt)}")
        
        return messages
    
    def _compute_scores(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据 LLM 返回的原始结果计算评分
        
        Args:
            raw_result: LLM 返回的 JSON，包含 total_key_facts, cited_key_facts, fake_count 等
            
        Returns:
            包含 citation_coverage_score, grounding_score, final_reward 的字典
        """
        total_key_facts = raw_result.get('total_key_facts', 0)
        cited_key_facts = raw_result.get('cited_key_facts', 0)
        fake_count = raw_result.get('fake_count', 0)

        # invalid refs: 结构化/可追溯性问题（来自 prompt 的 invalid_reference_nums）
        invalid_reference_nums = raw_result.get('invalid_reference_nums', [])
        if not isinstance(invalid_reference_nums, list):
            invalid_reference_nums = []
        invalid_ref_count = len(invalid_reference_nums)
        
        # 边界情况：没有关键事实，直接返回 0
        if total_key_facts == 0:
            citation_coverage_score = 0.0
            grounding_score = 0.0
        else:
            # coverage: 引用覆盖率
            citation_coverage_score = cited_key_facts / total_key_facts
            
            # grounding: 引用真实性（已引用中非虚假的比例）
            if cited_key_facts == 0:
                grounding_score = 0.0
            else:
                grounding_score = max(0.0, 1 - fake_count / cited_key_facts)
        
        # 轻量惩罚：存在 invalid refs 会降低 reward（但不改变 cited_key_facts 的统计口径）
        # 说明：invalid_reference_nums 在 prompt 中已定义为“正文出现过的不合规编号（去重）”。
        # 这里采用简单、确定性的惩罚：每个 invalid 号扣 0.1，最多扣 0.5。
        invalid_penalty = min(0.1 * invalid_ref_count, 0.5)

        # final_reward: 综合分数（代码计算，权重 0.5:0.5），再叠加 invalid 惩罚
        final_reward = 0.5 * citation_coverage_score + 0.5 * grounding_score
        final_reward = max(0.0, final_reward - invalid_penalty)
        
        return {
            'citation_coverage_score': citation_coverage_score,
            'grounding_score': grounding_score,
            'final_reward': final_reward,
            'invalid_ref_count': invalid_ref_count,
            'invalid_penalty': invalid_penalty,
        }
    
    async def evaluate_async(self, conversation_history: List[Dict]) -> Dict[str, Any]:
        """
        异步评估引用规范性
        
        Args:
            conversation_history: 对话历史
            
        Returns:
            评估结果字典，包含:
            - citation_coverage_score: 引用覆盖率分数 (0.0-1.0)
            - grounding_score: 引用真实性分数 (0.0-1.0)
            - final_reward: 最终奖励分数 (0.0-1.0)
            - total_key_facts, cited_key_facts, fake_count 等原始字段
        """
        # print(f"\n开始评估引用规范性...")
        
        messages = self.build_messages(conversation_history)
        raw_result = await self.llm_client.evaluate_async(messages)
        
        # 计算评分
        scores = self._compute_scores(raw_result)
        
        # 合并原始结果和计算的评分
        result = {**raw_result, **scores}
        
        # 确保必要字段存在
        result.setdefault('total_key_facts', 0)
        result.setdefault('cited_key_facts', 0)
        result.setdefault('missing_count', 0)
        result.setdefault('fake_count', 0)
        result.setdefault('invalid_reference_nums', [])
        result.setdefault('good_citations', [])
        
        print(f"  ✓ [RefJudgeEvaluator] 引用规范性评估完成:")
        print(f"    - total_key_facts: {result['total_key_facts']}")
        print(f"    - cited_key_facts: {result['cited_key_facts']}")
        print(f"    - fake_count: {result['fake_count']}")
        print(f"    - invalid_ref_count: {result.get('invalid_ref_count', 0)}")
        print(f"    - invalid_penalty: {result.get('invalid_penalty', 0.0):.4f}")
        print(f"    - citation_coverage_score: {result['citation_coverage_score']:.4f}")
        print(f"    - grounding_score: {result['grounding_score']:.4f}")
        print(f"    - final_reward: {result['final_reward']:.4f}")
        
        return result
    
    def evaluate_sync(self, conversation_history: List[Dict]) -> Dict[str, Any]:
        """
        同步评估引用规范性
        """
        import asyncio
        return asyncio.run(self.evaluate_async(conversation_history))
