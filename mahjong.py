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


def find_yaku(tiles):
    """Return list of yaku names present in the hand."""
    yaku = []
    counts = {}
    for s, n in tiles:
        counts[(s, n)] = counts.get((s, n), 0) + 1

    all_nums = [n for s, n in tiles if s != "z"]
    all_suits = [s for s, n in tiles if s != "z"]
    honor_pairs = sum(1 for (s, n), c in counts.items() if s == "z" and c >= 2)

    # Tanyao: all tiles 2-8, no honors
    if all(2 <= n <= 8 for s, n in tiles if s != "z") and all(s != "z" for s, n in tiles):
        yaku.append("断幺九")

    # Yakuhai: triplet of any dragon, plus check
    for (s, n), c in counts.items():
        if s == "z" and c >= 3:
            yaku.append("役牌")

    # Toitoi: 4 triplets + 1 pair (all melds are triplets)
    triplets = sum(1 for c in counts.values() if c >= 3)
    pairs = sum(1 for c in counts.values() if c == 2)
    if triplets == 4 and pairs == 1:
        yaku.append("对对和")

    # Seven pairs
    if all(c == 2 or c == 4 for c in counts.values()) and sum(1 for c in counts.values() if c == 2) == 7:
        yaku.append("七对子")

    # Iipeikou: two identical chi sequences (same suit, same numbers)
    for s in "wps":
        suit_tiles = sorted([n for ss, n in tiles if ss == s])
        for start in range(1, 8):
            seq = [start, start+1, start+2]
            if suit_tiles.count(start) >= 1 and suit_tiles.count(start+1) >= 1 and suit_tiles.count(start+2) >= 1:
                # Found at least one copy of this sequence
                remaining = list(suit_tiles)
                for x in seq:
                    remaining.remove(x)
                if remaining.count(start) >= 1 and remaining.count(start+1) >= 1 and remaining.count(start+2) >= 1:
                    yaku.append("一盃口")
                    break

    # Pinfu: all chi, pair not yakuhai, two-sided wait (simplified)
    # Just check if hand has 4 chi + non-yakuhai pair
    chi_count = 0
    remaining_tiles = list(tiles)
    # Remove one pair first
    has_pair = False
    for (s, n), c in counts.items():
        if c >= 2:
            # Check if this pair is valid for pinfu (not yakuhai)
            if s == "z":
                continue  # Skip honor pairs for pinfu
            # Found a non-yakuhai pair
            remaining_tiles.remove((s, n))
            remaining_tiles.remove((s, n))
            has_pair = True
            break
    if has_pair:
        for s in "wps":
            suit_remain = sorted([n for ss, n in remaining_tiles if ss == s])
            for start in range(1, 8):
                seq = [start, start+1, start+2]
                temp = list(suit_remain)
                ok = True
                for x in seq:
                    if x in temp:
                        temp.remove(x)
                    else:
                        ok = False
                        break
                if ok:
                    chi_count += 1
                    suit_remain = temp
        if chi_count == 4:
            yaku.append("平和")

    return yaku


def generate_valid_hand():
    """Generate a valid 14-tile Riichi mahjong hand (4 melds + 1 pair, at least one yaku)."""
    for _ in range(500):
        yaku_type = random.randint(0, 5)
        if yaku_type == 0:
            hand = _build_tanyao()
        elif yaku_type == 1:
            hand = _build_yakuhai()
        elif yaku_type == 2:
            hand = _build_toitoi()
        elif yaku_type == 3:
            hand = _build_chiitoitsu()
        elif yaku_type == 4:
            hand = _build_iipeikou()
        else:
            hand = _build_pinfu()
        if hand and len(hand) == 14:
            # Choose a random winning tile
            tiles = list(hand)
            random.shuffle(tiles)
            win_tile = tiles[-1]
            remaining = sorted(tiles[:13], key=lambda t: ({"w":0,"p":1,"s":2,"z":3}[t[0]], t[1]))
            return remaining + [win_tile]
    return _build_chiitoitsu() or _build_yakuhai()


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
    # Pair: not yakuhai, not the same suit's triplets
    ps = random.choice("wps")
    pn = random.randint(2, 8)
    tiles += [(ps, pn), (ps, pn)]
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
    """Check if 14 tiles form a valid Riichi winning hand (4 melds + 1 pair, or 7 pairs)."""
    if len(tiles) != 14:
        return False
    return _is_valid_standard(tiles) or _is_chiitoitsu(tiles)


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
    """Position-based comparison. First 13 are sorted, winning tile at position 13.
    - Green: correct tile at correct position
    - Yellow: tile exists in target but at wrong position
    - Gray: tile not in target
    """
    suit_order = {"w": 0, "p": 1, "s": 2, "z": 3}

    g13 = sorted(guess_tiles[:13], key=lambda t: (suit_order.get(t[0], 99), t[1]))
    t13 = sorted(target_tiles[:13], key=lambda t: (suit_order.get(t[0], 99), t[1]))
    g_sorted = g13 + [guess_tiles[13]]
    t_sorted = t13 + [target_tiles[13]]

    result = []
    target_counts = {}
    for t in t_sorted:
        target_counts[t] = target_counts.get(t, 0) + 1

    # First pass: exact matches
    used = {}
    for i, g in enumerate(g_sorted):
        t = t_sorted[i]
        if g == t and used.get(g, 0) < target_counts.get(g, 0):
            result.append((g, "correct"))
            used[g] = used.get(g, 0) + 1
            target_counts[g] -= 1
        else:
            result.append((g, None))

    # Second pass: present/absent
    for i, (g, status) in enumerate(result):
        if status is None:
            if target_counts.get(g, 0) > 0:
                result[i] = (g, "present")
                target_counts[g] -= 1
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
