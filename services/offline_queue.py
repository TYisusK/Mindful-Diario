# services/offline_queue.py
import json

QUEUE_KEY = "offline_action_queue"


def _get_storage(page):
    # En web esto es localStorage; funciona sin conexión
    return page.client_storage


def _load_list(page):
    storage = _get_storage(page)
    raw = storage.get(QUEUE_KEY) or "[]"
    try:
        return json.loads(raw)
    except Exception:
        return []


def _save_list(page, data):
    storage = _get_storage(page)
    storage.set(QUEUE_KEY, json.dumps(data))


def queue_action(page, action: dict):
    """
    action debe tener al menos:
    {
      "type": "note" | "diagnostic" | ...,
      "payload": {...},
      "uid": "user-id-opcional"
    }
    """
    lst = _load_list(page)
    lst.append(action)
    _save_list(page, lst)


def peek_all(page):
    return _load_list(page)


def pop_all(page):
    lst = _load_list(page)
    _save_list(page, [])
    return lst


def has_pending(page) -> bool:
    return len(_load_list(page)) > 0
