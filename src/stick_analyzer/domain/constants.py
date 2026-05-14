"""领域算法共享常量。"""

WINDOW_BEFORE_S = 2.0
WINDOW_AFTER_S = 1.5
FIRE_GAP_THRESHOLD_S = 0.4
DEFAULT_MIN_DURATION_S = 0.05
PRE_FIRE_STABILITY_MS = 100
DURING_FIRE_STABILITY_MS = 300

# 常见 FPS 武器的 RPM（rounds per minute）/ 每秒射速。
# 关键词匹配：只要用户填的武器名包含其中一个，就拿对应的 RPM。
WEAPON_RPM = {
    # 高射速冲锋枪
    "r99": 1080, "r-99": 1080, "volt": 720, "alternator": 600,
    "car": 930, "p2020": 420,
    # 步枪 / 突击步枪
    "r301": 810, "r-301": 810, "flatline": 600, "havoc": 672,
    "hemlock": 930, "30-30": 192, "nemesis": 720,
    # 轻机枪
    "spitfire": 540, "rampage": 312, "devotion": 900, "lstar": 600,
    # 霰弹
    "eva": 138, "mastiff": 156, "peacekeeper": 102, "mozambique": 234,
    # 半自动 / DMR
    "g7": 240, "scout": 240, "wingman": 156, "bocek": 162,
    # 拉栓 / 单发
    "kraber": 30, "sentinel": 30, "longbow": 78, "triple": 96,
    # 通用类别词（兜底）
    "smg": 800, "冲锋枪": 800,
    "rifle": 600, "步枪": 600, "突击步枪": 600,
    "lmg": 600, "轻机枪": 600,
    "shotgun": 150, "霰弹": 150, "霰弹枪": 150,
    "dmr": 240, "marksman": 240,
    "sniper": 30, "狙击": 30, "狙击枪": 30, "拉栓": 30,
}


# 分类对应的玩家直觉解释（按从好到差排列）。
CLASSIFICATION_EXPLANATIONS = {
    "完美稳定 ⭐": "教科书级压枪，准星几乎纹丝不动",
    "稳定射击 ✓": "理想状态，压枪稳、命中率高",
    "接近稳定": "基本稳但有微调，实战可用",
    "中等稳定": "能打中但不稳，需要练习",
    "微调跟枪": "远距离精修目标，推杆量很小",
    "开火前抖动 ⚠": "瞄准时手抖，准星没停在敌人身上（曲线低段问题/瞄太久/紧张）",
    "开火中抖动 ⚠": "后坐力没压住，曲线匹配差（中段过陡）",
    "频繁过冲 ⚠": "准星反复修正越过目标，斜率太高",
    "数据不足": "burst 时长太短或采样不足",
}

