# -*- coding: utf-8 -*-
import difflib
import logging
import traceback

import git
from fastapi import APIRouter, Body, HTTPException

watcher_router = APIRouter()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_git_user(repo):
    repo.config_writer().set_value("user", "name", "User").release()
    repo.config_writer().set_value(
        "user",
        "email",
        "user@example.com",
    ).release()
    return repo


@watcher_router.post(
    "/watcher/commit_changes",
    summary="...",
)
async def commit_changes(
    commit_message: str = Body(
        "Automated commit",
        example="Your commit message",
        embed=True,
    ),
):
    """
    Commit the uncommitted changes.
    """
    try:
        repo_path = "."

        repo = git.Repo(repo_path)
        repo = initialize_git_user(repo)

        # Add all changes to the staging area
        repo.git.add(A=True)

        # Commit the changes
        commit = repo.index.commit(commit_message)
        return {"commit": commit.hexsha, "message": commit_message}

    except Exception as e:
        logger.error(f"{str(e)}:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"{str(e)}: {traceback.format_exc()}",
        ) from e


@watcher_router.post(
    "/watcher/generate_diff",
    summary="...",
)
async def generate_diff(
    commit_a: str = Body(..., embed=True),
    commit_b: str = Body(..., embed=True),
):
    """
    Generate the diff of the uncommitted changes or two commits.
    """
    try:
        repo_path = "."
        repo = git.Repo(repo_path)
        repo = initialize_git_user(repo)

        if not commit_a and not commit_b:
            # Default to uncommitted changes compared to the last commit
            repo.git.add(A=True)
            diff_index = repo.index.diff("HEAD")
            print(diff_index, repo.git.status())
        elif commit_a and commit_b:
            # Get diff between two commits
            diff_index = repo.commit(commit_a).diff(commit_b)
        else:
            return HTTPException(
                detail="Invalid commit range",
                status_code=400,
            )
        diffs = {}
        for diff in diff_index:
            if diff.a_blob and diff.b_blob:
                # Both files are present in commits; perform a diff
                a_content = (
                    diff.a_blob.data_stream.read()
                    .decode(
                        "utf-8",
                    )
                    .splitlines()
                )
                b_content = (
                    diff.b_blob.data_stream.read()
                    .decode(
                        "utf-8",
                    )
                    .splitlines()
                )
            elif diff.a_blob:  # File was deleted
                # Only 'a' file is present; 'b' file is empty
                a_content = (
                    diff.a_blob.data_stream.read()
                    .decode(
                        "utf-8",
                    )
                    .splitlines()
                )
                b_content = []
            elif diff.b_blob:  # File was added
                # Only 'b' file is present; 'a' file is empty
                a_content = []
                b_content = (
                    diff.b_blob.data_stream.read()
                    .decode(
                        "utf-8",
                    )
                    .splitlines()
                )
            else:
                continue

            # Generate the diff content
            diff_text = "\n".join(
                difflib.unified_diff(
                    a_content,
                    b_content,
                    fromfile=f"a/{diff.a_path}",
                    tofile=f"b/{diff.b_path}",
                    lineterm="",
                ),
            )
            diffs[diff.b_path or diff.a_path] = diff_text
        return {"diffs": diffs}

    except Exception as e:
        logger.error(f"{str(e)}:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"{str(e)}: {traceback.format_exc()}",
        ) from e


@watcher_router.get(
    "/watcher/git_logs",
    summary="...",
)
async def git_logs():
    """
    Return the git logs.
    """
    try:
        repo = git.Repo(".")
        repo = initialize_git_user(repo)
        logs = []
        for commit in repo.iter_commits():
            diff_result = {"diffs": {}}
            if commit.parents:
                parent_commit = commit.parents[0]
                diff_result = await generate_diff(
                    commit.hexsha,
                    parent_commit.hexsha,
                )

            log_entry = {
                "commit": commit.hexsha,
                "author": commit.author.name,
                "date": commit.committed_datetime.isoformat(),
                "message": commit.message.strip(),
                "diff": diff_result["diffs"],
            }
            logs.append(log_entry)
        return {"logs": logs}
    except Exception as e:
        logger.error(f"{str(e)}:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"{str(e)}: {traceback.format_exc()}",
        ) from e
