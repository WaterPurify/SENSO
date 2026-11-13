import pytest

from senso.text import josa, quote


@pytest.mark.parametrize(
    ("word", "particle", "expected"),
    [
        ("원두", "을", "원두를"),
        ("찻잎", "을", "찻잎을"),
        ("차", "이", "차가"),
        ("'산미 줄이기'", "을", "'산미 줄이기'를"),
        ("'더 진하게'", "을", "'더 진하게'를"),
        ("'제주 세작'", "이", "'제주 세작'이"),
        ("원두", "으로", "원두로"),
        ("차", "으로", "차로"),
        ("물", "으로", "물로"),  # ㄹ 받침
        ("찻잎", "으로", "찻잎으로"),
        ("V60", "을", "V60을"),  # 0(영)은 받침
        ("V62", "을", "V62를"),
        ("Kalita", "을", "Kalita을(를)"),  # 판단할 수 없으면 둘 다
    ],
)
def test_josa(word, particle, expected):
    assert josa(word, particle) == expected


def test_quote():
    assert quote("세작") == "'세작'"
