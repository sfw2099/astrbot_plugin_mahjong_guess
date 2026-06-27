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


def hand_str(tiles):
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
    """Generate a valid 14-tile Riichi mahjong hand with at least one yaku."""
    for _ in range(1000):
        # Pick a random yaku type to generate
        yaku_type = random.randint(0, 5)

        if yaku_type == 0:
            hand = _generate_tanyao()
        elif yaku_type == 1:
            hand = _generate_yakuhai()
        elif yaku_type == 2:
            hand = _generate_toitoi()
        elif yaku_type == 3:
            hand = _generate_chiitoitsu()
        elif yaku_type == 4:
            hand = _generate_iipeikou()
        else:
            hand = _generate_mixed()

        if hand and len(hand) == 14 and has_yaku(hand):
            # Make last tile the "winning tile" (ensure it's not just part of a sorted pair)
            return hand
    return _generate_tanyao() or _generate_chiitoitsu()


def _generate_tanyao():
    """Generate a tanyao (all simples 2-8, no honors) hand."""
    suit_counts = {"w": 0, "p": 0, "s": 0}
    total = 0
    suits = random.sample("wps", random.randint(1, 3))
    for s in suits:
        suit_counts[s] = random.randint(4, 8)
        total += suit_counts[s]
    # Trim to 14
    while total > 14:
        s = random.choice(suits)
        if suit_counts[s] > 4:
            suit_counts[s] -= 1
            total -= 1
    while total < 14:
        s = random.choice(suits)
        suit_counts[s] += 1
        total += 1

    tiles = []
    for s in suits:
        for _ in range(suit_counts[s]):
            tiles.append((s, random.randint(2, 8)))

    random.shuffle(tiles)
    return _make_winning_hand(tiles)


def _generate_yakuhai():
    """Generate a hand with at least one yakuhai (honor triplet)."""
    tiles = []
    # Add a honor triplet
    honor = random.randint(1, 7)
    for _ in range(3):
        tiles.append(("z", honor))
    # Fill rest with numeric tiles
    for _ in range(11):
        s = random.choice("wps")
        tiles.append((s, random.randint(1, 9)))
    random.shuffle(tiles)
    return _make_winning_hand(tiles[:14])


def _generate_toitoi():
    """Generate a toitoi (4 triplets + 1 pair) hand."""
    tiles = []
    # 4 triplets
    for _ in range(4):
        s = random.choice("wpsz")
        n = random.randint(1, 9) if s != "z" else random.randint(1, 7)
        for _ in range(3):
            tiles.append((s, n))
    # 1 pair  
    s = random.choice("wpsz")
    n = random.randint(1, 9) if s != "z" else random.randint(1, 7)
    for _ in range(2):
        tiles.append((s, n))
    random.shuffle(tiles)
    return tiles


def _generate_chiitoitsu():
    """Generate a chiitoitsu (7 pairs) hand."""
    tiles = []
    used = set()
    for _ in range(7):
        while True:
            s = random.choice("wpsz")
            n = random.randint(1, 9) if s != "z" else random.randint(1, 7)
            key = (s, n)
            if key not in used:
                used.add(key)
                break
        tiles.append((s, n))
        tiles.append((s, n))
    random.shuffle(tiles)
    return tiles


def _generate_iipeikou():
    """Generate an iipeikou (two identical sequences) hand."""
    suit = random.choice("wps")
    start = random.randint(1, 7)
    seq = [start, start+1, start+2]

    tiles = []
    # Two identical sequences
    for _ in range(2):
        for n in seq:
            tiles.append((suit, n))

    # Fill the rest (8 more tiles = one pair + 2 melds)
    # Add a pair
    p_suit = random.choice("wpsz")
    p_n = random.randint(1, 9) if p_suit != "z" else random.randint(1, 7)
    tiles.append((p_suit, p_n))
    tiles.append((p_suit, p_n))

    # Add 6 more tiles as triplets or chi
    for _ in range(6):
        s2 = random.choice("wpsz")
        n2 = random.randint(1, 9) if s2 != "z" else random.randint(1, 7)
        tiles.append((s2, n2))

    random.shuffle(tiles)
    return _make_winning_hand(tiles[:14])


def _generate_mixed():
    """Generate a random hand that might have a yaku."""
    tiles = []
    for _ in range(14):
        s = random.choice("wpsz")
        n = random.randint(1, 9) if s != "z" else random.randint(1, 7)
        tiles.append((s, n))
    return _make_winning_hand(tiles)


def _make_winning_hand(tiles):
    """Ensure last tile is the 'winning tile' by putting it out of order."""
    if len(tiles) < 14:
        return None
    # Sort first 13 tiles by suit then number
    suit_order = {"w": 0, "p": 1, "s": 2, "z": 3}
    first13 = sorted(tiles[:13], key=lambda t: (suit_order.get(t[0], 99), t[1]))
    return first13 + [tiles[13]]


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


def compare_guess(guess_tiles, target_tiles):
    """Compare guess with target using tile counts (set-based, not positional).
    - Green: you have this tile, within the correct count
    - Yellow: tile is in target, but you have too many of this type
    - Gray: tile is not in the target at all
    """
    target_counts = {}
    for t in target_tiles:
        target_counts[t] = target_counts.get(t, 0) + 1

    guess_counts = {}
    for t in guess_tiles:
        guess_counts[t] = guess_counts.get(t, 0) + 1

    correct_remaining = {}
    for t, c in guess_counts.items():
        correct_remaining[t] = min(c, target_counts.get(t, 0))

    result = []
    for g in guess_tiles:
        if correct_remaining.get(g, 0) > 0:
            result.append((g, "correct"))
            correct_remaining[g] -= 1
        elif g in target_counts:
            result.append((g, "present"))
        else:
            result.append((g, "absent"))

    return result
