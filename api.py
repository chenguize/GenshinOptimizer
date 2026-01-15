# api.py
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import sys
import io
from typing import List, Dict, Any, Optional

from models import CharacterData, CalculationRequest, BaseStats, Artifact

app = FastAPI(title="Genshin Calc API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CHAR_DATA_PATH = "data/rules/characters.json"
ARTIFACT_DATA_PATH = "data/processed/artifacts.json"
SET_EFFECTS_PATH = "data/rules/set_effects.json"

# --- 游戏全量套装名录 ---
ALL_GAME_SETS = [
    "绝缘之旗印", "深林的记忆", "饰金之梦", "逐影猎人", "黄金剧团",
    "昔时之歌", "回声之林夜话", "黑曜秘典", "烬城勇者卷绘",
    "千岩牢固", "苍白之火", "海染砗磲", "华馆梦醒形骸记",
    "冰风迷途的勇士", "沉沦之心", "魔女的炎之花", "渡过烈火的贤人",
    "如雷的盛怒", "平息雷鸣的尊者", "翠绿之影", "被怜爱的少女",
    "悠古的磐岩", "逆飞的流星", "昔日宗室之仪", "染血的骑士道",
    "角斗士的终幕礼", "流浪大地的乐团", "追忆之注连", "辰砂往生录",
    "来歆余响", "乐园遗落之花", "沙上楼阁史话", "水仙之梦", "花海甘露之光"
]

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
    # 🟢 [核心修改] 补全了所有伤害加成类型
    "buff_types": [
        {"value": "atk_percent", "label": "攻击力% (ATK%)"},
        {"value": "hp_percent", "label": "生命值% (HP%)"},
        {"value": "def_percent", "label": "防御力% (DEF%)"},
        {"value": "em", "label": "元素精通 (EM)"},
        {"value": "crit_rate", "label": "暴击率 (CR)"},
        {"value": "crit_dmg", "label": "暴击伤害 (CD)"},
        {"value": "energy_recharge", "label": "充能效率 (ER)"},

        {"value": "damage_bonus", "label": "全伤害加成 (All DMG)"},
        {"value": "elemental_bonus", "label": "元素伤害加成 (Elemental)"},
        {"value": "physical_bonus", "label": "物理伤害加成 (Physical)"},

        {"value": "normal_bonus", "label": "普攻伤害加成 (Normal)"},
        {"value": "charged_bonus", "label": "重击伤害加成 (Charged)"},
        {"value": "plunging_bonus", "label": "下落伤害加成 (Plunging)"},
        {"value": "skill_bonus", "label": "战技伤害加成 (Skill)"},
        {"value": "burst_bonus", "label": "爆发伤害加成 (Burst)"},

        {"value": "base_multiplier_add", "label": "基础倍率增加 (Flat DMG)"}
    ]
}


def load_json(path: str) -> Any:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        if path.endswith("artifacts.json"): return []
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return [] if path.endswith("artifacts.json") else {}


def save_json(path: str, data: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class SetEffectValue(BaseModel):
    type: Optional[str] = None
    value: Optional[float] = None
    element: Optional[str] = "null"
    note: Optional[str] = None


class SetEffectUpdate(BaseModel):
    effects: Dict[str, List[SetEffectValue]]


@app.get("/api/meta")
async def get_meta_data():
    try:
        # 扫描库存补全列表
        artifacts = load_json(ARTIFACT_DATA_PATH)
        inventory_sets = set()
        if isinstance(artifacts, list):
            for a in artifacts:
                if isinstance(a, dict) and "set" in a:
                    inventory_sets.add(a["set"])

        all_potential_sets = inventory_sets.union(set(ALL_GAME_SETS))

        rules = load_json(SET_EFFECTS_PATH)
        configured_sets = list(rules.keys())

        return {
            **CONSTANTS,
            "artifact_sets": sorted(configured_sets),
            "set_suggestions": sorted(list(all_potential_sets))
        }
    except Exception as e:
        print(f"Meta Error: {e}")
        return {**CONSTANTS, "artifact_sets": [], "set_suggestions": []}


@app.get("/api/sets")
async def get_all_sets():
    return load_json(SET_EFFECTS_PATH)


@app.post("/api/sets/{set_name}")
async def create_set(set_name: str):
    data = load_json(SET_EFFECTS_PATH)
    if set_name in data:
        return {"status": "success", "message": "Exists"}

    data[set_name] = {
        "2": [{"type": "atk_percent", "value": 0.18, "element": "null"}],
        "4": []
    }
    save_json(SET_EFFECTS_PATH, data)
    return {"status": "success"}


@app.put("/api/sets/{set_name}")
async def update_set(set_name: str, update: SetEffectUpdate):
    data = load_json(SET_EFFECTS_PATH)
    if set_name not in data:
        raise HTTPException(404, "Set not found")
    data[set_name] = update.dict()["effects"]
    save_json(SET_EFFECTS_PATH, data)
    return {"status": "success"}


@app.delete("/api/sets/{set_name}")
async def delete_set(set_name: str):
    data = load_json(SET_EFFECTS_PATH)
    if set_name in data:
        del data[set_name]
        save_json(SET_EFFECTS_PATH, data)
    return {"status": "success"}


# --- 角色与计算 ---
@app.get("/api/characters/list")
async def get_character_list():
    chars = load_json(CHAR_DATA_PATH)
    return [{"id": k, "label": k} for k in chars.keys()]


@app.get("/api/characters/{char_id}", response_model=CharacterData)
async def get_character_detail(char_id: str):
    chars = load_json(CHAR_DATA_PATH)
    return chars.get(char_id, CharacterData())


@app.post("/api/characters/{char_id}")
async def save_character(char_id: str, data: CharacterData, old_id: Optional[str] = Query(None)):
    chars = load_json(CHAR_DATA_PATH)
    if old_id and old_id != char_id and old_id in chars:
        del chars[old_id]
    chars[char_id] = data.dict(by_alias=True)
    save_json(CHAR_DATA_PATH, chars)
    return {"status": "success"}


@app.delete("/api/characters/{char_id}")
async def delete_character(char_id: str):
    chars = load_json(CHAR_DATA_PATH)
    if char_id in chars:
        del chars[char_id]
        save_json(CHAR_DATA_PATH, chars)
    return {"status": "success"}


@app.post("/api/calculate")
async def calculate_damage(req: CalculationRequest):
    try:
        from main import run_optimizer
        old_stdout = sys.stdout
        sys.stdout = cap = io.StringIO()
        run_optimizer(req.target_char, req.teammates, skill_type=req.skill_type, reaction=req.reaction)
        output = cap.getvalue()
        return {"result": output, "status": "success"}
    except Exception as e:
        import traceback
        return {"result": traceback.format_exc(), "status": "error"}
    finally:
        sys.stdout = sys.__stdout__


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)