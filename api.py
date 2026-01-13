from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import sys
import io
from typing import List, Dict, Any, Optional
from models import CharacterData, CalculationRequest, BaseStats

app = FastAPI(title="Genshin Calc API")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = "data/rules/characters.json"

# --- 1. 常量数据 ---
CONSTANTS = {
    "skill_types": {
        "NormalAttack": "普通攻击", "ChargedAttack": "重击",
        "PlungingAttack": "下落攻击", "ElementalSkill": "元素战技 (E)", "ElementalBurst": "元素爆发 (Q)"
    },
    "elements": {
        "Physical": "物理", "Pyro": "火", "Hydro": "水", "Electro": "雷",
        "Cryo": "冰", "Dendro": "草", "Anemo": "风", "Geo": "岩", "null": "无限制"
    },
    "reactions": {
        "": "无反应", "vaporize_hydro": "蒸发 (水打火)", "vaporize_pyro": "蒸发 (火打水)",
        "melt_pyro": "融化 (火打冰)", "melt_cryo": "融化 (冰打火)", "aggravate": "超激化", "spread": "蔓激化"
    },
    "damage_types": {
        "attack": "普通攻击伤害", "Charged": "重击伤害", "plunging": "下落攻击伤害",
        "Skill": "元素战技伤害", "Burst": "元素爆发伤害"
    },
    "buff_types": [
        {"value": "damage_bonus", "label": "伤害加成"},
        {"value": "elemental_bonus", "label": "元素伤害加成"},
        {"value": "atk_percent", "label": "攻击力%"},
        {"value": "hp_percent", "label": "生命值%"},
        {"value": "crit_rate", "label": "暴击率"},
        {"value": "crit_dmg", "label": "暴击伤害"},
        {"value": "em", "label": "元素精通"},
        {"value": "def_reduction", "label": "防御削弱"},
        {"value": "resistance_percent", "label": "抗性降低"},
        {"value": "base_multiplier_add", "label": "固定增伤"}
    ]
}


# --- 2. 数据 IO 工具 ---
def load_json():
    if not os.path.exists(DATA_PATH): return {}
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_json(data):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --- 3. API 路由 ---

@app.get("/api/meta")
async def get_meta_data():
    """返回前端下拉菜单需要的所有选项"""
    return CONSTANTS


@app.get("/api/characters/list")
async def get_character_list():
    """返回简单列表供选择"""
    chars = load_json()
    result = []
    for cid, data in chars.items():
        elems = data.get("base_stats", {}).get("elements", [])
        elem_name = CONSTANTS["elements"].get(elems[0], elems[0]) if elems else "物理"
        result.append({"id": cid, "label": f"{cid} ({elem_name})"})
    return result


@app.get("/api/characters/{char_id}", response_model=CharacterData)
async def get_character_detail(char_id: str):
    """获取详情"""
    chars = load_json()
    if char_id not in chars:
        # 如果是新建，返回默认空对象
        return CharacterData()
    return chars[char_id]


# ✅ 新增：DELETE 接口
@app.delete("/api/characters/{char_id}")
async def delete_character(char_id: str):
    """删除指定角色"""
    chars = load_json()
    if char_id in chars:
        del chars[char_id]
        save_json(chars)
        return {"status": "success", "message": f"{char_id} deleted"}
    else:
        # 即使不存在也返回成功（幂等性），或者返回 404 看你需求
        return {"status": "ignored", "message": "Character not found"}


# ✅ 修改：POST 接口增加 old_id 参数处理重命名逻辑
@app.post("/api/characters/{char_id}")
async def save_character(
        char_id: str,
        data: CharacterData,
        old_id: Optional[str] = Query(None)  # 获取 URL 参数 ?old_id=xxx
):
    """
    保存角色配置。
    如果提供了 old_id 且 old_id != char_id，说明发生了改名，会删除旧数据。
    """
    chars = load_json()

    # 1. 处理改名逻辑：如果旧 ID 存在且不等于新 ID，先删除旧的
    if old_id and old_id != char_id and old_id in chars:
        print(f"Renaming character from {old_id} to {char_id}")
        del chars[old_id]

    # 2. 保存新数据 (Create or Update)
    chars[char_id] = data.dict(by_alias=True)

    save_json(chars)
    return {"status": "success", "id": char_id}


@app.post("/api/calculate")
async def calculate_damage(req: CalculationRequest):
    """调用核心计算逻辑"""
    try:
        from main import run_optimizer
        old_stdout = sys.stdout
        sys.stdout = cap = io.StringIO()

        run_optimizer(
            req.target_char,
            req.teammates,
            skill_type=req.skill_type,
            reaction=req.reaction
        )

        output = cap.getvalue()
        return {"result": output, "status": "success"}
    except Exception as e:
        return {"result": f"计算发生错误: {str(e)}", "status": "error"}
    finally:
        sys.stdout = sys.__stdout__


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)