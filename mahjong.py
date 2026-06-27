"""Mahjong hand generation and verification for Riichi Mahjong."""

import random
from itertools import combinations

# Tile encoding: (suit, number)
# suit: 'w'=万, 'p'=筒, 's'=索, 'z'=字
# number: 1-9 for wan/pin/sou, 1-7 for honors

HONOR_NAMES = {1: "東", 2: "南", 3: "西", 4: "北", 5: "白", 6: "発", 7: "中"}
HONOR_TO_NUM = {v: k for k, v in HONOR_NAMES.items()}

ALL_TILES = []
for s in "wps":
    for n in range(1, 10):
        ALL_TILES.append((s, n))
for n in range(1, 8):
    ALL_TILES.append(("z", n))


def tile_str(t):
    s, n = t
    if s == "z":
        return f"z{HONOR_NAMES.get(n, str(n))}"
    return f"{s}{n}"


def hand_str(tiles, separate_win=True):
    """Convert tile list to display string. Winning tile (last) separated if separate_win=True."""
    if len(tiles) != 14:
        suits = {"w": [], "p": [], "s": [], "z": []}
        for s, n in tiles:
            suits[s].append(n)
        parts = []
        for s in "wpsz":
            if suits[s]:
                nums = suits[s]
                nums.sort()
                if s == "z":
                    parts.append("z" + "".join(HONOR_NAMES.get(n, str(n)) for n in nums))
                else:
                    parts.append(s + "".join(str(n) for n in nums))
        return " ".join(parts)

    suit_order = {"w": 0, "p": 1, "s": 2, "z": 3}
    first13 = sorted(tiles[:13], key=lambda t: (suit_order.get(t[0], 99), t[1]))
    win_tile = tiles[13]

    suits = {"w": [], "p": [], "s": [], "z": []}
    for s, n in first13:
        suits[s].append(n)
    parts = []
    for s in "wpsz":
        if suits[s]:
            nums = suits[s]
            nums.sort()
            if s == "z":
                parts.append("z" + "".join(HONOR_NAMES.get(n, str(n)) for n in nums))
            else:
                parts.append(s + "".join(str(n) for n in nums))

    main = " ".join(parts)
    wt = describe_tile(win_tile) if separate_win else tile_str(win_tile)
    return f"{main} 河底[{wt}]" if separate_win else f"{main} {tile_str(win_tile)}"


def parse_hand(text):
    """Parse a guess string like 'w112233 s445566 p77' or 'z東東東 w123...' into tile list."""
    tiles = []
    text = text.strip().lower()
    parts = text.split()
    for part in parts:
        if not part:
            continue
        suit = part[0]
        rest = part[1:]
        if suit not in "wpsz":
            continue
        if suit == "z":
            for ch in rest:
                if ch.isdigit():
                    n = int(ch)
                else:
                    n = HONOR_TO_NUM.get(ch)
                    if n is None:
                        continue
                tiles.append((suit, n))
        else:
            for ch in rest:
                if ch.isdigit():
                    tiles.append((suit, int(ch)))
    return tiles


def has_yaku(tiles):
    """Check if the 14-tile hand has at least one valid yaku."""
    return len(find_yaku(tiles)) > 0


def find_yaku(tiles, seat_wind=1, round_wind=1):
    """Return list of yaku names present in the hand. Winds affect yakuhai detection."""
    yaku = []
    counts = _count_tiles(tiles)

    # 国士无双: 13 unique orphans + 1 duplicate
    orphans_required = set()
    for s in "wps":
        orphans_required.add((s, 1))
        orphans_required.add((s, 9))
    for n in range(1, 8):
        orphans_required.add(("z", n))
    actual = set(tiles)
    missing = orphans_required - actual
    if len(missing) <= 1 and len(tiles) == 14:
        if len(missing) == 0 and any(c == 2 for c in counts.values()):
            yaku.append("国士无双")
        elif len(missing) == 1:
            yaku.append("国士无双")

    # 字一色: all honors
    if all(s == "z" for s, n in tiles):
        yaku.append("字一色")

    # 小四喜: 3 or 4 wind triplets
    wind_triplets = sum(1 for n in range(1, 5) if counts.get(("z", n), 0) >= 3)
    wind_pairs = sum(1 for n in range(1, 5) if counts.get(("z", n), 0) == 2)
    if wind_triplets == 3 and wind_pairs == 1:
        yaku.append("小四喜")
    elif wind_triplets == 4:
        yaku.append("小四喜")

    # 役牌: triplet of seat wind, round wind, or dragon
    yakuhai_tiles = {("z", seat_wind), ("z", round_wind), ("z", 5), ("z", 6), ("z", 7)}
    for (s, n), c in counts.items():
        if (s, n) in yakuhai_tiles and c >= 3:
            yaku.append("役牌")

    # 断幺九: all 2-8, no honors
    if all(s != "z" and 2 <= n <= 8 for s, n in tiles):
        yaku.append("断幺九")

    # 对对和: 4 triplets + 1 pair
    tri = sum(1 for c in counts.values() if c >= 3)
    pr = sum(1 for c in counts.values() if c == 2)
    if tri == 4 and pr == 1:
        yaku.append("对对和")

    # 七对子
    if len(counts) == 7 and all(c == 2 for c in counts.values()):
        yaku.append("七对子")

    # 混一色: one number suit + honors
    suits_present = set(s for s, n in tiles)
    number_suits = suits_present - {"z"}
    if len(number_suits) == 1 and "z" in suits_present and len(suits_present) == 2:
        yaku.append("混一色")

    # 一气通贯: 1-9 straight in one suit
    for s in "wps":
        if all(counts.get((s, n), 0) >= 1 for n in range(1, 10)):
            yaku.append("一气通贯")

    # 三色同刻: same-number triplet in all 3 suits
    for n in range(1, 10):
        if all(counts.get((s, n), 0) >= 3 for s in "wps"):
            yaku.append("三色同刻")

    # 三色同顺: same-number sequence in all 3 suits
    for start in range(1, 8):
        seq = [start, start+1, start+2]
        if all(all(counts.get((s, x), 0) >= 1 for x in seq) for s in "wps"):
            yaku.append("三色同顺")

    # 一盃口
    for s in "wps":
        suit_nums = sorted([n for ss, n in tiles if ss == s])
        for start in range(1, 8):
            seq = [start, start+1, start+2]
            remaining = list(suit_nums)
            ok = True
            for x in seq:
                if x in remaining:
                    remaining.remove(x)
                else:
                    ok = False
                    break
            if ok:
                remaining2 = list(remaining)
                for x in seq:
                    if x in remaining2:
                        remaining2.remove(x)
                    else:
                        ok = False
                        break
            if ok:
                yaku.append("一盃口")
                break

    return yaku


def generate_valid_hand(seat_wind=1, round_wind=1):
    """Generate a valid 14-tile Riichi mahjong hand with at least one yaku."""
    builders = [
        _build_tanyao, _build_chiitoitsu, _build_toitoi,
        _build_iipeikou, _build_pinfu, _build_kokushi,
        _build_sanshoku_doukou, _build_ikkitsuukan,
        _build_sanshoku_doujun, _build_honitsu, _build_tsuuiisou,
        _build_shousuushi,
    ]
    for _ in range(500):
        builder = random.choice(builders)
        if builder in (_build_yakuhai,):
            # yakuhai needs the specific honor that matches winds
            honor = random.choice([seat_wind, round_wind, 5, 6, 7])
            tiles = _build_yakuhai_with_honor(honor)
        else:
            tiles = builder()
        if tiles and len(tiles) == 14:
            hand = list(tiles)
            random.shuffle(hand)
            win_tile = hand[-1]
            first13 = sorted(hand[:13], key=lambda t: ({"w":0,"p":1,"s":2,"z":3}[t[0]], t[1]))
            return first13 + [win_tile]
    return _build_chiitoitsu() or _build_yakuhai_with_honor(5)


def _build_yakuhai_with_honor(honor_num):
    """Hand with specific honor triplet (for yakuhai with seat/round wind)."""
    tiles = [("z", honor_num)] * 3
    for _ in range(3):
        if random.random() < 0.5:
            tiles += _random_sequence()
        else:
            tiles += _random_triplet()
    tiles += _random_pair()
    return tiles


YAKU_BUILDERS = {
    "断幺九": _build_tanyao,
    "役牌": lambda: _build_yakuhai_with_honor(random.choice([1,2,3,4,5,6,7])),
    "对对和": _build_toitoi,
    "七对子": _build_chiitoitsu,
    "一盃口": _build_iipeikou,
    "平和": _build_pinfu,
    "国士无双": _build_kokushi,
    "三色同刻": _build_sanshoku_doukou,
    "一气通贯": _build_ikkitsuukan,
    "三色同顺": _build_sanshoku_doujun,
    "混一色": _build_honitsu,
    "字一色": _build_tsuuiisou,
    "小四喜": _build_shousuushi,
}


def generate_hand_with_yaku(yaku_name, seat_wind=1, round_wind=1):
    """Generate a hand with a specific yaku. Returns None if not found."""
    if not yaku_name:
        return generate_valid_hand(seat_wind, round_wind)

    builder = YAKU_BUILDERS.get(yaku_name)
    if builder is None:
        # Try partial match
        for name, b in YAKU_BUILDERS.items():
            if yaku_name in name or name in yaku_name:
                builder = b
                break
        if builder is None:
            return None

    for _ in range(200):
        tiles = builder()
        if tiles and len(tiles) == 14 and yaku_name in find_yaku(tiles, seat_wind, round_wind):
            hand = list(tiles)
            random.shuffle(hand)
            win_tile = hand[-1]
            first13 = sorted(hand[:13], key=lambda t: ({"w":0,"p":1,"s":2,"z":3}[t[0]], t[1]))
            return first13 + [win_tile]
    return None


def _random_sequence(suit=None):
    """Return a random sequence of 3 tiles like ('w',1),('w',2),('w',3)."""
    if suit is None:
        suit = random.choice("wps")
    start = random.randint(1, 7)
    return [(suit, start), (suit, start+1), (suit, start+2)]


def _random_triplet(suit=None, num=None):
    """Return 3 copies of a random tile."""
    if suit is None:
        suit = random.choice("wpsz")
    if num is None:
        num = random.randint(2, 8) if suit != "z" else random.randint(1, 7)
    return [(suit, num), (suit, num), (suit, num)]


def _random_pair(suit=None, num=None):
    """Return 2 copies of a random tile."""
    if suit is None:
        suit = random.choice("wpsz")
    if num is None:
        num = random.randint(2, 8) if suit != "z" else random.randint(1, 7)
    return [(suit, num), (suit, num)]


def _any_sequence(suit):
    """Return a random sequence from the given suit."""
    start = random.randint(1, 7)
    return [(suit, start), (suit, start+1), (suit, start+2)]


def _any_triplet(suit):
    num = random.randint(1, 9) if suit != "z" else random.randint(1, 7)
    return [(suit, num), (suit, num), (suit, num)]


def _build_tanyao():
    """4 melds + 1 pair, all tiles 2-8, no honors."""
    tiles = []
    # 4 melds (sequences or triplets, all 2-8)
    for _ in range(4):
        if random.random() < 0.6:
            tiles += _random_sequence()
        else:
            tiles += _random_triplet()
    # 1 pair (2-8, no honor)
    tiles += _random_pair()
    return tiles


def _build_yakuhai():
    """Hand with at least one honor triplet (yakuhai)."""
    tiles = []
    # One honor triplet
    honor_num = random.randint(1, 7)
    tiles += [("z", honor_num)] * 3
    # 3 more melds
    for _ in range(3):
        if random.random() < 0.5:
            tiles += _random_sequence()
        else:
            tiles += _random_triplet()
    # 1 pair
    tiles += _random_pair()
    return tiles


def _build_toitoi():
    """4 triplets + 1 pair (all triplets)."""
    tiles = []
    for _ in range(4):
        tiles += _random_triplet()
    tiles += _random_pair()
    return tiles


def _build_chiitoitsu():
    """7 distinct pairs."""
    tiles = []
    used = set()
    for _ in range(7):
        while True:
            s = random.choice("wpsz")
            n = random.randint(1, 9) if s != "z" else random.randint(1, 7)
            if (s, n) not in used:
                used.add((s, n))
                break
        tiles += [(s, n), (s, n)]
    return tiles


def _build_iipeikou():
    """Two identical sequences + other melds."""
    suit = random.choice("wps")
    start = random.randint(1, 7)
    seq = [(suit, start), (suit, start+1), (suit, start+2)]
    tiles = seq + seq  # two identical sequences (6 tiles)
    # 2 more melds (4 tiles total needed, minus 6 = need 8 more)
    for _ in range(2):
        if random.random() < 0.5:
            tiles += _random_sequence()
        else:
            tiles += _random_triplet()
    tiles += _random_pair()
    return tiles


def _build_pinfu():
    """All sequences, non-yakuhai pair, two-sided wait."""
    tiles = []
    for _ in range(4):
        tiles += _random_sequence()
    ps = random.choice("wps")
    pn = random.randint(2, 8)
    tiles += [(ps, pn), (ps, pn)]
    return tiles


def _build_kokushi():
    """国士无双: 13 unique orphans (1,9 + 7 honors) + 1 duplicate."""
    orphans = []
    for s in "wps":
        orphans.append((s, 1))
        orphans.append((s, 9))
    for n in range(1, 8):
        orphans.append(("z", n))
    dup = random.choice(orphans)
    return orphans + [dup]


def _build_honchantaiyao():
    """混全带幺九: every meld contains at least one terminal (1,9) or honor."""
    tiles = []
    for _ in range(4):
        kind = random.random()
        if kind < 0.3:
            t = random.choice("wps")
            tiles += [(t, random.choice([1, 2, 3, 7, 8, 9])), (t, random.choice([1, 2, 3])), (t, random.choice([7, 8, 9]))]
        elif kind < 0.6:
            su = random.choice("wps")
            start = random.choice([1, 7])
            tiles += [(su, start), (su, start+1), (su, start+2)]
        else:
            tiles += _random_triplet(random.choice("z"))
    tiles += _random_pair()
    return tiles


def _build_sanshoku_doukou():
    """三色同刻: same-number triplet in w, p, s."""
    num = random.randint(1, 9)
    tiles = []
    for s in "wps":
        tiles += [(s, num)] * 3
    tiles += _random_triplet()
    tiles += _random_pair()
    return tiles


def _build_ikkitsuukan():
    """一气通贯: 1-9 straight in one suit."""
    suit = random.choice("wps")
    tiles = [(suit, 1), (suit, 2), (suit, 3), (suit, 4), (suit, 5), (suit, 6), (suit, 7), (suit, 8), (suit, 9)]
    tiles += _random_triplet()
    tiles += _random_pair()
    return tiles


def _build_sanshoku_doujun():
    """三色同顺: same sequence across w/p/s."""
    start = random.randint(1, 7)
    tiles = []
    for s in "wps":
        tiles += [(s, start), (s, start+1), (s, start+2)]
    tiles += _random_triplet()
    tiles += _random_pair()
    return tiles


def _build_honitsu():
    """混一色: one suit + honors only."""
    suit = random.choice("wps")
    tiles = []
    hon = random.choice([0, 1, 2, 3])
    for _ in range(4 - hon):
        if random.random() < 0.5:
            tiles += _random_sequence(suit)
        else:
            tiles += _random_triplet(suit)
    for _ in range(hon):
        tiles += _random_triplet("z")
    tiles += _random_pair()
    return tiles


def _build_tsuuiisou():
    """字一色: all honor tiles."""
    tiles = []
    for _ in range(4):
        n = random.randint(1, 7)
        tiles += [("z", n)] * 3
    n = random.randint(1, 7)
    tiles += [("z", n), ("z", n)]
    return tiles


def _build_shousuushi():
    """小四喜: 3 wind triplets + 1 wind pair."""
    winds = [("z", 1), ("z", 2), ("z", 3), ("z", 4)]
    random.shuffle(winds)
    pair_wind = winds[3]
    tiles = []
    for i in range(3):
        tiles += winds[i:i+1] * 3  # triplet
    tiles += [pair_wind, pair_wind]  # pair
    tiles += _random_triplet()
    return tiles


def validate_hand(tiles):
    """Validate parsed hand. Returns (True, "") or (False, error_message)."""
    if len(tiles) != 14:
        return False, f"手牌必须为 14 张，当前 {len(tiles)} 张。"
    for s, n in tiles:
        if s == "z" and n not in range(1, 8):
            return False, f"无效字牌: z{n}"
        elif s in "wps" and n not in range(1, 10):
            return False, f"无效数牌: {s}{n}"
    return True, ""


def is_valid_hand(tiles):
    """Check if 14 tiles form a valid Riichi winning hand."""
    if len(tiles) != 14:
        return False
    return _is_valid_standard(tiles) or _is_chiitoitsu(tiles) or _is_kokushi(tiles)


def _is_kokushi(tiles):
    """国士无双: 13 unique orphans + 1 duplicate."""
    orphans_needed = set()
    for s in "wps":
        orphans_needed.add((s, 1))
        orphans_needed.add((s, 9))
    for n in range(1, 8):
        orphans_needed.add(("z", n))
    actual = set(tiles)
    missing = orphans_needed - actual
    return len(missing) <= 1 and len(tiles) == 14


def _count_tiles(tiles):
    counts = {}
    for t in tiles:
        counts[t] = counts.get(t, 0) + 1
    return counts


def _is_chiitoitsu(tiles):
    """7 distinct pairs."""
    counts = _count_tiles(tiles)
    return len(counts) == 7 and all(c == 2 for c in counts.values())


def _is_valid_standard(tiles):
    """Check 4 melds + 1 pair by backtracking."""
    counts = _count_tiles(tiles)
    total = sum(counts.values())
    if total != 14:
        return False

    # Try each possible pair
    pairs = []
    for t, c in counts.items():
        if c >= 2:
            pairs.append(t)

    for pair in pairs:
        c = dict(counts)
        c[pair] -= 2
        if c[pair] == 0:
            del c[pair]
        if _can_form_melds(c, 4):
            return True
    return False


def _can_form_melds(counts, remaining_melds):
    """Recursively check if remaining tiles can form `remaining_melds` melds."""
    if remaining_melds == 0:
        return len(counts) == 0

    if not counts:
        return False

    # Try triplet
    for (s, n), c in list(counts.items()):
        if c >= 3:
            updated = dict(counts)
            updated[(s, n)] -= 3
            if updated[(s, n)] == 0:
                del updated[(s, n)]
            if _can_form_melds(updated, remaining_melds - 1):
                return True

    # Try sequence (only for w/p/s suits)
    for s in "wps":
        for n in range(1, 8):
            seq = [(s, n), (s, n+1), (s, n+2)]
            if all(counts.get(t, 0) >= 1 for t in seq):
                updated = dict(counts)
                for t in seq:
                    updated[t] -= 1
                    if updated[t] == 0:
                        del updated[t]
                if _can_form_melds(updated, remaining_melds - 1):
                    return True

    return False


def compare_guess(guess_tiles, target_tiles):
    """Position-based comparison. Target is sorted (first 13 + winning tile at pos 13).
    Guess is compared as-is (user's input order).
    - Green: correct tile at correct position
    - Yellow: tile exists in target but at wrong position
    - Gray: tile not in target
    """
    result = []
    original_counts = {}
    remaining_counts = {}
    for t in target_tiles:
        original_counts[t] = original_counts.get(t, 0) + 1
        remaining_counts[t] = remaining_counts.get(t, 0) + 1

    used = {}
    for i, g in enumerate(guess_tiles):
        t = target_tiles[i] if i < len(target_tiles) else None
        if t is not None and g == t and used.get(g, 0) < original_counts.get(g, 0):
            result.append((g, "correct"))
            used[g] = used.get(g, 0) + 1
            remaining_counts[g] -= 1
        else:
            result.append((g, None))

    for i, (g, status) in enumerate(result):
        if status is None:
            if remaining_counts.get(g, 0) > 0:
                result[i] = (g, "present")
                remaining_counts[g] -= 1
            else:
                result[i] = (g, "absent")

    return result


def describe_tile(tile):
    """Convert a tile tuple to Chinese name."""
    s, n = tile
    if s == "z":
        names = {1: "東", 2: "南", 3: "西", 4: "北", 5: "白", 6: "発", 7: "中"}
        return names.get(n, str(n))
    suits = {"w": "万", "p": "筒", "s": "索"}
    chinese_nums = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九"}
    return f"{chinese_nums.get(n, str(n))}{suits.get(s, s)}"


def describe_result(comp_result):
    """Convert comparison result to a human-readable Chinese string."""
    status_names = {"correct": "绿色", "present": "黄色", "absent": "灰色"}
    parts = []
    for tile, status in comp_result:
        name = describe_tile(tile)
        parts.append(f"{name}({status_names[status]})")
    return " ".join(parts)
