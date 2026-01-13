# main.py
import json
import os
from typing import List, Dict, Any, Optional
from src.optimizer.genetic_algo import ArtifactOptimizer
from collections import Counter

def load_json(path: str) -> Any:
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到文件: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def format_value(t: str, v: float) -> str:
    if any(x in t for x in ["percent", "rate", "damage", "bonus", "reduction", "ignore", "res"]):
        return f"{v:+.1%}"
    return f"{v:+.0f}"

def apply_team_buffs_to_panel(target_key: str, team_data: Dict[str, Dict], character_element: str, skill_type: str):
    char_base = team_data[target_key]["base_stats"]
    base_info = {
        "base_atk": char_base.get("atk", 0),
        "base_hp": char_base.get("hp", 0),
        "base_def": char_base.get("def", 0)
    }
    sums = {
        "atk_pct": 0.0, "atk_flat": 0.0, "hp_pct": 0.0, "hp_flat": 0.0,
        "def_pct": 0.0, "def_flat": 0.0, "em": char_base.get("em", 0),
        "crit_rate": char_base.get("crit_rate", 0.05),
        "crit_dmg": char_base.get("crit_dmg", 0.50) or char_base.get("crit_damage", 0.50),
    }
    fixed_damage_bonus = 1.0
    other_params = {
        "def_reduction": 0.0, "def_ignore": 0.0, "resistance_percent": 0.0,
        "reaction_bonus_buff": 0.0, "reaction_specific_bonus": 0.0, "base_multiplier_add": 0.0,
    }

    type_names = {
        "atk_percent": "攻击力%", "atk_flat": "固定攻击", "hp_percent": "生命值%", "hp_flat": "固定生命",
        "def_percent": "防御力%", "def_flat": "固定防御", "em": "元素精通", "crit_rate": "暴击率",
        "crit_dmg": "暴击伤害", "crit_damage": "暴击伤害", "damage_bonus": "全伤害加成",
        "elemental_bonus": "元素伤害加成", "skill_bonus": "战技伤害加成",
        "burst_bonus": "爆发伤害加成","charged_bonus": "重击伤害加成","attack_bonus": "普通统计伤害加成","plunging_bonus": "下落攻击伤害加成", "def_reduction": "敌人减防", "resistance_percent": "敌人减抗"
    }

    team_buff_logs = {}

    # === [新增逻辑] 元素共鸣判定 ===
    elements_in_team = [data["base_stats"]["elements"][0].lower() for data in team_data.values()]
    element_counts = Counter(elements_in_team)
    res_logs = []

    if element_counts.get("pyro", 0) >= 2:
        sums["atk_pct"] += 0.25
        res_logs.append("双火共鸣 (攻击力+25%)")
    if element_counts.get("water", 0) >= 2 or element_counts.get("hydro", 0) >= 2:
        sums["hp_pct"] += 0.25
        res_logs.append("双水共鸣 (生命值+25%)")
    if element_counts.get("dendro", 0) >= 2:
        sums["em"] += 100
        res_logs.append("双草共鸣 (元素精通+100)")
    if element_counts.get("geo", 0) >= 2:
        fixed_damage_bonus += 0.15
        res_logs.append("双岩共鸣 (全增伤+15%)")

    if res_logs: team_buff_logs["元素共鸣"] = res_logs

    for name, data in team_data.items():
        is_target = (name == target_key)
        char_display = name.upper()
        current_logs = []
        for buff in data.get("buffs", []):
            scope = buff.get("scope", "self")
            if scope == "self" and not is_target: continue
            t, v = buff["type"], buff["value"]
            elem = buff.get("element", "null")
            active = True
            if t == "atk_percent": sums["atk_pct"] += v
            elif t == "atk_flat": sums["atk_flat"] += v
            elif t == "hp_percent": sums["hp_pct"] += v
            elif t == "hp_flat": sums["hp_flat"] += v
            elif t == "def_percent": sums["def_pct"] += v
            elif t == "def_flat": sums["def_flat"] += v
            elif t == "em": sums["em"] += v
            elif t == "crit_rate": sums["crit_rate"] += v
            elif t in ["crit_dmg", "crit_damage"]: sums["crit_dmg"] += v
            elif t in other_params: other_params[t] += v
            elif t in ["damage_bonus", "elemental_bonus"]:
                if t == "elemental_bonus" and elem.lower() != character_element.lower(): active = False
                else: fixed_damage_bonus += v
            elif t == "skill_bonus" and skill_type == "ElementalSkill": fixed_damage_bonus += v
            elif t == "burst_bonus" and skill_type == "ElementalBurst": fixed_damage_bonus += v
            elif t == "attack_bonus" and skill_type == "NormalAttack":
                fixed_damage_bonus += v
            elif t == "charged_bonus" and skill_type == "ChargedAttack":
                fixed_damage_bonus += v
            elif t == "plunging_bonus" and skill_type == "PlungingAttack":
                fixed_damage_bonus += v
            else: active = False
            if active: current_logs.append(f"{type_names.get(t, t)} {format_value(t, v)}")
        if current_logs: team_buff_logs[char_display] = current_logs

    # 此处 fixed_panel 保持包含基础值的逻辑，genetic_algo 已针对此点做减法修复
    fixed_panel = {
        "atk": base_info["base_atk"] * (1 + sums["atk_pct"]) + sums["atk_flat"],
        "hp": base_info["base_hp"] * (1 + sums["hp_pct"]) + sums["hp_flat"],
        "def": base_info["base_def"] * (1 + sums["def_pct"]) + sums["def_flat"],
        "em": sums["em"], "crit_rate": sums["crit_rate"], "crit_dmg": sums["crit_dmg"]
    }
    return base_info, fixed_panel, fixed_damage_bonus, other_params, team_buff_logs

def run_optimizer(target_char: str, teammates: List[str], skill_type: str = "ElementalSkill", reaction: Optional[str] = None, forced_set: Optional[str] = None):
    characters = load_json("data/rules/characters.json")
    artifacts = load_json("data/processed/artifacts.json")
    set_effects = load_json("data/rules/set_effects.json")

    team_data = {k: characters[k] for k in ([target_char] + teammates) if k in characters}
    char_elem = characters[target_char]["base_stats"]["elements"][0].lower()

    base_info, fixed_panel, fixed_dmg_bonus, others, logs = apply_team_buffs_to_panel(target_char, team_data, char_elem, skill_type)

    if reaction is None:
        reaction = "spread" if char_elem == "dendro" else "aggravate" if char_elem == "electro" else None

    print("\n" + "╔" + "═" * 78 + "╗")
    print(f"║ 优化任务: {target_char.upper():<10} 技能: {skill_type:<15} 约束: {str(forced_set or '无'):<12} ║")
    print("╠" + "═" * 78 + "╣")
    print(f"║ [1] 角色白字: ATK {base_info['base_atk']:.0f} | HP {base_info['base_hp']:.0f} | DEF {base_info['base_def']:.0f}")
    print(f"║ [2] 队伍增益明细:")
    for name, blist in logs.items(): print(f"║     ● {name:<10}: {', '.join(blist)}")
    initial_dmg_bonus_pct = (fixed_dmg_bonus - 1.0)

    print(f"║ [3] 特殊乘区: 减抗 {others['resistance_percent']:.1%} | 减防 {others['def_reduction']:.1%}")
    print(f"║ [4] 队友后固定面板:")
    print(
        f"║     ● 属性: 攻击力 {fixed_panel['atk']:.0f} | 生命值 {fixed_panel['hp']:.0f} | 防御 {fixed_panel['def']:.0f} | 精通 {fixed_panel['em']:.0f}")
    print(f"║     ● 暴击: {fixed_panel['crit_rate']:.1%} / {fixed_panel['crit_dmg']:.1%}")
    print(f"║     ● 初始总增伤: {initial_dmg_bonus_pct:.1%}")  # 这里会显示如 275.6%
    print("╚" + "═" * 78 + "╝")

    optimizer = ArtifactOptimizer(
        artifacts_data=artifacts, set_effects_data=set_effects,
        base_info=base_info, fixed_panel=fixed_panel, fixed_damage_bonus=fixed_dmg_bonus,
        target_skill_multipliers=characters[target_char]["skills"][skill_type]["default"]["multipliers"],skill_type=skill_type,
        character_element=char_elem, reaction=reaction, forced_set=forced_set, **others
    )

    results = optimizer.optimize(population_size=1000, generations=200)

    for i, res in enumerate(results, 1):
        p = res["panel"]
        # 1. 提取总增伤（由于内部存的是 1.90 这种，需要转为百分比）
        # 如果你代码里 all_damage_bonus 已经包含了基础的 100%，则显示 (p - 1)
        total_dmg_bonus = p.get("all_damage_bonus", 0)

        print(f"\n[方案 {i}] 期望伤害: {res['damage']*1.6:,.0f}")

        # 2. 在面板这一行增加“增伤”输出
        print(
            f" > 面板: 攻击力 {p['atk']:.0f} | 生命值 {p['hp']:.0f} | 增伤 {total_dmg_bonus:.1%} | 精通 {p['em']:.0f} | 暴击率 {p['crit_rate']:.1%} | 暴伤 {p['crit_damage']:.1%}")

        set_desc = " + ".join([f"{name}({count})" for name, count in res['sets'].items()])
        print(f" > 套装: {set_desc}")
        for art_str in res['artifact_strings']:
            print(art_str)
        print("-" * 80)

if __name__ == "__main__":
    # 请根据您的实际路径修改 set_effects.json 路径
    run_optimizer("瓦蕾莎", [ "希诺宁", "万叶","杜林"], forced_set="",skill_type="PlungingAttack",reaction="")