"""合规引擎：禁词硬拦截（M6 第 1 层）+ 软提示，产出 pass/soft/blocked 三态。

与前端 Variant 的三态模型一致：
- blocked：命中禁词 → 该文案不通过（真实生成时触发定向改写，见 M6）。
- soft   ：命中软提示 → 交人工判断，返回首个命中句 + 命中句数（对应 softFlagSentence/softFlagCount）。
- pass   ：均未命中。
"""

import re
from dataclasses import dataclass, field

from .rules import BANNED_WORDS, SOFT_FLAG_WORDS, normalize

# 句子切分：印尼语/中文常见句末标点 + 换行。
_SENTENCE_SPLIT = re.compile(r"[^.!?。！？\n]+[.!?。！？]?", re.UNICODE)


@dataclass
class ComplianceResult:
    status: str  # 'pass' | 'soft' | 'blocked'
    banned_hits: list[str] = field(default_factory=list)
    soft_flag_sentence: str | None = None
    soft_flag_count: int = 0
    soft_hits: list[str] = field(default_factory=list)


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.findall(text) if s.strip()]


def _find_terms(haystack_norm: str, terms: list[str]) -> list[str]:
    return [t for t in terms if t in haystack_norm]


def scan_compliance(text: str) -> ComplianceResult:
    """扫描一段文案，返回三态合规结果。"""
    norm_full = normalize(text)

    # 第 1 层：禁词硬拦截 —— 命中即 blocked（优先级最高）。
    banned = _find_terms(norm_full, BANNED_WORDS)
    if banned:
        return ComplianceResult(status="blocked", banned_hits=sorted(set(banned)))

    # 软提示：逐句扫描，记录命中句，返回首个命中句 + 命中句数。
    sentences = _split_sentences(text) or [text.strip()]
    flagged_sentences: list[str] = []
    all_soft_hits: list[str] = []
    for sent in sentences:
        hits = _find_terms(normalize(sent), SOFT_FLAG_WORDS)
        if hits:
            flagged_sentences.append(sent)
            all_soft_hits.extend(hits)

    if flagged_sentences:
        return ComplianceResult(
            status="soft",
            soft_flag_sentence=flagged_sentences[0],
            soft_flag_count=len(flagged_sentences),
            soft_hits=sorted(set(all_soft_hits)),
        )

    return ComplianceResult(status="pass")
