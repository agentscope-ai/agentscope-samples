from pydantic import BaseModel, Field

class SubtasksDecomposition(BaseModel):
    """
    Model for structured subtask decomposition output in deep research.
    """

    knowledge_gaps: str = Field(
        description=(
            "A markdown checklist of essential knowledge gaps and optional "
            "perspective-expansion gaps (flagged with (EXPANSION)), each on its own line. "
            "E.g. '- [ ] Detailed analysis of JD.com's ...\\n- [ ] (EXPANSION) X...'."
        ),
    )
    working_plan: str = Field(
        description=(
            "A logically ordered step-by-step working plan (3-5 steps), "
            "each step starting with its number (1., 2., etc), including both "
            "core and expansion steps. Expanded steps should be clearly marked "
            "with (EXPANSION) and provide contextual or analytical depth.."
        ),
    )

class WebExtraction(BaseModel):
    """
    Model for structured follow-up web extraction output in deep research.
    """

    reasoning: str = Field(
        description=(
            "The reasoning for your decision, including a summary of "
            "evidence and logic for whether more information is needed."
        ),
    )
    need_extraction: bool = Field(
        description="Whether more information is to be extracted.",
    )
    url: str = Field(
        description=(
            "Direct URL to the original search result requiring further "
            "extraction, or an empty string if not applicable."
        ),
    )

class FollowupJudge(BaseModel):
    """
    Model for structured follow-up decompose judging output in deep research.
    """

    reasoning: str = Field(
        description=(
            "The reasoning for your decision, including a summary of evidence "
            "and logic for whether more information is needed. You should "
            "include specific gaps or opportunities if the current "
            "information is still insufficient"
        ),
    )
    knowledge_gap_revision: str = Field(
        "Revise the knowledge gaps in the current. "
        "Mark the gaps with sufficient information as [x]."
    )
    to_further_explore: bool = Field(
        description=(
            "whether the information content is adequate "
            "or need to further explore (as `subtask`)."
        ),
    )
    subtask: str = Field(
        description=(
            "Actionable description of the follow-up task to obtain needed "
            "information, focused research question/direction, "
            "or an empty string if not applicable."
        ),
    )


class ReflectFailure(BaseModel):
    """
    Model for structured failure reflection output in deep research.
    """

    rephrase_subtask: dict = Field(
        description=(
            "Information about whether the problematic subtask needs to be "
            "rephrased due to a design flaw or misunderstanding. If rephrasing "
            "is needed, provide the modified working plan with only the inappropriate "
            "subtask replaced by its improved version."
        ),
        json_schema_extra={
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "need_rephrase": {
                        "type": "boolean",
                        "description": "Set to 'true' if the failed subtask "
                                       "needs to be rephrased due to a design "
                                       "flaw or misunderstanding; otherwise, 'false'.",
                    },
                    "rephrased_plan": {
                        "type": "string",
                        "description": "The modified working plan with only the inappropriate "
                                       "subtask replaced by its improved version. If no "
                                       "rephrasing is needed, provide an empty string.",
                    },
                }
            }
        }
    )
    decompose_subtask: dict = Field(
        description=(
            "Information about whether the problematic subtask should be further "
            "decomposed. If decomposition is required, provide the failed subtask "
            "and the reason for its decomposition."
        ),
        json_schema_extra={
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "need_decompose": {
                        "type": "boolean",
                        "description": "Set to 'true' if the failed subtask should "
                                       "be further decomposed; otherwise, 'false'.",
                    },
                    "failed_subtask": {
                        "type": "string",
                        "description": "The failed subtask that needs to be further "
                                        "decomposed.",
                    },
                }
            }
        }
    )
