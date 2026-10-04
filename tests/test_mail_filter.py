from mail_filter import classify


def test_important_wins_over_unwanted():
    assert classify("Скидки на заказ", "") == "important"


def test_unwanted_and_ignored():
    assert classify("Распродажа", "") == "unwanted"
    assert classify("Привет", "как дела") == "ignored"
