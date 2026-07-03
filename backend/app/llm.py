"""Anthropic 客户端工厂 + 调用/解析辅助 + 模型分工常量。

密钥从 settings.anthropic_api_key（env / .env）读取，绝不硬编码。
JSON 输出采用「提示要求 JSON + 稳健解析」而非版本相关的 output_config，跨 SDK 版本更稳。
"""

import json
import re
from functools import lru_cache

import anthropic

from .config import settings

# DESIGN 模型分工：清洗/分类/语义合规 → Haiku；生成/评审/去AI味 → Sonnet 或 Opus；快线 → Sonnet。
MODEL_HAIKU = "claude-haiku-4-5"
MODEL_SONNET = "claude-sonnet-5"
MODEL_OPUS = "claude-opus-4-8"

# Opus/Sonnet 4.7+ 仅支持 adaptive thinking；生成任务默认关思考以省钱提速（Haiku 不传 thinking）。
_THINKING_TOGGLE = {MODEL_SONNET, MODEL_OPUS}

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


@lru_cache
def get_client() -> anthropic.Anthropic:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY 未配置（见 backend/.env）")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def call_text(
    model: str,
    system: str,
    user: str,
    max_tokens: int = 1024,
    disable_thinking: bool = True,
) -> tuple[str, dict]:
    """发一次请求，返回 (纯文本, {model, input, output})。"""
    kwargs: dict = {}
    if disable_thinking and model in _THINKING_TOGGLE:
        kwargs["thinking"] = {"type": "disabled"}
    resp = get_client().messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        **kwargs,
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    usage = {"model": model, "input": resp.usage.input_tokens, "output": resp.usage.output_tokens}
    return text, usage


def parse_json(text: str):
    """从模型输出稳健提取 JSON（容忍 ```json 代码围栏、前后噪声）。失败抛 ValueError。"""
    cleaned = _FENCE.sub("", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # 回退：截取第一个 { 或 [ 到最后一个 } 或 ]
    starts = [i for i in (cleaned.find("{"), cleaned.find("[")) if i != -1]
    ends = [i for i in (cleaned.rfind("}"), cleaned.rfind("]")) if i != -1]
    if starts and ends:
        snippet = cleaned[min(starts) : max(ends) + 1]
        return json.loads(snippet)
    raise ValueError(f"无法解析 JSON：{text[:200]}")


def call_json(model: str, system: str, user: str, max_tokens: int = 1024) -> tuple[object, dict]:
    """call_text + parse_json。返回 (解析后的对象, usage)。"""
    text, usage = call_text(model, system, user, max_tokens=max_tokens)
    return parse_json(text), usage


def verify_key() -> dict:
    """最小连通性自检：对 Haiku 发 1 token 请求。返回 {ok, model?/error?}。"""
    try:
        resp = get_client().messages.create(
            model=MODEL_HAIKU, max_tokens=1, messages=[{"role": "user", "content": "hi"}]
        )
        return {"ok": True, "model": resp.model}
    except anthropic.AuthenticationError:
        return {"ok": False, "error": "认证失败：API Key 无效"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
