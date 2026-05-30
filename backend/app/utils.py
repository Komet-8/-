"""通用小工具。"""
from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def extract_json(text: str) -> Any:
    """从可能含有 markdown 代码块 / 多余文字的模型输出里抠出 JSON。

    解析失败时抛出 ValueError。
    """
    if not text:
        raise ValueError("empty text")

    # 1) 优先解析 ```json ... ``` 代码块
    m = _FENCE_RE.search(text)
    candidates = [m.group(1)] if m else []
    candidates.append(text)

    # 2) 退而求其次：截取第一个 { 或 [ 到最后一个 } 或 ]
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end != -1 and end > start:
            candidates.append(text[start : end + 1])

    for c in candidates:
        try:
            return json.loads(c)
        except (json.JSONDecodeError, TypeError):
            continue
    raise ValueError(f"无法从输出中解析 JSON: {text[:200]!r}")
