# main.py
import json
import os
from typing import List, Dict, Any, Optional
from collections import Counter

from src.optimizer.genetic_algo import ArtifactOptimizer
from src.engine.calculator import DamageCalculator
from src.engine.analyzer import SubstatAnalyzer


def load_json(path: str) -> Any:
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到文件: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_value(t: str, v: float) -> str:
    keywords = ["percent", "pct", "rate", "damage", "dmg", "bonus", "reduction", "ignore", "res"]
    if any(x in t for x in keywords):
        return f"{v:+.1%}"
    return f"{v:+.0f}"


def resolve_skill_data(char_data: Dict, skill_type: str):
    """解析技能元素和伤害类型"""
    skill_config = char_data.get("skills", {}).get(skill_type, {}).get("default", {})
    element = skill_config.get("element", "")
    if not element:
        char_elements = char_data.get("base_stats", {}).get("elements", ["Physical"])
        element = char_elements[0] if char_elements else "Physical"
    damage_type = skill_config.get("damage_type", skill_type)
    return element, damage_type


def apply_single_buff(t: str, v: float, sums: Dict, other_params: Dict, target_element: str = None,
                      buff_element: str = "null"):
    t = t.lower().strip()
    # 基础属性
    if t in ["atk_percent", "atk_pct", "atk%"]:
        sums["atk_pct"] = sums.get("atk_pct", 0.0) + v
    elif t in ["atk", "atk_flat"]:
        sums["atk_flat"] = sums.get("atk_flat", 0.0) + v
    elif t in ["hp_percent", "hp_pct", "hp%"]:
        sums["hp_pct"] = sums.get("hp_pct", 0.0) + v
    elif t in ["hp", "hp_flat"]:
        sums["hp_flat"] = sums.get("hp_flat", 0.0) + v
    elif t in ["def_percent", "def_pct", "def%"]:
        sums["def_pct"] = sums.get("def_pct", 0.0) + v
    elif t in ["def", "def_flat"]:
        sums["def_flat"] = sums.get("def_flat", 0.0) + v
    elif t in ["em", "elemental_mastery"]:
        sums["em"] = sums.get("em", 0.0) + v
    elif t in ["crit_rate", "crit_rate_percent", "cr"]:
        sums["crit_rate"] = sums.get("crit_rate", 0.0) + v
    elif t in ["crit_dmg", "crit_dmg", "cd"]:
        sums["crit_dmg"] = sums.get("crit_dmg", 0.0) + v
    elif t in ["energy_recharge", "energy_recharge_bonus", "er"]:
        sums["er"] = sums.get("er", 0.0) + v
    # 增伤属性
    elif t in ["damage_bonus", "dmg_bonus", "all_damage_bonus"]:
        return v
    elif "bonus" in t and any(ele in t for ele in
                              ["pyro", "hydro", "cryo", "electro", "anemo", "geo", "dendro", "physical", "elemental"]):
        curr_buff_ele = buff_element.lower() if "elemental" in t else t.replace("_bonus", "").replace("_dmg",
                                                                                                      "").strip()
        if curr_buff_ele in ["null", "none", "all"] or curr_buff_ele == (
        target_element.lower() if target_element else ""):
            other_params["elemental_bonus"] = other_params.get("elemental_bonus", 0.0) + v
    elif any(act in t for act in ["charged", "normal", "plunging", "skill", "burst"]):
        key = [k for k in ["charged_bonus", "normal_bonus", "plunging_bonus", "skill_bonus", "burst_bonus"] if
               k.split('_')[0] in t][0]
        other_params[key] = other_params.get(key, 0.0) + v
    else:
        other_params[t] = other_params.get(t, 0.0) + v
    return 0.0


def calculate_basic_panel(char_data: Dict, team_sums: Dict = None) -> Dict[str, float]:
    base = char_data.get("base_stats", {})
    sums = team_sums.copy() if team_sums else {}
    sums["em"] = sums.get("em", 0.0) + base.get("em", 0.0)
    sums["er"] = sums.get("er", 0.0) + (1.0 + base.get("energy_recharge_bonus", 0.0))
    sums["crit_rate"] = sums.get("crit_rate", 0.0) + base.get("crit_rate", 0.05)
    sums["crit_dmg"] = sums.get("crit_dmg", 0.0) + base.get("crit_dmg", 0.5)
    for b in char_data.get("buffs", []):
        if isinstance(b.get("value"), (int, float)): apply_single_buff(b["type"], b["value"], sums, {})
    base_def = base.get("def", 0) or base.get("def_", 0)
    return {
        "atk": base.get("atk", 0) * (1 + sums.get("atk_pct", 0)) + sums.get("atk_flat", 0),
        "hp": base.get("hp", 0) * (1 + sums.get("hp_pct", 0)) + sums.get("hp_flat", 0),
        "def": base_def * (1 + sums.get("def_pct", 0)) + sums.get("def_flat", 0),
        "em": sums["em"], "er": sums["er"], "crit_rate": sums["crit_rate"], "crit_dmg": sums["crit_dmg"]
    }


def apply_team_buffs_to_panel(target_key, team_data, skill_ele, skill_type):
    target_base_stats = team_data[target_key]["base_stats"]
    base_info = {"base_atk": target_base_stats.get("atk", 0), "base_hp": target_base_stats.get("hp", 0),
                 "base_def": target_base_stats.get("def", 0) or target_base_stats.get("def_", 0)}
    team_global_sums, logs = {}, {}
    elems = [d["base_stats"]["elements"][0].lower() for d in team_data.values()]
    cnt = Counter(elems)
    if cnt.get("pyro", 0) >= 2: team_global_sums["atk_pct"] = 0.25; logs.setdefault("System", []).append(
        "双火共鸣 +25% ATK")
    if cnt.get("hydro", 0) >= 2: team_global_sums["hp_pct"] = 0.25; logs.setdefault("System", []).append(
        "双水共鸣 +25% HP")
    if cnt.get("dendro", 0) >= 2: team_global_sums["em"] = 100; logs.setdefault("System", []).append("双草共鸣 +100 EM")
    fixed_damage_bonus = 1.0
    if cnt.get("geo", 0) >= 2: fixed_damage_bonus += 0.15; logs.setdefault("System", []).append("双岩共鸣 +15% DMG")
    teammate_panels = {name: calculate_basic_panel(data, team_global_sums) for name, data in team_data.items()}
    sums = team_global_sums.copy()
    sums.update({"em": sums.get("em", 0.0) + target_base_stats.get("em", 0),
                 "er": sums.get("er", 0.0) + (1.0 + target_base_stats.get("energy_recharge_bonus", 0.0)),
                 "crit_rate": sums.get("crit_rate", 0.0) + target_base_stats.get("crit_rate", 0.05),
                 "crit_dmg": sums.get("crit_dmg", 0.0) + target_base_stats.get("crit_dmg", 0.5)})
    other_params, pending_dynamic = {}, []
    for name, data in team_data.items():
        is_target = (name == target_key)
        for buff in data.get("buffs", []):
            if buff.get("scope", "self") == "self" and not is_target: continue
            if isinstance(buff["value"], str): pending_dynamic.append((name, buff)); continue
            val = apply_single_buff(buff["type"], buff["value"], sums, other_params, skill_ele,
                                    buff.get("element", "null"))
            fixed_damage_bonus += val
            if is_target or buff.get("scope") == "team": logs.setdefault(name, []).append(
                f"[{buff['type']}] {format_value(buff['type'], buff['value'])}")
    current_ctx = teammate_panels[target_key]
    for owner_name, buff in pending_dynamic:
        eval_ctx = current_ctx if owner_name == target_key else teammate_panels.get(owner_name, {})
        val = DamageCalculator.resolve_dynamic_value(buff["value"], eval_ctx)
        d_val = apply_single_buff(buff["type"], val, sums, other_params, skill_ele, buff.get("element", "null"))
        fixed_damage_bonus += d_val
        logs.setdefault(owner_name, []).append(
            f"[{buff['type']}] {format_value(buff['type'], val)} (动态: {buff['value']})")
    return base_info, {"atk": base_info["base_atk"] * (1 + sums.get("atk_pct", 0)) + sums.get("atk_flat", 0),
                       "hp": base_info["base_hp"] * (1 + sums.get("hp_pct", 0)) + sums.get("hp_flat", 0),
                       "def": base_info["base_def"] * (1 + sums.get("def_pct", 0)) + sums.get("def_flat", 0),
                       "em": sums["em"], "er": sums["er"] - 1.0,
                       "crit_rate": sums["crit_rate"], "crit_dmg": sums["crit_dmg"],
                       "damage_bonus": fixed_damage_bonus}, fixed_damage_bonus, other_params, logs


def run_optimizer(target_char, teammates, skill_type="ElementalSkill", reaction=None, forced_set=None):
    chars = load_json("data/rules/characters.json")
    arts = load_json("data/processed/artifacts.json")
    sets = load_json("data/rules/set_effects.json")

    if target_char not in chars:
        print(f"Error: Character {target_char} not found.")
        return None

    team_data = {k: chars[k] for k in [target_char] + teammates if k in chars}
    ele, dmg_type = resolve_skill_data(chars[target_char], skill_type)

    # [步骤 1] 应用队伍 Buff 和共鸣
    base, panel, fixed_dmg, others, logs = apply_team_buffs_to_panel(target_char, team_data, ele, skill_type)

    # [步骤 2] 反应推断逻辑
    # 显式传 "" 代表强制无反应，不进行自动推断
    if reaction is None:
        reaction = "spread" if ele.lower() == "dendro" else "aggravate" if ele.lower() == "electro" else None
    elif reaction == "":
        reaction = None

    print(f"Running optimization for {target_char} ({dmg_type})...")

    # [步骤 3] 初始化优化器
    opt = ArtifactOptimizer(
        arts, sets, base, panel, fixed_dmg,
        chars[target_char]["skills"][skill_type]["default"]["multipliers"],
        ele, skill_type, dmg_type, reaction, forced_set, **others
    )
    res = opt.optimize(population_size=1000, generations=200)

    solutions = []
    others_params = others.copy()

    for i, r in enumerate(res, 1):
        p = r["panel"]

        # 这里的 p 已经由 genetic_algo 修正，包含了 elemental_bonus 和 action_bonus
        calc_args = {
            "skill_multipliers": chars[target_char]["skills"][skill_type]["default"]["multipliers"],
            "damage_type": dmg_type,
            "all_damage_bonus": p["all_damage_bonus"],
            "reaction": reaction,
        }

        # [步骤 4] 计算最终伤害
        final_dmg = DamageCalculator.calculate_damage(
            final_atk=p['atk'], final_hp=p['hp'], final_def=p['def'],
            final_em=p['em'], final_er_bonus=p.get('energy_recharge_bonus', 0),
            crit_rate=p['crit_rate'],
            crit_dmg=p['crit_dmg'],
            **calc_args, **others_params
        )

        # [步骤 5] 执行收益分析

        substat_priority = SubstatAnalyzer.analyze(base, p, calc_args, others_params)

        solutions.append({
            "rank": i,
            "damage": final_dmg,
            "panel": p,
            "sets": r["sets"],
            "dmg_type": dmg_type,
            "artifact_strings": r.get("artifact_strings", []),
            "substat_priority": substat_priority
        })

    return {
        "meta": {"target_char": target_char, "skill_type": skill_type, "dmg_type": dmg_type},
        "solutions": solutions,
        "logs": logs
    }


def print_result_cli(data: Dict[str, Any]):
    if not data: return
    meta = data['meta']
    print(f"\n=== {meta['target_char']} | {meta['skill_type']} ({meta['dmg_type']}) ===")

    print("╔" + "═" * 75 + "╗")
    for char_name, buff_list in data["logs"].items():
        print(f"║   🔹 [{char_name}]: {', '.join(buff_list[:3])}...")
    print("╚" + "═" * 75 + "╝")

    for sol in data["solutions"]:
        p = sol["panel"]
        print(f"\n[方案 {sol['rank']}] 期望伤害: {sol['damage']:,.0f}")

        # 🟢 展示具体的圣遗物属性
        for art_str in sol.get("artifact_strings", []):
            print(art_str)

        if sol["dmg_type"] == "MoonBloom":
            em = p.get('em', 0)
            moon_curve = 1.0 + (6.0 * em) / (2000.0 + em)
            moon_static = p.get('moon_dmg_bonus', 0.0)
            print(
                f"   面板: HP {p.get('hp', 0):.0f} | EM {em:.0f} | CR {p.get('crit_rate', 0):.1%} | CD {p.get('crit_dmg', 0.5):.1%}")
            print(f"   月倍率区: BaseFlat {p.get('moon_base_flat', 0):.0f} | BasePct {p.get('moon_base_pct', 0):.1%}")
            print(
                f"   月增伤区: 曲线加成 {moon_curve:.2f}x | 静态月加成 {moon_static:+.1%} | 总增伤乘数 {moon_curve + moon_static:.2f}x")
            print(f"   防御区: 强制无视防御 (100% Ignore)")
        else:
            # 🟢 修正：综合增伤统计（通用 + 元素 + 动作加成）
            # p['all_damage_bonus'] 现在包含 1.0 基础 + 通用全加成（芙宁娜、万叶、套装等）
            universal_bonus = p.get("all_damage_bonus", 1.0) - 1.0
            elemental_bonus = p.get("elemental_bonus", 0.0)

            # 匹配当前技能动作的加成键
            st = meta['skill_type']
            action_key = {
                "NormalAttack": "normal_bonus", "ChargedAttack": "charged_bonus",
                "ElementalSkill": "skill_bonus", "ElementalBurst": "burst_bonus"
            }.get(st, "")
            action_bonus = p.get(action_key, 0.0)

            total_bonus = universal_bonus + elemental_bonus + action_bonus

            print(
                f"   面板: ATK {p.get('atk', 0):.0f} | HP {p.get('hp', 0):.0f} | CR {p.get('crit_rate', 0):.1%} | CD {p.get('crit_dmg', 0.5):.1%}")
            print(
                f"   增伤统计: 总计 {total_bonus:.1%} (通用 {universal_bonus:.1%} + 元素 {elemental_bonus:.1%} + 动作加成 {action_bonus:.1%})")
            print(f"   套装: {sol['sets']}")

        # 🟢 展示 Analyzer 收益报告
        if sol.get("substat_priority"):
            SubstatAnalyzer.print_report(sol["substat_priority"])
if __name__ == "__main__":
    # 示例 1: 龙王 (常规 ChargedAttack)
    res_lw = run_optimizer("龙王", ["水神-芙宁娜", "万叶", "希诺宁"], skill_type="ChargedAttack")
    print_result_cli(res_lw)

    # 示例 2: 月神-少女 (MoonBloom)
    # res_ys = run_optimizer("月神-少女", [ "草神", "白术"], skill_type="ChargedAttack")
    # print_result_cli(res_ys)