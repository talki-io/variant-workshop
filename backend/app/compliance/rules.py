"""可维护的合规规则资产（禁词 / 软提示词表）。

面向印尼股市荐股营销文案 + OJK 监管语境。词条以**小写归一化**后做子串匹配。
维护约定：
- BANNED（硬拦截）= 明确违规：收益/涨幅保证、无风险承诺、内幕/操纵暗示。命中即 blocked。
- SOFT（软提示）= 需人工判断：FOMO 煽动、未证实的机构/内幕断言、过度催促。命中即 soft。
- 优先保守（宁可 soft 交人判断），硬拦截只放确凿违规，避免误杀正常财经表述。

下一轮接 Haiku 语义合规（第 2 层）时，这两张表继续作为「确定性护栏」保留，
语义层只补规则覆盖不到的隐性表达。
"""

# —— 硬拦截：收益 / 涨幅 / 无风险保证 ——
_BANNED_GUARANTEE = [
    "dijamin untung", "dijamin profit", "dijamin cuan", "dijamin naik", "dijamin balik modal",
    "pasti untung", "pasti profit", "pasti cuan", "pasti naik", "pasti terbang", "pasti jp",
    "untung pasti", "profit pasti", "cuan pasti", "naik pasti",
    "auto cuan", "auto profit", "auto untung", "auto jp",
    "tanpa risiko", "bebas risiko", "nol risiko", "risk free", "no risk",
    "100% untung", "100% profit", "100% cuan", "100% naik",
    "sudah pasti naik", "sudah pasti untung", "guaranteed profit", "guaranteed return",
    "balik modal pasti", "pasti balik modal",
]

# —— 硬拦截：内幕 / 操纵暗示 ——
_BANNED_INSIDER = [
    "info orang dalam", "bocoran orang dalam", "kabar orang dalam", "insider info",
    "ikut bandar dijamin", "ikut bandar pasti", "bandar pasti naik", "sinyal orang dalam pasti",
    "goreng saham pasti", "pom pom pasti",
]

BANNED_WORDS: list[str] = _BANNED_GUARANTEE + _BANNED_INSIDER

# —— 软提示：FOMO / 未证实断言 / 过度催促（需人工判断，不必然违规）——
SOFT_FLAG_WORDS: list[str] = [
    # FOMO / 错过恐惧
    "jangan sampai ketinggalan", "siap-siap ketinggalan", "ketinggalan kereta",
    "jangan jadi penonton", "nyesel kalau", "menyesal kalau", "menyesal seumur hidup",
    "kesempatan terakhir", "sebelum terlambat", "sebelum kehabisan", "buruan sebelum",
    # 未证实的机构 / 内幕断言（软）
    "institusi jelas", "bandar sudah masuk", "orang dalam tau", "semua sudah tau",
    "smart money masuk", "asing borong",
    # 过度催促
    "beli sekarang juga", "sekarang atau tidak sama sekali", "detik ini juga",
]


def normalize(text: str) -> str:
    """匹配前归一化：小写 + 折叠连续空白。"""
    return " ".join(text.lower().split())
