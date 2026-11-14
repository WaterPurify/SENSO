"""너무 흔하거나 추측하기 쉬운 비밀번호 거르기.

외부 목록을 내려받지 않고, 유출 목록 상위에 늘 나오는 낱말과 규칙으로 막는다.
길이 규칙(12~128자)은 auth.py가 따로 검사한다.
"""

import re

# 유출 비밀번호 목록 상위에 자주 나오는 낱말 (소문자). 앞뒤 숫자·기호를 떼고 비교한다.
COMMON_WORDS = frozenset(
    """
    password passw0rd pass passwd qwerty qwert asdf asdfgh zxcvbn iloveyou loveyou love
    admin administrator root user guest login welcome letmein hello hi test test1 testtest
    secret master monkey dragon shadow sunshine princess football baseball soccer superman
    batman trustno1 starwars whatever freedom computer internet samsung apple google naver
    kakao korea seoul busan sarang saranghae saranghaeyo hangul abc abcd abcde abcdef
    qazwsx qweasd qweasdzxc 1q2w3e 1q2w3e4r 1q2w3e4r5t q1w2e3r4 senso sen so coffee tea
    changeme default secure security private mypassword yourpassword nopassword
    """.split()
)

_SEQUENCES = (
    "abcdefghijklmnopqrstuvwxyz",
    "0123456789012345678901234567890",
    "qwertyuiopasdfghjklzxcvbnm",
    "1qaz2wsx3edc4rfv5tgb6yhn7ujm8ik9ol0p",
    "1q2w3e4r5t6y7u8i9o0p",
    "qazwsxedcrfvtgbyhnujmikolp",
)

_EDGE = re.compile(r"^[\d\W_]+|[\d\W_]+$")


def _is_repetition(text: str) -> bool:
    """'abcabcabcabc', 'aaaaaaaaaaaa'처럼 짧은 덩어리를 되풀이한 것."""
    n = len(text)
    return any(n % k == 0 and text[:k] * (n // k) == text for k in range(1, min(6, n // 2) + 1))


def _is_sequence(text: str) -> bool:
    for seq in _SEQUENCES:
        if text in seq * 2 or text in (seq * 2)[::-1]:
            return True
    return False


def weakness(password: str, username: str | None = None) -> str | None:
    """약한 이유를 한국어로. 괜찮으면 None."""
    lowered = password.lower()
    compact = re.sub(r"\s+", "", lowered)
    if username and len(username) >= 3 and username.lower() in compact:
        return "아이디가 들어간 비밀번호는 쓸 수 없어요."
    if len(set(compact)) < 5 or _is_repetition(compact):
        return "같은 글자나 짧은 덩어리를 되풀이한 비밀번호는 쓸 수 없어요."
    if _is_sequence(compact):
        return "1234나 abcd, qwerty처럼 이어진 글자는 쓸 수 없어요."
    core = _EDGE.sub("", compact)
    if not core or core in COMMON_WORDS or _is_repetition(core) or _is_sequence(core):
        return "너무 흔한 비밀번호예요. 여러 낱말을 섞은 문장처럼 만들어 보세요."
    return None
