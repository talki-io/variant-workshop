"""Anthropic 客户端工厂 + 调用/解析辅助 + 模型分工常量。

密钥从 settings.anthropic_api_key（env / .env）读取，绝不硬编码。
JSON 输出采用「提示要求 JSON + 稳健解析」而非版本相关的 output_config，跨 SDK 版本更稳。
"""

import json
import re
from dataclasses import dataclass
from functools import lru_cache

import anthropic
import httpx

from .config import settings

# DESIGN 模型分工：清洗/分类/语义合规 → Haiku；生成/评审/去AI味 → Sonnet 或 Opus；快线 → Sonnet。
MODEL_HAIKU = "claude-haiku-4-5"
MODEL_SONNET = "claude-sonnet-5"
MODEL_OPUS = "claude-opus-4-8"

# 已知 Anthropic 模型（新装模型库默认灌这几个；管理员可增补其他厂商）
KNOWN_MODELS = [
    {"id": MODEL_HAIKU, "name": "Haiku 4.5（快·省）"},
    {"id": MODEL_SONNET, "name": "Sonnet 5（均衡·主力）"},
    {"id": MODEL_OPUS, "name": "Opus 4.8（最强·贵）"},
]

PROVIDERS = ["anthropic", "openai"]  # openai = OpenAI 兼容（含各厂商/中转）

# Opus/Sonnet 4.7+ 仅支持 adaptive thinking；生成任务默认关思考以省钱提速（Haiku 不传 thinking）。
_THINKING_TOGGLE = {MODEL_SONNET, MODEL_OPUS}


@dataclass(frozen=True)
class ModelSpec:
    """一个可调用模型的完整定义（来自模型库 llm_model 行，或内置默认）。"""

    provider: str  # anthropic | openai
    model_id: str  # 厂商裸模型串
    base_url: str | None = None
    api_key: str | None = None
    name: str = ""


# —— 各场景内置默认（DB 无配置时回退，保证离线/空库仍可跑）——
_DEFAULT_SPECS: dict[str, ModelSpec] = {
    "generate": ModelSpec("anthropic", MODEL_SONNET, name="Sonnet 5"),
    "clean": ModelSpec("anthropic", MODEL_HAIKU, name="Haiku 4.5"),
    "compliance": ModelSpec("anthropic", MODEL_HAIKU, name="Haiku 4.5"),
}
_DEFAULT_MAX = {"generate": 3600, "clean": 4000, "compliance": 600}
_model_cache: dict[str, dict] = {}


def refresh_model_config(db) -> None:
    """从 DB 载入各场景绑定的模型（join 模型库）到进程缓存（启动 + 每次保存后调用）。"""
    global _model_cache
    from sqlalchemy import select

    from .models import LlmModel, ModelConfig

    models = {m.id: m for m in db.scalars(select(LlmModel))}
    cache: dict[str, dict] = {}
    for r in db.scalars(select(ModelConfig)):
        m = models.get(r.model_id)
        spec = ModelSpec(m.provider, m.model_id, m.base_url, m.api_key, m.name) if m else None
        cache[r.scene] = {"spec": spec, "max_tokens": r.max_tokens, "temperature": r.temperature,
                          "enabled": r.enabled and (m.enabled if m else True)}
    _model_cache = cache


def scene_spec(scene: str) -> ModelSpec:
    c = _model_cache.get(scene)
    if c and c.get("enabled", True) and c.get("spec"):
        return c["spec"]
    return _DEFAULT_SPECS.get(scene, _DEFAULT_SPECS["generate"])


def scene_max_tokens(scene: str, override: int | None = None) -> int:
    if override is not None:
        return override
    c = _model_cache.get(scene)
    if c and c.get("max_tokens"):
        return c["max_tokens"]
    return _DEFAULT_MAX.get(scene, 1024)


def scene_temperature(scene: str) -> float | None:
    c = _model_cache.get(scene)
    return c.get("temperature") if c else None

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


@lru_cache
def get_client() -> anthropic.Anthropic:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY 未配置（见 backend/.env）")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


@lru_cache
def _anthropic_client(api_key: str, base_url: str | None) -> anthropic.Anthropic:
    kw = {"api_key": api_key}
    if base_url:
        kw["base_url"] = base_url
    return anthropic.Anthropic(**kw)


def _call_anthropic(spec: ModelSpec, system: str, user: str, max_tokens: int,
                    disable_thinking: bool, temperature: float | None) -> tuple[str, dict]:
    key = spec.api_key or settings.anthropic_api_key
    if not key:
        raise RuntimeError("Anthropic API Key 未配置")
    client = _anthropic_client(key, spec.base_url)
    kwargs: dict = {}
    if disable_thinking and spec.model_id in _THINKING_TOGGLE:
        kwargs["thinking"] = {"type": "disabled"}
    if temperature is not None:
        kwargs["temperature"] = temperature
    resp = client.messages.create(
        model=spec.model_id, max_tokens=max_tokens, system=system,
        messages=[{"role": "user", "content": user}], **kwargs,
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return text, {"model": spec.model_id, "input": resp.usage.input_tokens, "output": resp.usage.output_tokens}


def _call_openai(spec: ModelSpec, system: str, user: str, max_tokens: int,
                 temperature: float | None) -> tuple[str, dict]:
    """OpenAI 兼容 /chat/completions（覆盖 OpenAI/DeepSeek/Kimi/Qwen/Gemini兼容端点/各类中转）。"""
    if not spec.api_key:
        raise RuntimeError(f"模型「{spec.name or spec.model_id}」未配置 API Key")
    base = (spec.base_url or "https://api.openai.com/v1").rstrip("/")
    body: dict = {
        "model": spec.model_id,
        "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    if temperature is not None:
        body["temperature"] = temperature
    r = httpx.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {spec.api_key}", "Content-Type": "application/json"},
        json=body, timeout=90,
    )
    r.raise_for_status()
    data = r.json()
    text = (data["choices"][0]["message"].get("content") or "").strip()
    u = data.get("usage") or {}
    return text, {"model": spec.model_id, "input": u.get("prompt_tokens", 0), "output": u.get("completion_tokens", 0)}


def call_text(
    model: "ModelSpec | str",
    system: str,
    user: str,
    max_tokens: int = 1024,
    disable_thinking: bool = True,
    temperature: float | None = None,
) -> tuple[str, dict]:
    """发一次请求，返回 (纯文本, {model, input, output})。

    model 传 ModelSpec 时按其 provider 分发；传裸串时按 Anthropic 处理（向后兼容）。
    """
    spec = model if isinstance(model, ModelSpec) else ModelSpec("anthropic", model, name=model)
    if spec.provider == "openai":
        return _call_openai(spec, system, user, max_tokens, temperature)
    return _call_anthropic(spec, system, user, max_tokens, disable_thinking, temperature)


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


def call_json(
    model: "ModelSpec | str", system: str, user: str, max_tokens: int = 1024, temperature: float | None = None
) -> tuple[object, dict]:
    """call_text + parse_json。返回 (解析后的对象, usage)。"""
    text, usage = call_text(model, system, user, max_tokens=max_tokens, temperature=temperature)
    return parse_json(text), usage


def verify_model(spec: ModelSpec) -> dict:
    """对指定模型发 1 次极小请求做连通性自检。返回 {ok, model?/error?}。"""
    try:
        _text, _u = call_text(spec, "只回一个字。", "hi", max_tokens=4)
        return {"ok": True, "model": spec.model_id}
    except anthropic.AuthenticationError:
        return {"ok": False, "error": "认证失败：API Key 无效"}
    except httpx.HTTPStatusError as e:
        return {"ok": False, "error": f"HTTP {e.response.status_code}：{e.response.text[:120]}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def verify_key() -> dict:
    """默认 Anthropic（.env key）连通性自检。"""
    return verify_model(_DEFAULT_SPECS["compliance"])
