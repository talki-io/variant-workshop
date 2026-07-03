"""合规层（规则部分，无需模型/样本）。

DESIGN §3 M6-3 三层合规的第 1 层（禁词硬拦截）与软提示，以及 P0-2 抗注入。
第 2 层（Haiku 语义合规）留到接 Anthropic 那一轮，直接调用 engine 里的接口拼装。

对外主要接口：
- engine.scan_compliance(text) -> ComplianceResult（pass/soft/blocked + 命中详情）
- injection.detect_injection / sanitize_untrusted / wrap_untrusted
"""

from .engine import ComplianceResult, scan_compliance
from .injection import detect_injection, sanitize_untrusted, wrap_untrusted
from .semantic import merge_status, semantic_check_batch

__all__ = [
    "ComplianceResult",
    "scan_compliance",
    "detect_injection",
    "sanitize_untrusted",
    "wrap_untrusted",
    "merge_status",
    "semantic_check_batch",
]
