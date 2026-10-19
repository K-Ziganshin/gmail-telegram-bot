import pytest

from mailbot.mail_filter import classify


@pytest.mark.parametrize(
    ("subject", "snippet", "expected"),
    [
        ("Скидки на заказ", "", "important"),  # important wins over unwanted
        ("Распродажа", "", "unwanted"),
        ("Привет", "как дела", "ignored"),
        ("Ваш КОД подтверждения", "", "important"),  # case-insensitive
        ("Weekly digest", "click to unsubscribe", "unwanted"),
    ],
)
def test_classify(subject, snippet, expected):
    assert classify(subject, snippet) == expected
