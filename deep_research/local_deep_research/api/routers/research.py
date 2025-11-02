# -*- coding: utf-8 -*-
"""Research query API routes."""
import glob
import os

from agentscope.message import Msg
from fastapi import APIRouter, HTTPException

from local_deep_research.agent import LocalDeepResearchAgent
from local_deep_research.utils import log

from ..config import settings
from ..dependencies import create_agent
from ..models import ErrorResponse, ResearchRequest, ResearchResponse

router = APIRouter(prefix="/research", tags=["research"])


@router.post(
    "/query",
    response_model=ResearchResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Perform research query",
    description="Submit a research query to the LocalDeepResearchAgent",
)
async def research_query(request: ResearchRequest) -> ResearchResponse:
    """Perform a research query using LocalDeepResearchAgent.

    Args:
        request (ResearchRequest): Research query request.

    Returns:
        ResearchResponse: Research result.

    Raises:
        HTTPException: If query fails.
    """
    try:
        # Validate query
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        log.info(f"Received research query: {request.query[:100]}...")

        # Create agent with optional overrides
        agent: LocalDeepResearchAgent = create_agent(
            max_iters=request.max_iters,
            max_depth=request.max_depth,
        )

        # Create user message
        user_msg = Msg(
            name="User",
            content=request.query,
            role="user",
        )

        # Execute query
        log.info("Executing research query...")
        result_msg = await agent(user_msg)

        # Extract result content
        if isinstance(result_msg.content, str):
            result_content = result_msg.content
        elif isinstance(result_msg.content, list):
            # Handle list of content blocks
            result_content = "\n\n".join(
                str(block.get("text", block)) if isinstance(block, dict) else str(block)
                for block in result_msg.content
            )
        else:
            result_content = str(result_msg.content)

        # Find the generated detailed report
        report_pattern = os.path.join(
            settings.tmp_file_storage_dir,
            f"{agent.name}*_detailed_report.md",
        )
        report_files = glob.glob(report_pattern)
        report_path = report_files[0] if report_files else None

        log.info(f"Research query completed. Report: {report_path}")

        return ResearchResponse(
            query=request.query,
            result=result_content,
            agent_name=agent.name,
            report_path=report_path,
            status="success",
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Research query failed: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
