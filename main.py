import os
import json
import random
import logging
from astrbot.api.all import *
from .mahjong import generate_valid_hand, parse_hand, compare_guess, hand_str, validate_hand
from .renderer import render_guess, render_rules

logger = logging.getLogger("astrbot")


@register("astrbot_plugin_mahjong_guess", "ALin", "立直麻将猜胡牌", "0.1.2")
class MahjongGuessPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        self.sessions = {}
        cfg = config or {}
        self.max_attempts = cfg.get("max_attempts", 10)

        logger.info("[mahjong] 立直麻将猜胡牌插件已加载")

    @command("猜胡牌")
    async def mahjong_start(self, event: AstrMessageEvent):
        session_id = event.get_session_id()
        if session_id in self.sessions:
            yield event.plain_result("游戏进行中！输入牌型猜胡牌，或发送【结束猜胡牌】退出。")
            return

        hand = generate_valid_hand()

        self.sessions[session_id] = {
            "target": hand,
            "history": [],
            "tries": 0,
        }

        rules_path = os.path.join(self.plugin_dir, "temp_rules.png")
        render_rules(hand, rules_path)
        yield event.image_result(rules_path)
        yield event.plain_result(
            f"【立直麻将猜胡牌】开始！\n"
            f"格式：w/p/s/z + 数字或中文\n"
            f"如: w112233 s445566 p77\n"
            f"字牌: z東東東 或 z111\n"
            f"共 {self.max_attempts} 次机会，发送 14 张牌开始猜"
        )

    @command("结束猜胡牌")
    async def mahjong_end(self, event: AstrMessageEvent):
        session_id = event.get_session_id()
        if session_id in self.sessions:
            ans = self.sessions[session_id]["target"]
            yield event.plain_result(f"游戏结束，正确牌型：{hand_str(ans)}")
            del self.sessions[session_id]

    @event_message_type(EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        session_id = event.get_session_id()
        if session_id not in self.sessions:
            return

        user_input = event.message_str.strip()
        if user_input.startswith("/") or user_input in ["结束猜胡牌", "结束猜胡牌！"]:
            return

        session = self.sessions[session_id]
        guess = parse_hand(user_input)

        # Validate
        if len(guess) != 14:
            if len(guess) == 0:
                return  # Silently ignore completely unrecognized input
            yield event.plain_result(f"请发送 14 张手牌（当前 {len(guess)} 张）。格式: w/p/s/z + 数字或中文")
            return

        valid, err = validate_hand(guess)
        if not valid:
            yield event.plain_result(f"手牌格式错误：{err}")
            return

        comp = compare_guess(guess, session["target"])
        session["history"].append((guess, comp))
        session["tries"] += 1

        # Render result
        img_path = os.path.join(self.plugin_dir, f"temp_{session_id}.png")
        render_guess(session["history"], session["target"], img_path)
        yield event.image_result(img_path)

        # Check win/lose
        all_correct = all(s == "correct" for _, s in comp)
        remaining = self.max_attempts - session["tries"]
        if all_correct:
            yield event.plain_result(f"🎉 猜中了！正确牌型：{hand_str(session['target'])}")
            if os.path.exists(img_path):
                os.remove(img_path)
            del self.sessions[session_id]
        elif session["tries"] >= self.max_attempts:
            yield event.plain_result(f"机会耗尽！正确牌型：{hand_str(session['target'])}")
            if os.path.exists(img_path):
                os.remove(img_path)
            del self.sessions[session_id]
        else:
            yield event.plain_result(f"继续猜！剩余 {remaining} 次机会")

    async def terminate(self):
        self.sessions.clear()
