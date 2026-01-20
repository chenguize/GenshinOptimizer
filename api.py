# api.py
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from typing import List, Dict, Any, Optional

# 导入修正后的 models
from models import CharacterData, CalculationRequest

app = FastAPI(title="Genshin Calc API - Dynamic Meta")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 路径配置 ---
CHAR_DATA_PATH = "data/rules/characters.json"
SET_EFFECTS_PATH = "data/rules/set_effects.json"


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --- 🟢 核心辅助：清洗数据 ---
def get_safe_character_data(char_dict: dict) -> dict:
    """
    即使 char_dict 是空的 {}，也能通过 Pydantic 补全所有默认字段
    """
    try:
        # 如果 char_dict 为 None 或无效，使用空字典触发模型默认值
        input_data = char_dict if char_dict else {}
        model = CharacterData.parse_obj(input_data)
        # 🟢 铁律：by_alias=True 保证输出 "def", "NormalAttack" 等符合前端要求的键名
        return model.dict(by_alias=True)
    except Exception as e:
        print(f"[Error] 解析角色数据失败，返回空白模型: {e}")
        return CharacterData().dict(by_alias=True)


@app.get("/api/meta")
async def get_meta_data():
    """
    🟢 动态元数据接口
    不再返回死数据的 artifact_sets，而是读取 set_effects.json 的所有 Key。
    """
    # 1. 读取已配置的套装 (Warehouse 中保存的)
    configured_sets_map = load_json(SET_EFFECTS_PATH)
    configured_set_names = list(configured_sets_map.keys())

    # 2. 默认建议套装 (用于新建套装时的自动补全建议，可选保留常用列表)
    suggestions = [
        "绝缘之旗印", "深林的记忆", "饰金之梦", "逐影猎人", "黄金剧团",
        "昔时之歌", "回声之林夜话", "黑曜秘典", "烬城勇者卷绘"
    ]

    # 3. 合并列表并去重 (前端下拉框显示的列表)
    # 优先显示已配置的，再显示建议的
    all_sets = sorted(list(set(configured_set_names + suggestions)))

    return {
        "skill_types": {
            "NormalAttack": "普通攻击",
            "ChargedAttack": "重击",
            "PlungingAttack": "下落攻击",
            "ElementalSkill": "元素战技",
            "ElementalBurst": "元素爆发"
        },
        "elements": {
            "Pyro": "火", "Hydro": "水", "Electro": "雷", "Cryo": "冰",
            "Dendro": "草", "Anemo": "风", "Geo": "岩", "Physical": "物理"
        },
        "reactions": {
            "vaporize": "蒸发", "melt": "融化",
            "aggravate": "超激化", "spread": "蔓激化",
            "MoonBloom": "月绽放",
            "MoonElectro": "月感电",
            "": "无反应"
        },
        # 🟢 动态列表
        "artifact_sets": all_sets,
        "set_suggestions": suggestions,  # 给 Warehouse 用
        "buff_types": [
            {"value": "atk_percent", "label": "攻击力%"},
            {"value": "hp_percent", "label": "生命值%"},
            {"value": "em", "label": "元素精通"},
            {"value": "crit_rate", "label": "暴击率"},
            {"value": "crit_dmg", "label": "暴击伤害"},
            {"value": "energy_recharge_bonus", "label": "元素充能"}
        ]
    }


@app.get("/api/characters/list")
async def get_character_list():
    chars = load_json(CHAR_DATA_PATH)
    # 简单列表不需要校验，直接返回 ID 和 Label
    return [{"id": k, "label": k} for k in chars.keys()]


@app.get("/api/characters/{char_id}")
async def get_character_detail(char_id: str):
    chars = load_json(CHAR_DATA_PATH)
    if char_id not in chars:
        # 返回默认空对象而不是 404，这样前端可以进入编辑模式
        print(f"Character {char_id} not found, returning default.")
        return CharacterData().dict(by_alias=True)

    # 🟢 经过清洗的数据
    return get_safe_character_data(chars[char_id])


@app.post("/api/characters/{char_id}")
async def save_character(char_id: str, data: CharacterData, old_id: Optional[str] = Query(None)):
    """接收前端发来的数据 (Rust 已对齐模型)，保存到文件"""
    chars = load_json(CHAR_DATA_PATH)

    # 处理重命名
    if old_id and old_id != char_id and old_id in chars:
        del chars[old_id]

    # 转为 dict 并使用 alias (def, NormalAttack 等)
    chars[char_id] = data.dict(by_alias=True)
    save_json(CHAR_DATA_PATH, chars)
    return {"status": "success"}


@app.post("/api/calculate")
async def calculate_damage(req: CalculationRequest):
    try:
        from main import run_optimizer, print_result_cli
        result_data = run_optimizer(
            target_char=req.target_char,
            teammates=req.teammates,
            skill_type=req.skill_type,
            reaction=req.reaction if req.reaction else None,  # 空串转 None
            forced_set=req.forced_set
        )
        # 可以在服务器控制台打印结果方便调试
        # print_result_cli(result_data)
        return result_data
    except Exception as e:
        import traceback
        traceback.print_exc()
        # 返回 500 详情
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rules/set_effects")
async def get_set_effects():
    """获取所有圣遗物套装配置"""
    # SET_EFFECTS_PATH 在文件开头已经定义为 "data/rules/set_effects.json"
    data = load_json(SET_EFFECTS_PATH)
    return data

@app.post("/api/rules/set_effects")
async def save_set_effects(data: dict = Body(...)):
    """保存圣遗物套装配置"""
    save_json(SET_EFFECTS_PATH, data)
    return {"status": "success"}
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)