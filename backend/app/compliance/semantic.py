"""M6 第 2 层：Haiku 语义合规（补规则层覆盖不到的隐性表达）。

与规则层（禁词/软提示）合并成三态：blocked > soft > pass（取最严）。
语义层不可用时（无 key / 调用异常）降级为 pass，由规则层兜底——绝不因语义层故障放行更严的规则判定。
"""

from ..llm import MODEL_HAIKU, call_json

_SYSTEM = (
    "你是印尼股市营销文案的合规审核员，依印尼 OJK 监管精神审查荐股/理财类文案。"
    "对每条文案判定三档：\n"
    "- blocked：确定违规——收益或涨幅保证、无风险承诺、内幕/操纵暗示、未经许可的明确投资建议。\n"
    "- soft：存在夸大、煽动 FOMO、未证实的机构/内幕断言等需人工判断的表达。\n"
    "- pass：无上述问题。\n"
    "只输出 JSON 数组，每项 {index, status, reason}，index 从 0 起，reason 用中文简述，≤30字。不要输出任何额外文字。"
)

_ORDER = {"pass": 0, "soft": 1, "blocked": 2}


def merge_status(*statuses: str) -> str:
    """取最严的合规状态。"""
    worst = max(statuses, key=lambda s: _ORDER.get(s, 0), default="pass")
    return worst


def semantic_check_batch(texts: list[str]) -> tuple[list[dict], dict | None]:
    """对一批文案做语义合规。返回 (每条 {status, reason}, usage)。异常时全判 pass 并 usage=None。"""
    if not texts:
        return [], None
    numbered = "\n".join(f"[{i}] {t}" for i, t in enumerate(texts))
    try:
        data, usage = call_json(MODEL_HAIKU, _SYSTEM, numbered, max_tokens=600)
        # Haiku 偶尔把数组包在对象里（如 {"results":[...]}），取第一个列表值兜底
        if isinstance(data, dict):
            data = next((v for v in data.values() if isinstance(v, list)), [])
        by_index = {int(item.get("index", i)): item for i, item in enumerate(data)}
        out = []
        for i in range(len(texts)):
            item = by_index.get(i, {})
            status = item.get("status", "pass")
            out.append({
                "status": status if status in _ORDER else "pass",
                "reason": item.get("reason", ""),
            })
        return out, usage
    except Exception:  # noqa: BLE001 —— 语义层降级：交规则层兜底
        return [{"status": "pass", "reason": "语义层不可用"} for _ in texts], None
