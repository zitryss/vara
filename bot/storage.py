from datetime import datetime


class MessageStorage:
    def __init__(self) -> None:
        self._buffers: dict[int, list[dict]] = {}

    def add(self, group_id: int, sender: str, text: str, timestamp: datetime) -> None:
        if group_id not in self._buffers:
            self._buffers[group_id] = []
        self._buffers[group_id].append({
            "sender": sender,
            "text": text,
            "timestamp": timestamp,
        })

    def get_and_clear(self, group_id: int) -> list[dict]:
        return self._buffers.pop(group_id, [])

    def is_empty(self, group_id: int) -> bool:
        return len(self._buffers.get(group_id, [])) == 0
