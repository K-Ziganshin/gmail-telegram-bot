from mailbot.processing import header, process_unread


def gmail_message(subject, sender="Shop <shop@example.com>", snippet=""):
    return {
        "snippet": snippet,
        "payload": {"headers": [{"name": "Subject", "value": subject}, {"name": "From", "value": sender}]},
    }


class FakeBox:
    def __init__(self, messages):
        self.messages = messages
        self.read, self.trashed, self.pauses = [], [], 0

    def unread_ids(self):
        return list(self.messages)

    def get(self, msg_id):
        return self.messages[msg_id]

    def mark_read(self, msg_id):
        self.read.append(msg_id)

    def trash(self, msg_id):
        self.trashed.append(msg_id)

    def pause(self, seconds):
        self.pauses += 1


def test_actions_per_category():
    box = FakeBox(
        {"a": gmail_message("Оплата заказа"), "b": gmail_message("Большая распродажа"), "c": gmail_message("Привет")}
    )
    report = process_unread(box)
    assert box.read == ["a"]
    assert box.trashed == ["b"]
    assert report.counts == {"important": 1, "unwanted": 1, "ignored": 1}
    assert [m.subject for m in report.important] == ["Оплата заказа"]
    assert box.pauses == 3


def test_ignored_mail_is_left_untouched():
    box = FakeBox({"x": gmail_message("Просто письмо")})
    process_unread(box)
    assert box.read == [] and box.trashed == []


def test_empty_inbox():
    assert process_unread(FakeBox({})).mails == []


def test_header_lookup_is_case_insensitive_and_safe():
    msg = {"payload": {"headers": [{"name": "subject", "value": "Hi"}]}}
    assert header(msg, "Subject") == "Hi"
    assert header(msg, "From") == ""
    assert header({}, "Subject") == ""
