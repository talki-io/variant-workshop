"""内部合规自检端点：把规则层合规引擎 + 抗注入检测暴露成可调用工具。

用途：素材员/管理员对任意文案做即时三态合规自检 + 抗注入体检（登录即可）。
不在前端固定契约内，前端暂不调用；接 AI 管线后 M6 会内部复用同一 engine。
"""

from fastapi import APIRouter, Depends

from ..compliance import detect_injection, sanitize_untrusted, scan_compliance
from ..models import User
from ..schemas import ComplianceCheckIn, ComplianceCheckOut
from ..security import get_current_user

router = APIRouter(prefix="/api", tags=["compliance"])


@router.post("/compliance/check", response_model=ComplianceCheckOut)
def check(body: ComplianceCheckIn, _: User = Depends(get_current_user)) -> ComplianceCheckOut:
    result = scan_compliance(body.text)
    injection = detect_injection(body.text)
    return ComplianceCheckOut(
        status=result.status,
        banned_hits=result.banned_hits,
        soft_flag_sentence=result.soft_flag_sentence,
        soft_flag_count=result.soft_flag_count,
        soft_hits=result.soft_hits,
        injection_detected=bool(injection),
        injection_patterns=injection,
        sanitized_text=sanitize_untrusted(body.text),
    )
