# -*- coding: utf-8 -*-
"""Enhanced prompts with reasoning/statement separation awareness - 7 Player Version."""


class EnglishPrompts:
    """English prompts used to guide the werewolf game."""

    to_dead_player = (
        "{}, you're eliminated now. Now you can make a final statement to "
        "all alive players before you leave the game.\n\n"
        "IMPORTANT: Your final words will be structured into two parts:\n"
        "1. REASONING (Private): Your strategic thinking - NOT visible to others\n"
        "2. STATEMENT (Public): Your actual final words - VISIBLE to all players\n\n"
        "Think carefully about what information to reveal or hide in your final statement."
    )

    to_all_new_game = (
        "A new game is starting, the players are: {}. Now we randomly "
        "reassign the roles to each player and inform them of their roles "
        "privately."
    )

    to_all_night = (
        "Night has fallen, everyone close your eyes. Werewolves open your "
        "eyes and choose a player to eliminate tonight."
    )

    to_wolves_discussion = (
        "[WEREWOLVES ONLY] {}, you should discuss and "
        "decide on a player to eliminate tonight. Current alive players "
        "are {}. Remember to set `reach_agreement` to True if you reach an "
        "agreement during the discussion."
    )

    to_wolves_vote = "[WEREWOLVES ONLY] Which player do you vote to kill?"

    to_wolves_res = (
        "[WEREWOLVES ONLY] The voting result is {}. So you have chosen to "
        "eliminate {}."
    )

    to_all_witch_turn = (
        "Witch's turn, witch open your eyes and decide your action tonight..."
    )
    to_witch_resurrect = (
        "[WITCH ONLY] {witch_name}, you're the witch, and tonight {dead_name} "
        "is eliminated. You can resurrect him/her by using your healing "
        "potion, "
        "and note you can only use it once in the whole game. Do you want to "
        "resurrect {dead_name}? Give me your reason and decision."
    )

    to_witch_resurrect_no = (
        "[WITCH ONLY] The witch has chosen not to resurrect the player."
    )
    to_witch_resurrect_yes = (
        "[WITCH ONLY] The witch has chosen to resurrect the player."
    )

    to_witch_poison = (
        "[WITCH ONLY] {witch_name}, as a witch, you have a one-time-use "
        "poison potion, do you want to use it tonight? Give me your reason "
        "and decision."
    )

    to_all_seer_turn = (
        "Seer's turn, seer open your eyes and check one player's identity "
        "tonight..."
    )

    to_seer = (
        "[SEER ONLY] {}, as the seer you can check one player's identity "
        "tonight. Who do you want to check? Give me your reason and decision."
    )

    to_seer_result = (
        "[SEER ONLY] You've checked {agent_name}, and the result is: {role}."
    )

    to_all_day = (
        "The day is coming, all players open your eyes. Last night, "
        "the following player(s) has been eliminated: {}."
    )

    to_all_peace = (
        "The day is coming, all the players open your eyes. Last night is "
        "peaceful, no player is eliminated."
    )

    to_all_discuss = (
        "Now the alive players are {names}. The game goes on, it's time to "
        "discuss and vote a player to be eliminated. Now you each take turns "
        "to speak once in the order of {names}.\n\n"
        "IMPORTANT: Your response will be structured into two parts:\n"
        "1. REASONING (Private): Your internal analysis - NOT visible to others\n"
        "2. STATEMENT (Public): Your actual speech - VISIBLE to all players\n\n"
        "Think carefully in your reasoning, then speak strategically in your statement."
    )

    to_all_vote = (
        "Now the discussion is over. Everyone, please vote to eliminate one "
        "player from the alive players: {}."
    )

    to_all_res = "The voting result is {}. So {} has been voted out."

    to_all_wolf_win = (
        "There are {n_alive} players alive, and {n_werewolves} of them are "
        "werewolves. "
        "The game is over and werewolves win🐺🎉!"
        "In this game, the true roles of all players are: {true_roles}"
    )

    to_all_village_win = (
        "All the werewolves have been eliminated."
        "The game is over and villagers win🏘️🎉!"
        "In this game, the true roles of all players are: {true_roles}"
    )

    to_all_continue = "The game goes on."

    to_all_reflect = (
        "The game is over. Now each player can reflect on their performance. "
        "Note each player only has one chance to speak and the reflection is "
        "only visible to themselves."
    )


class ChinesePrompts:
    """Chinese prompts used to guide the werewolf game."""

    to_dead_player = (
        "{}, 你已被淘汰。现在你可以向所有存活玩家发表最后的遗言。\n\n"
        "重要提示：你的遗言将分为两个部分：\n"
        "1. 推理（私密）：你的策略思考 - 其他玩家看不到\n"
        "2. 发言（公开）：你的实际遗言 - 所有玩家都能看到\n\n"
        "仔细思考在遗言中应该透露或隐藏什么信息。"
    )

    to_all_new_game = "新的一局游戏开始，参与玩家包括：{}。现在为每位玩家重新随机分配身份，并私下告知各自身份。"

    to_all_night = "天黑了，请所有人闭眼。狼人请睁眼，选择今晚要淘汰的一名玩家..."

    to_wolves_discussion = (
        "[仅狼人可见] {}, 你们可以讨论并决定今晚要淘汰的玩家。当前存活玩家有：{}。"
        "如果达成一致，请将 `reach_agreement` 设为 True。"
    )

    to_wolves_vote = "[仅狼人可见] 你投票要杀死哪位玩家？"

    to_wolves_res = "[仅狼人可见] 投票结果为 {}，你们选择淘汰 {}。"

    to_all_witch_turn = "轮到女巫行动，女巫请睁眼并决定今晚的操作..."
    to_witch_resurrect = (
        "[仅女巫可见] {witch_name}，你是女巫，今晚{dead_name}被淘汰。"
        "你可以用解药救他/她，注意解药全局只能用一次。你要救{dead_name}吗？"
        "请给出理由和决定。"
    )

    to_witch_resurrect_no = "[仅女巫可见] 女巫选择不救该玩家。"
    to_witch_resurrect_yes = "[仅女巫可见] 女巫选择救活该玩家。"

    to_witch_poison = "[仅女巫可见] {witch_name}，你有一瓶一次性毒药，今晚要使用吗？请给出理由和决定。"

    to_all_seer_turn = "轮到预言家行动，预言家请睁眼并查验一名玩家身份..."

    to_seer = "[仅预言家可见] {}, 你是预言家，今晚可以查验一名玩家身份。你要查谁？请给出理由和决定。"

    to_seer_result = "[仅预言家可见] 你查验了{agent_name}，结果是：{role}。"

    to_all_day = "天亮了，请所有玩家睁眼。昨晚被淘汰的玩家有：{}。"

    to_all_peace = "天亮了，请所有玩家睁眼。昨晚平安夜，无人被淘汰。"

    to_all_discuss = (
        "现在存活玩家有：{names}。游戏继续，大家开始讨论并投票淘汰一名玩家。请按顺序（{names}）依次发言。\n\n"
        "重要提示：你的回答将分为两个部分：\n"
        "1. 推理（私密）：你的内心分析 - 其他玩家看不到\n"
        "2. 发言（公开）：你的实际发言 - 所有玩家都能看到\n\n"
        "在推理中仔细思考，然后在发言中策略性地表达。"
    )

    to_all_vote = "讨论结束。请大家从存活玩家中投票淘汰一人：{}。"

    to_all_res = "投票结果为 {}，{} 被淘汰。"

    to_all_wolf_win = (
        "当前存活玩家共{n_alive}人，其中{n_werewolves}人为狼人。"
        "游戏结束，狼人获胜🐺🎉！"
        "本局所有玩家真实身份为：{true_roles}"
    )

    to_all_village_win = "所有狼人已被淘汰。游戏结束，村民获胜🏘️🎉！本局所有玩家真实身份为：{true_roles}"

    to_all_continue = "游戏继续。"

    to_all_reflect = "游戏结束。现在每位玩家可以对自己的表现进行反思。注意每位玩家只有一次发言机会，且反思内容仅自己可见。"

