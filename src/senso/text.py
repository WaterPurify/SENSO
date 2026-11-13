"""한국어 문장 도우미."""

_PAIRS = {"을": "를", "이": "가", "은": "는", "과": "와", "으로": "로"}


def _has_final_consonant(word: str) -> bool | None:
    """마지막 글자에 받침이 있는지. 한글이 아니면 None."""
    for ch in reversed(word.strip()):
        if ch in "'\")]」』 ":
            continue
        code = ord(ch) - 0xAC00
        if 0 <= code < 11172:
            return code % 28 != 0
        if ch.isdigit():
            return ch in "013678"  # 영, 일, 삼, 육, 칠, 팔
        return None
    return None


def quote(word: str) -> str:
    return f"'{word}'"


def josa(word: str, with_final: str) -> str:
    """단어 뒤에 알맞은 조사를 붙인다. josa('원두', '을') → '원두를'.

    받침을 판단할 수 없으면 '을(를)'처럼 둘 다 적는다.
    """
    without_final = _PAIRS[with_final]
    final = _has_final_consonant(word)
    if final is None:
        return f"{word}{with_final}({without_final})"
    if with_final == "으로" and word.strip()[-1:] and (ord(word.strip()[-1]) - 0xAC00) % 28 == 8:
        return f"{word}로"  # ㄹ 받침은 '로'
    return f"{word}{with_final if final else without_final}"
