import os
import json
import random
import logging
from astrbot.api.all import *
from .mahjong import generate_valid_hand, parse_hand, compare_guess, hand_str, find_yaku
from .renderer import render_guess

logger = logging.getLogger("astrbot")


@register("astrbot_plugin_mahjong_guess", "ALin", "立直麻将猜胡牌", "0.1.0")
class MahjongGuessPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        self.sessions = {}

        logger.info("[mahjong] 立直麻将猜胡牌插件已加载")

    @command("猜胡牌")
    async def mahjong_start(self, event: AstrMessageEvent):
        session_id = event.get_session_id()
        if session_id in self.sessions:
            yield event.plain_result("游戏进行中！输入牌型猜胡牌，或发送【结束猜胡牌】退出。")
            return

        hand = generate_valid_hand()
        yaku_list = find_yaku(hand)
        yaku_text = "、".join(yaku_list) if yaku_list else "无役"
        
        self.sessions[session_id] = {
            "target": hand,
            "history": [],
            "tries": 0,
        }

        yield event.plain_result(
            f"【立直麻将猜胡牌】开始！\n"
            f"役种提示：{yaku_text}\n"
            f"格式：w112233 s445566 p77（最多 10 次机会）\n"
            f"字牌可用中文：z東東東 或 z111"
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

        if len(guess) != 14:
            return  # Silently ignore invalid input

        comp = compare_guess(guess, session["target"])
        session["history"].append((guess, comp))
        session["tries"] += 1

        # Render result
        img_path = os.path.join(self.plugin_dir, f"temp_{session_id}.png")
        render_guess(session["history"], session["target"], img_path)
        yield event.image_result(img_path)

        # Check win/lose
        all_correct = all(s == "correct" for _, s in comp)
        if all_correct:
            yield event.plain_result(f"🎉 猜中了！正确牌型：{hand_str(session['target'])}")
            if os.path.exists(img_path):
                os.remove(img_path)
            del self.sessions[session_id]
        elif session["tries"] >= 10:
            yield event.plain_result(f"机会耗尽！正确牌型：{hand_str(session['target'])}")
            if os.path.exists(img_path):
                os.remove(img_path)
            del self.sessions[session_id]

    async def terminate(self):
        self.sessions.clear()
