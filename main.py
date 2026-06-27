import os
import json
import random
import logging
from astrbot.api.all import *
from .mahjong import generate_valid_hand, parse_hand, compare_guess, hand_str, validate_hand, is_valid_hand, find_yaku, describe_result
from .renderer import render_guess, render_rules, render_rules

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

        seat_wind = random.randint(1, 4)
        round_wind = random.randint(1, 4)
        wind_names = {1: "東", 2: "南", 3: "西", 4: "北"}
        hand = generate_valid_hand(seat_wind, round_wind)
        yaku_list = find_yaku(hand, seat_wind, round_wind)
        yaku_text = "、".join(yaku_list) if yaku_list else "无役"

        self.sessions[session_id] = {
            "target": hand,
            "history": [],
            "tries": 0,
            "seat_wind": seat_wind,
            "round_wind": round_wind,
        }

        rules_path = os.path.join(self.plugin_dir, "temp_rules.png")
        render_rules(hand, rules_path)
        yield event.image_result(rules_path)
        yield event.plain_result(
            f"【立直麻将猜胡牌】开始！\n"
            f"自风: {wind_names[seat_wind]}  场风: {wind_names[round_wind]}\n"
            f"格式：w/p/s/z + 数字或中文\n"
            f"如: w112233 s445566 p77\n"
            f"字牌: z東東東 或 z111\n"
            f"共 {self.max_attempts} 次机会，发送合法胡牌开始猜"
        )

    @command("结束猜胡牌")
    async def mahjong_end(self, event: AstrMessageEvent):
        session_id = event.get_session_id()
        if session_id in self.sessions:
            ans = self.sessions[session_id]["target"]
            ans_path = os.path.join(self.plugin_dir, f"temp_ans_{session_id}.png")
            render_rules(ans, ans_path)
            yield event.image_result(ans_path)
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

        if not is_valid_hand(guess):
            yield event.plain_result("该牌型不是合法胡牌（需要 4 面子 + 1 雀头 或 国士无双 或 七对子），请重新提交。")
            return

        has_yaku = find_yaku(guess, session["seat_wind"], session["round_wind"])
        if not has_yaku:
            yield event.plain_result("该牌型没有役种，无法胡牌。请确保牌型包含至少一个役种。")
            return

        comp = compare_guess(guess, session["target"])
        session["history"].append((guess, comp))
        session["tries"] += 1

        # Render result
        img_path = os.path.join(self.plugin_dir, f"temp_{session_id}.png")
        render_guess(session["history"], session["target"], img_path)
        yield event.image_result(img_path)

        # Text feedback (log only, not sent to chat)
        desc = describe_result(comp)
        logger.info(f"[mahjong] {desc}")

        # Check win/lose
        all_correct = all(s == "correct" for _, s in comp)
        remaining = self.max_attempts - session["tries"]
        if all_correct:
            yield event.plain_result(f"🎉 猜中了！正确牌型：{hand_str(session['target'])}")
            if os.path.exists(img_path):
                os.remove(img_path)
            del self.sessions[session_id]
        elif session["tries"] >= self.max_attempts:
            ans_path = os.path.join(self.plugin_dir, f"temp_ans_{session_id}.png")
            render_rules(session["target"], ans_path)
            yield event.image_result(ans_path)
            yield event.plain_result(f"机会耗尽！正确牌型：{hand_str(session['target'])}")
            if os.path.exists(img_path):
                os.remove(img_path)
            del self.sessions[session_id]
        else:
            yield event.plain_result(f"继续猜！剩余 {remaining} 次机会")

    async def terminate(self):
        self.sessions.clear()
