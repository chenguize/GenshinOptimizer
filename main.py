# main.py
import json
import os
from typing import List, Dict, Any, Optional
from src.optimizer.genetic_algo import ArtifactOptimizer
from collections import Counter

# --- 常量定义：增伤映射表 (简化逻辑的关键) ---
BONUS_MAPPING = {
    "skill_bonus": "ElementalSkill",
    "burst_bonus": "ElementalBurst",
    "normal_bonus": "NormalAttack",
    "attack_bonus": "NormalAttack",  # 兼容旧版
    "charged_bonus": "ChargedAttack",
    "plunging_bonus": "PlungingAttack"
}


def load_json(path: str) -> Any:
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到文件: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_value(t: str, v: float) -> str:
    # 包含了 dmg 关键字，修复暴伤显示问题
    keywords = ["percent", "rate", "damage", "dmg", "bonus", "reduction", "ignore", "res"]
    if any(x in t for x in keywords):
        return f"{v:+.1%}"
    return f"{v:+.0f}"


def resolve_skill_element(char_data: Dict, skill_type: str) -> str:
    """
    确定技能实际元素：
    1. 读 JSON 配置 (Refactored JSON 应该都有值)
    2. 如果为空，回退到角色自身属性
    """
    skill_config = char_data.get("skills", {}).get(skill_type, {}).get("default", {})
    defined_element = skill_config.get("element", "")

    if defined_element and defined_element != "":
        return defined_element

    char_elements = char_data.get("base_stats", {}).get("elements", ["Physical"])
    return char_elements[0] if char_elements else "Physical"


def apply_team_buffs_to_panel(target_key: str, team_data: Dict[str, Dict], actual_skill_element: str, skill_type: str):
    """
    计算面板与增伤。
    actual_skill_element: 技能实际造成的元素类型 (e.g. "Hydro")
    skill_type: 技能类型 (e.g. "ChargedAttack")
    """
    char_base = team_data[target_key]["base_stats"]
    base_info = {
        "base_atk": char_base.get("atk", 0),
        "base_hp": char_base.get("hp", 0),
        "base_def": char_base.get("def", 0) or char_base.get("def_", 0)
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

    # 中文显示映射
    type_names = {
        "atk_percent": "攻击力%", "atk_flat": "固定攻击", "hp_percent": "生命值%", "hp_flat": "固定生命",
        "def_percent": "防御力%", "def_flat": "固定防御", "em": "元素精通",
        "crit_rate": "暴击率", "crit_dmg": "暴击伤害",
        "damage_bonus": "全伤害加成", "elemental_bonus": "元素伤害加成",
        "physical_bonus": "物理伤害加成",
        "skill_bonus": "战技伤害加成", "burst_bonus": "爆发伤害加成",
        "charged_bonus": "重击伤害加成", "plunging_bonus": "下落伤害加成",
        "normal_bonus": "普攻伤害加成",
        "def_reduction": "敌人减防", "resistance_percent": "敌人减抗",
        "base_multiplier_add": "基础倍率提升"
    }

    team_buff_logs = {}

    # === 元素共鸣 (基于角色自身属性) ===
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
        res_logs.append("双草共鸣 (精通+100)")
    if element_counts.get("geo", 0) >= 2:
        fixed_damage_bonus += 0.15
        res_logs.append("双岩共鸣 (全增伤+15%)")
    if res_logs: team_buff_logs["元素共鸣"] = res_logs

    # === 遍历 Buff ===
    for name, data in team_data.items():
        is_target = (name == target_key)
        char_display = name.upper()
        current_logs = []

        for buff in data.get("buffs", []):
            scope = buff.get("scope", "self")
            if scope == "self" and not is_target: continue

            t, v = buff["type"], buff["value"]
            buff_elem = buff.get("element", "null")
            active = True

            # --- 基础属性 ---
            if t == "atk_percent":
                sums["atk_pct"] += v
            elif t == "atk_flat":
                sums["atk_flat"] += v
            elif t == "hp_percent":
                sums["hp_pct"] += v
            elif t == "hp_flat":
                sums["hp_flat"] += v
            elif t == "def_percent":
                sums["def_pct"] += v
            elif t == "def_flat":
                sums["def_flat"] += v
            elif t == "em":
                sums["em"] += v
            elif t == "crit_rate":
                sums["crit_rate"] += v
            elif t in ["crit_dmg", "crit_damage"]:
                sums["crit_dmg"] += v
            elif t in other_params:
                other_params[t] += v

            # --- 增伤逻辑 (重构核心) ---

            # 1. 技能类型专用增伤 (使用 BONUS_MAPPING 查表)
            elif t in BONUS_MAPPING:
                required_skill = BONUS_MAPPING[t]
                if skill_type == required_skill:
                    fixed_damage_bonus += v
                else:
                    active = False

            # 2. 全伤害加成
            elif t == "damage_bonus":
                fixed_damage_bonus += v

            # 3. 元素/物理增伤
            elif t == "elemental_bonus":
                # 指定了元素 -> 严格匹配
                if buff_elem not in ["null", "", None]:
                    if buff_elem.lower() == actual_skill_element.lower():
                        fixed_damage_bonus += v
                    else:
                        active = False
                # 未指定(null) -> 只要不是物理就生效
                else:
                    if actual_skill_element.lower() != "physical":
                        fixed_damage_bonus += v
                    else:
                        active = False  # 物理不吃通用元素杯

            elif t == "physical_bonus":
                if actual_skill_element.lower() == "physical":
                    fixed_damage_bonus += v
                else:
                    active = False

            else:
                active = False

            if active:
                log_elem = f"[{buff_elem}]" if buff_elem not in ["null", ""] else ""
                current_logs.append(f"{type_names.get(t, t)}{log_elem} {format_value(t, v)}")

        if current_logs: team_buff_logs[char_display] = current_logs

    fixed_panel = {
        "atk": base_info["base_atk"] * (1 + sums["atk_pct"]) + sums["atk_flat"],
        "hp": base_info["base_hp"] * (1 + sums["hp_pct"]) + sums["hp_flat"],
        "def": base_info["base_def"] * (1 + sums["def_pct"]) + sums["def_flat"],
        "em": sums["em"], "crit_rate": sums["crit_rate"], "crit_dmg": sums["crit_dmg"]
    }
    return base_info, fixed_panel, fixed_damage_bonus, other_params, team_buff_logs


def run_optimizer(target_char: str, teammates: List[str], skill_type: str = "ElementalSkill",
                  reaction: Optional[str] = None, forced_set: Optional[str] = None):
    # 路径根据您的实际情况可能需要调整
    characters = load_json("data/rules/characters.json")
    artifacts = load_json("data/processed/artifacts.json")
    set_effects = load_json("data/rules/set_effects.json")

    team_data = {k: characters[k] for k in ([target_char] + teammates) if k in characters}
    if target_char not in characters:
        print(f"Error: Character {target_char} not found.")
        return

    # [步骤1] 解析技能实际属性
    actual_skill_element = resolve_skill_element(characters[target_char], skill_type)

    # [步骤2] 计算面板
    base_info, fixed_panel, fixed_dmg_bonus, others, logs = apply_team_buffs_to_panel(
        target_char, team_data, actual_skill_element, skill_type
    )

    # [步骤3] 自动推断反应
    if reaction is None or reaction == "":
        elem_lower = actual_skill_element.lower()
        reaction = "spread" if elem_lower == "dendro" else "aggravate" if elem_lower == "electro" else None

    # 抗性逻辑：将减抗数值转换为抗性系数 (假设基础抗性 10%)
    total_res_shred = others['resistance_percent']
    enemy_base_res = 0.10
    final_res = enemy_base_res - total_res_shred
    others['resistance_percent'] = 1 - (final_res / 2) if final_res < 0 else 1 - final_res

    print("\n" + "╔" + "═" * 78 + "╗")
    print(f"║ 优化任务: {target_char.upper():<10} 技能: {skill_type:<15} 伤害元素: {actual_skill_element:<10} ║")
    print("╠" + "═" * 78 + "╣")
    print(
        f"║ [1] 角色白字: ATK {base_info['base_atk']:.0f} | HP {base_info['base_hp']:.0f} | DEF {base_info['base_def']:.0f}")
    print(f"║ [2] 队伍增益明细:")
    for name, blist in logs.items(): print(f"║     ● {name:<10}: {', '.join(blist)}")

    initial_dmg_bonus_pct = (fixed_dmg_bonus - 1.0)
    print(f"║ [3] 特殊乘区: 减抗 {total_res_shred:.1%} | 减防 {others['def_reduction']:.1%}")
    print(f"║ [4] 队友后固定面板:")
    print(
        f"║     ● 属性: 攻击力 {fixed_panel['atk']:.0f} | 生命值 {fixed_panel['hp']:.0f} | 防御 {fixed_panel['def']:.0f} | 精通 {fixed_panel['em']:.0f}")
    print(f"║     ● 暴击: {fixed_panel['crit_rate']:.1%} / {fixed_panel['crit_dmg']:.1%}")
    print(f"║     ● 初始总增伤: {initial_dmg_bonus_pct:.1%}")
    print("╚" + "═" * 78 + "╝")

    optimizer = ArtifactOptimizer(
        artifacts_data=artifacts, set_effects_data=set_effects,
        base_info=base_info, fixed_panel=fixed_panel, fixed_damage_bonus=fixed_dmg_bonus,
        target_skill_multipliers=characters[target_char]["skills"][skill_type]["default"]["multipliers"],
        skill_type=skill_type,
        character_element=actual_skill_element,
        reaction=reaction, forced_set=forced_set, **others
    )

    results = optimizer.optimize(population_size=1000, generations=200)

    for i, res in enumerate(results, 1):
        p = res["panel"]
        total_dmg_bonus = p.get("all_damage_bonus", 0)

        print(f"\n[方案 {i}] 期望伤害: {res['damage']:,.0f}")
        print(
            f" > 面板: 攻击力 {p['atk']:.0f} | 生命值 {p['hp']:.0f} | 增伤 {total_dmg_bonus:.1%} | 精通 {p['em']:.0f} | 暴击率 {p['crit_rate']:.1%} | 暴伤 {p['crit_damage']:.1%}")

        set_desc = " + ".join([f"{name}({count})" for name, count in res['sets'].items()])
        print(f" > 套装: {set_desc}")
        for art_str in res['artifact_strings']:
            print(art_str)
        print("-" * 80)


if __name__ == "__main__":
    # 使用修改后的数据进行测试
    # 龙王重击 (Hydro, ChargedAttack)
    # 队友：希诺宁(Geo, 减抗/增伤), 芙宁娜(Hydro, 巨额增伤), 万叶(Anemo, 增伤/减抗)
    run_optimizer("龙王", ["希诺宁", "水神-芙宁娜", "万叶"], forced_set="", skill_type="ChargedAttack", reaction="")