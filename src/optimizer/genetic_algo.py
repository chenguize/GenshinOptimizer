# src/optimizer/genetic_algo.py
# src/optimizer/genetic_algo.py
import random
from typing import List, Dict, Any, Optional
from collections import Counter
from src.engine.calculator import DamageCalculator


class ArtifactOptimizer:
    SLOTS = ["flower", "plume", "sands", "goblet", "circlet"]
    STAT_MAP = {
        "hp_flat": "生命值", "hp_percent": "生命值%", "atk_flat": "攻击力",
        "atk_percent": "攻击力%", "def_flat": "防御力", "def_percent": "防御力%",
        "em": "元素精通", "energy_recharge": "充能效率", "crit_rate": "暴击率",
        "crit_dmg": "暴击伤害", "crit_damage": "暴击伤害", "elemental_bonus": "元素伤害加成"
    }

    def __init__(self, artifacts_data, set_effects_data, base_info, fixed_panel,
                 fixed_damage_bonus, target_skill_multipliers, character_element,skill_type,
                 reaction=None, forced_set=None,**kwargs):
        self.artifacts = artifacts_data
        self.set_effects = set_effects_data
        self.base_info = base_info  # 角色+武器白字
        self.fixed_panel = fixed_panel  # main.py传来的包含共鸣和队友Buff的面板
        self.fixed_damage_bonus = fixed_damage_bonus
        self.skill_multipliers = target_skill_multipliers
        self.character_element = character_element
        self.reaction = reaction
        self.forced_set = forced_set
        self.skill_type = skill_type
        self.params = kwargs
        self.artifacts_by_slot = {s: [a for a in artifacts_data if a["slot"] == s] for s in self.SLOTS}

        if self.forced_set:
            self.forced_by_slot = {s: [a for a in artifacts_data if a["slot"] == s and a["set"] == self.forced_set] for
                                   s in self.SLOTS}

    def _format_stat_value(self, stat_type, value):
        is_percent = any(x in stat_type for x in ["percent", "crit", "recharge", "bonus"])
        return f"{value * 100:.1f}%" if is_percent else f"{int(value)}"

    def _calculate_panel_and_bonus(self, selected: List[Dict[str, Any]], skill_type: str = "") -> Dict[
        str, float]:
        # sums 只记录圣遗物带来的增量
        sums = {"atk_pct": 0.0, "atk_flat": 0.0, "hp_pct": 0.0, "hp_flat": 0.0,
                "def_pct": 0.0, "def_flat": 0.0, "em": 0.0, "crit_rate": 0.0,
                "crit_dmg": 0.0, "dmg_bonus": 0.0}

        char_elem = self.character_element.lower()
        set_count = Counter(a["set"] for a in selected)  #

        # 1. 圣遗物套装效果
        for set_name, count in set_count.items():
            if set_name in self.set_effects:
                effs = self.set_effects[set_name]
                for n in ["2", "4"]:
                    if count >= int(n):
                        key = n if n in effs else f"{n}_piece"
                        for eff in effs.get(key, []):
                            t, v, e = eff.get("type"), eff.get("value", 0), eff.get("element", "null").lower()
                            if t == "atk_percent":
                                sums["atk_pct"] += v
                            if t == "hp_percent":
                                sums["hp_pct"] += v
                            if t == "em":
                                sums["em"] += v
                            if t == "crit_rate":
                                sums["crit_rate"] += v
                            if t == "crit_dmg":
                                sums["crit_dmg"] += v
                            if (e == "null" or e == char_elem):
                                if t in ["damage_bonus", "elemental_bonus"]:
                                    sums["dmg_bonus"] += v
                            if t == "skill_bonus" and skill_type == "ElementalSkill":
                                sums["dmg_bonus"] += v
                            if t == "burst_bonus" and skill_type == "ElementalBurst":
                                sums["dmg_bonus"] += v
                            if t == "attack_bonus" and skill_type == "NormalAttack":
                                sums["dmg_bonus"] += v
                            if t == "charged_bonus" and skill_type == "ChargedAttack":
                                sums["dmg_bonus"] += v
                            if t == "plunging_bonus" and skill_type == "PlungingAttack":
                                sums["dmg_bonus"] += v

        # 2. 圣遗物单件词条
        for art in selected:
            for s in [art["main_stat"]] + art.get("substats", []):
                st, sv = s["type"], s["value"]
                if st == "atk_percent":
                    sums["atk_pct"] += sv
                elif st == "atk_flat":
                    sums["atk_flat"] += sv
                elif st == "hp_percent":
                    sums["hp_pct"] += sv
                elif st == "hp_flat":
                    sums["hp_flat"] += sv
                elif st == "em":
                    sums["em"] += sv
                elif st == "crit_rate":
                    sums["crit_rate"] += sv
                elif st in ["crit_dmg", "crit_damage"]:
                    sums["crit_dmg"] += sv

        # 3. 汇总公式 (核心修复：圣遗物增量 + fixed_panel)
        # 圣遗物的百分比直接作用于 base_info 的白字
        return {
            "atk": self.base_info["base_atk"] * sums["atk_pct"] + sums["atk_flat"] + self.fixed_panel["atk"],
            "hp": self.base_info["base_hp"] * sums["hp_pct"] + sums["hp_flat"] + self.fixed_panel["hp"],
            "def": self.base_info["base_def"] * sums["def_pct"] + sums["def_flat"] + self.fixed_panel["def"],
            "em": sums["em"] + self.fixed_panel["em"],
            "crit_rate": sums["crit_rate"] + self.fixed_panel["crit_rate"],
            "crit_damage": sums["crit_dmg"] + self.fixed_panel["crit_dmg"],
            "all_damage_bonus": sums["dmg_bonus"] + self.fixed_damage_bonus-1
        }

    def _evaluate(self, individual: List[int]) -> float:
        selected = [next(a for a in self.artifacts if a["id"] == aid) for aid in individual]
        if self.forced_set and sum(1 for a in selected if a["set"] == self.forced_set) < 4: return 0.0

        skill_t = self.skill_type
        p = self._calculate_panel_and_bonus(selected, skill_t)
        return DamageCalculator.calculate_damage(
            skill_multipliers=self.skill_multipliers,
            final_atk=p["atk"], final_hp=p["hp"], final_def=p["def"], final_em=p["em"],
            all_damage_bonus=p["all_damage_bonus"],
            crit_rate=p["crit_rate"], crit_damage=p["crit_damage"],
            reaction=self.reaction, **self.params
        )


    def optimize(self, population_size=400, generations=100, top_n=5):
        population = []
        for _ in range(population_size):
            if self.forced_set:
                off_slot = random.choice(self.SLOTS)
                ind = [random.choice(self.forced_by_slot[s] if s != off_slot and self.forced_by_slot[s] else self.artifacts_by_slot[s])["id"] for s in self.SLOTS]
            else:
                ind = [random.choice(self.artifacts_by_slot[s])["id"] for s in self.SLOTS]
            population.append(ind)

        for gen in range(generations):
            scored = sorted([(self._evaluate(ind), ind) for ind in population], key=lambda x: x[0], reverse=True)
            elites = [ind for score, ind in scored[:population_size // 5] if score > 0]
            if len(elites) < 5: elites = [ind for _, ind in scored[:10]]

            next_gen = elites.copy()
            while len(next_gen) < population_size:
                p1, p2 = random.sample(elites, 2)
                child = [random.choice([p1[i], p2[i]]) for i in range(5)]
                if random.random() < 0.2:
                    m_idx = random.randint(0, 4)
                    child[m_idx] = random.choice(self.artifacts_by_slot[self.SLOTS[m_idx]])["id"]
                next_gen.append(child)
            population = next_gen

        final_scored = sorted([(self._evaluate(ind), ind) for ind in population], key=lambda x: x[0], reverse=True)
        results = []
        seen = set()
        slot_cn = {"flower": "花", "plume": "羽", "sands": "沙", "goblet": "杯", "circlet": "头"}
        current_skill_type = self.skill_type

        for score, ind in final_scored:
            if score <= 0: continue
            combo = tuple(sorted(ind))
            if combo not in seen:
                selected_arts = [next(a for a in self.artifacts if a["id"] == aid) for aid in ind]
                art_details = []
                for a in selected_arts:
                    m_stat = a["main_stat"]
                    main_str = f"{self.STAT_MAP.get(m_stat['type'], m_stat['type'])} {self._format_stat_value(m_stat['type'], m_stat['value'])}"
                    sub_strs = [f"{self.STAT_MAP.get(s['type'], s['type'])} {self._format_stat_value(s['type'], s['value'])}" for s in a["substats"]]
                    art_details.append(f"   [{slot_cn[a['slot']]}] {a['set']} | {main_str} | 副: {' / '.join(sub_strs)}")

                results.append({
                    "damage": score,
                    "panel": self._calculate_panel_and_bonus(selected_arts, current_skill_type),
                    "sets": dict(Counter(a["set"] for a in selected_arts)),
                    "artifact_strings": art_details,
                    "artifacts": selected_arts
                })
                seen.add(combo)
            if len(results) >= top_n: break
        return results