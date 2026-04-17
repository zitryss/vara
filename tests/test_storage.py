from datetime import datetime, timezone

from bot.storage import MessageStorage


def test_add_and_get_messages():
    storage = MessageStorage()
    storage.add(1, "Alice", "Hello", datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc))
    storage.add(1, "Bob", "Hi there", datetime(2026, 4, 17, 10, 1, tzinfo=timezone.utc))

    messages = storage.get_and_clear(1)

    assert len(messages) == 2
    assert messages[0]["sender"] == "Alice"
    assert messages[0]["text"] == "Hello"
    assert messages[1]["sender"] == "Bob"
    assert messages[1]["text"] == "Hi there"


def test_get_and_clear_empties_buffer():
    storage = MessageStorage()
    storage.add(1, "Alice", "Hello", datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc))

    storage.get_and_clear(1)
    messages = storage.get_and_clear(1)

    assert messages == []


def test_is_empty_returns_true_for_new_group():
    storage = MessageStorage()

    assert storage.is_empty(999) is True


def test_is_empty_returns_false_after_add():
    storage = MessageStorage()
    storage.add(1, "Alice", "Hello", datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc))

    assert storage.is_empty(1) is False


def test_is_empty_returns_true_after_clear():
    storage = MessageStorage()
    storage.add(1, "Alice", "Hello", datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc))

    storage.get_and_clear(1)

    assert storage.is_empty(1) is True


def test_multiple_groups_are_independent():
    storage = MessageStorage()
    storage.add(1, "Alice", "Group 1 msg", datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc))
    storage.add(2, "Bob", "Group 2 msg", datetime(2026, 4, 17, 10, 0, tzinfo=timezone.utc))

    messages_1 = storage.get_and_clear(1)
    messages_2 = storage.get_and_clear(2)

    assert len(messages_1) == 1
    assert messages_1[0]["sender"] == "Alice"
    assert len(messages_2) == 1
    assert messages_2[0]["sender"] == "Bob"
