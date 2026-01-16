# -*- coding: utf-8 -*-
# flake8: noqa: E501
# pylint: disable=C0301,C0413,W0621,W0404,C0412,E0611,E1121
"""Example of training a werewolf game agent with Trinity-RFT using AgentScope tuner."""
import sys
from pathlib import Path
from typing import Dict
import traceback

import numpy as np

from agentscope.tuner import (
    tune,
    WorkflowOutput,
    TunerModelConfig,
)
from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIMultiAgentFormatter

# Add current directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from game import BadGuyException, werewolves_game  # noqa: E402


async def run_werewolves_workflow(
    task: Dict,
    model: TunerModelConfig,
    auxiliary_models: Dict[str, TunerModelConfig],
) -> WorkflowOutput:
    """Run the werewolf game workflow.

    Args:
        task (Dict): The task information containing:
            - 'seed': for role shuffling
            - 'workflow_args': optional dict with 'trainable_target' key
              ("werewolf" or "good_guy", default: "werewolf")
        model (TunerModelConfig): The trainable model.
        auxiliary_models (Dict[str, TunerModelConfig]): Dictionary of auxiliary
            models. Expected to have 'participant' key for opponent players.

    Returns:
        WorkflowOutput: Contains reward and metrics from the game.
    """
    # Initialize roles: 2 werewolves, 3 villagers, 1 seer, 1 witch
    roles = ["werewolf"] * 2 + ["villager"] * 3 + ["seer", "witch"]

    # Shuffle roles based on task seed for reproducibility
    seed = task.get("seed", 0)
    np.random.seed(seed)
    np.random.shuffle(roles)

    # Get trainable_target from workflow_args (default: "werewolf")
    # Options: "werewolf" or "good_guy" (villager, seer, witch)
    workflow_args = task.get("workflow_args", {})
    trainable_target = workflow_args.get("trainable_target", "werewolf")

    # Get the participant model for opponent players
    if "participant" not in auxiliary_models:
        raise ValueError(
            "Expected 'participant' model in auxiliary_models for opponent players",
        )
    participant_model = auxiliary_models["participant"]

    # Create players with appropriate models based on trainable_target
    players = []
    for i, role in enumerate(roles):
        # Determine which model to use based on trainable_target
        if trainable_target == "werewolf":
            # Training werewolves: werewolves use trainable model
            use_trainable = role == "werewolf"
        else:  # trainable_target == "good_guy"
            # Training good guys: villager, seer, witch use trainable model
            use_trainable = role in ["villager", "seer", "witch"]

        agent = ReActAgent(
            name=f"Player{i + 1}",
            sys_prompt=get_official_agent_prompt(f"Player{i + 1}"),
            model=model if use_trainable else participant_model,
            formatter=OpenAIMultiAgentFormatter(),
            max_iters=3,
        )
        players.append(agent)

    try:
        # Run the werewolf game
        good_guy_win = await werewolves_game(players, roles)

        # Calculate reward based on trainable_target
        is_success = False
        if trainable_target == "werewolf":
            # Training werewolves: reward when werewolves win (good_guy_win = False)
            if not good_guy_win:
                raw_reward = 1.0
                is_success = True
            else:
                raw_reward = 0.0
        else:  # trainable_target == "good_guy"
            # Training good guys: reward when good guys win (good_guy_win = True)
            if good_guy_win:
                raw_reward = 1.0
                is_success = True
            else:
                raw_reward = 0.0

        metrics = {
            "success": float(is_success),
            "werewolf_win": float(not good_guy_win),
            "villager_win": float(good_guy_win),
            "trainable_target": trainable_target,
        }

        return WorkflowOutput(
            reward=raw_reward,
            metrics=metrics,
        )

    except BadGuyException as e:
        # If game execution fails, give a small penalty
        traceback.print_exc()
        print(
            f"Error during game execution: {e}. "
            "Assigning penalty to trainable agents.",
        )
        return WorkflowOutput(
            reward=-0.1,
            metrics={"success": 0.0, "game_error": 1.0},
        )
    except Exception as e:
        # Catch any other unexpected errors
        traceback.print_exc()
        print(f"Unexpected error: {e}")
        return WorkflowOutput(
            reward=-0.1,
            metrics={"success": 0.0, "unexpected_error": 1.0},
        )


def get_official_agent_prompt(name: str) -> str:
    """Get the system prompt for an agent.

    Args:
        name (str): The name of the agent.

    Returns:
        str: The system prompt.
    """
    from textwrap import dedent

    system_prompt = dedent(
        f"""
        You're a werewolf game player named {name}.

        # YOUR TARGET
        Your target is to win the game with your teammates as much as possible.

        # GAME RULES
        - In werewolf game, players are divided into two werewolves, three villagers, one seer, and one witch.
            - Werewolves: kill one player each night, and must hide identity during the day.
            - Villagers: ordinary players without special abilities, try to identify and eliminate werewolves.
                - Seer: A special villager who can check one player's identity each night.
                - Witch: A special villager with two one-time-use potions: a healing potion to save a player (including herself) from being killed at night, and a poison to eliminate one player at night.
        - The game alternates between night and day phases until one side wins:
            - Night Phase
                - Werewolves choose one victim
                - Seer checks one player's identity
                - Witch decides whether to use potions
                - Moderator announces who died during the night
            - Day Phase
                - All players discuss and vote to eliminate one suspected player

        - The werewolves will win the game if they can eliminate all the villagers.
        - The villagers will win the game if they can eliminate all the werewolves.

        ## During PUBLIC discussion (day phase):
        - Your response will be split into TWO parts: REASONING (private) and STATEMENT (public)
        - REASONING: Your internal thoughts - ONLY YOU can see this. Think freely here.
        - STATEMENT: What you actually say - EVERYONE can see this. Be strategic!

        ## For WEREWOLVES in public discussion:
        - ❌ NEVER say "I'm a werewolf" or "we werewolves" in your STATEMENT
        - ❌ NEVER reveal your werewolf teammates in your STATEMENT
        - ❌ NEVER discuss werewolf strategy in your STATEMENT
        - ✅ In REASONING: freely think about werewolf strategy
        - ✅ In STATEMENT: pretend to be a villager, seer, or other role
        - ✅ In STATEMENT: accuse others, defend yourself, but NEVER reveal your true identity

        ## For ALL ROLES in public discussion:
        - Use REASONING to analyze: "Who might be the werewolf? What's my strategy?"
        - Use STATEMENT to speak: "I think Player X is suspicious because..."
        - Keep sensitive information in REASONING, not in STATEMENT

        ## Examples:
        ### BAD (Werewolf exposing themselves):
        REASONING: "I'm a werewolf, I should protect my teammates."
        STATEMENT: "As a werewolf, I think we should vote Player 5."  ❌ EXPOSED!

        ### GOOD (Werewolf hiding identity):
        REASONING: "I'm a werewolf. Player 5 might be the seer based on their questions. I should cast suspicion on them without being obvious."
        STATEMENT: "I find Player 5's behavior suspicious. They've been asking too many questions about people's roles."  ✅ HIDDEN!

        ### GOOD (Villager analyzing):
        REASONING: "Player 2 and Player 3 seem to be defending each other. Could they be werewolf teammates?"
        STATEMENT: "I noticed Player 2 and Player 3 have been very defensive of each other. This makes me suspicious."  ✅ STRATEGIC!

        # GAME GUIDANCE
        - Try your best to win the game with your teammates, tricks, lies, and deception are all allowed, e.g. pretending to be a different role.
        - During discussion, don't be political, be direct and to the point.
        - The day phase voting provides important clues. For example, the werewolves may vote together, attack the seer, etc.

        ## GAME GUIDANCE FOR WEREWOLF
        - Seer is your greatest threat, who can check one player's identity each night. Analyze players' speeches, find out the seer and eliminate him/her will greatly increase your chances of winning.
        - In the first night, making random choices is common for werewolves since no information is available.
        - Pretending to be other roles (seer, witch or villager) is a common strategy to hide your identity and mislead other villagers in the day phase.
        - The outcome of the night phase provides important clues. For example, if witch uses the healing or poison potion, etc. Use this information to adjust your strategy.
        - [CRITICAL] In public discussion, NEVER reveal you are a werewolf. Always pretend to be a villager or other role.

        ## GAME GUIDANCE FOR SEER
        - Seer is very important to villagers, you should earn the villagers' trust, and lead the discussion phase if possible.
        - Your ability to check one player's identity is crucial.
        - The outcome of the night phase provides important clues. For example, if witch uses the healing or poison potion, etc. Use this information to adjust your strategy.
        - Consider when to reveal your identity - too early and werewolves will target you, too late and villagers won't trust you.

        ## GAME GUIDANCE FOR WITCH
        - Witch has two powerful potions, use them wisely to protect key villagers or eliminate suspected werewolves.
        - [IMPORTANT] You CAN use the healing potion to save yourself if you are killed by werewolves (self-rescue is allowed).
        - Consider saving the healing potion for critical moments, especially if you think you might be targeted.
        - The outcome of the night phase provides important clues. Use this information to adjust your strategy. For example, the person you save is likely to be on the villagers' side.

        ## GAME GUIDANCE FOR VILLAGER
        - Protecting special villagers, especially the seer, is crucial for your team's success.
        - Be cautious and decide whether to trust other players based on their speeches and actions.
        - Base your decisions on the information you have received, be logical and engage in the discussion to vote out the suspected werewolves.

        # NOTE
        - [IMPORTANT] DO NOT make up any information that is not provided by the moderator or other players.
        - This is a TEXT-based game, so DO NOT use or make up any non-textual information.
        - Always critically reflect on whether your evidence exist, and avoid making assumptions.
        - Your response should be specific and concise, provide clear reason and avoid unnecessary elaboration.
        - Generate your one-line response by using the `generate_response` function.
        - Don't repeat the others' speeches.
        - [CRITICAL] Remember: REASONING is private (only you see it), STATEMENT is public (everyone sees it). Use this to your advantage!""",
    )
    return system_prompt


if __name__ == "__main__":
    from agentscope.tuner import (
        DatasetConfig,
        TunerModelConfig,
        AlgorithmConfig,
    )

    # High-level configuration in code (easy to modify)
    config_path = Path(__file__).parent / "config.yaml"

    # Setup Model Path
    trained_model_path = (
        "Qwen/Qwen2.5-7B-Instruct"  # fill in your model path here
    )
    auxiliary_model_path = "Qwen/Qwen3-30B-A3B-Instruct-2507"  # fill in your auxiliary model path here

    # Dataset configuration
    dataset = DatasetConfig(
        path=str(Path(__file__).parent / "data"),
        split="train",
        total_steps=400,  # Total training steps
    )

    # Model configuration (trainable model for werewolf players)
    model = TunerModelConfig(
        model_path=trained_model_path,
        max_model_len=25600,
        max_tokens=4096,
        temperature=1.0,
        inference_engine_num=16,
        tensor_parallel_size=1,
        tool_call_parser="hermes",
        reasoning_parser=None,
    )

    # Auxiliary models (for non-werewolf players)
    auxiliary_models = {
        "participant": TunerModelConfig(
            model_path=auxiliary_model_path,
            max_model_len=25600,
            max_tokens=4096,
            temperature=0.1,  # Lower temperature for auxiliary models
            inference_engine_num=8,
            tensor_parallel_size=1,
            tool_call_parser="hermes",
            reasoning_parser=None,
        ),
    }

    # Algorithm configuration
    algorithm = AlgorithmConfig(
        algorithm_type="multi_step_grpo",
        group_size=32,  # repeat_times in Trinity
        batch_size=24,
        learning_rate=1e-6,
        save_interval_steps=100,
        eval_interval_steps=100,
    )

    # Run training with hybrid configuration
    # Code parameters above + detailed Trinity config from YAML
    tune(
        workflow_func=run_werewolves_workflow,
        judge_func=None,  # We compute reward directly in the workflow
        train_dataset=dataset,
        model=model,
        auxiliary_models=auxiliary_models,
        algorithm=algorithm,
        config_path=str(config_path),  # For cluster, explorer, trainer details
    )
