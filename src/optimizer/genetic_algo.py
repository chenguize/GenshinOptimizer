# src/optimizer/genetic_algo.py
import random
from typing import List, Dict, Any, Optional
from collections import Counter
from src.engine.calculator import DamageCalculator


class ArtifactOptimizer:
    SLOTS = ["flower", "plume", "sands", "goblet", "circlet"]
    # 🟢 统一铁律字段: crit_dmg
    STAT_MAP = {
        "hp_flat": "生命值", "hp_percent": "生命值%", "atk_flat": "攻击力",
        "atk_percent": "攻击力%", "def_flat": "防御力", "def_percent": "防御力%",
        "em": "元素精通", "energy_recharge": "充能效率", "crit_rate": "暴击率",
        "crit_dmg": "暴击伤害", "elemental_bonus": "元素伤害加成"
    }

    def __init__(self, artifacts_data, set_effects_data, base_info, fixed_panel,
                 fixed_damage_bonus, target_skill_multipliers, character_element, skill_type,
                 damage_type,
                 reaction=None, forced_set=None, **kwargs):
        self.artifacts = artifacts_data
        self.set_effects = set_effects_data
        self.base_info = base_info
        self.fixed_panel = fixed_panel
        self.fixed_damage_bonus = fixed_damage_bonus
        self.skill_multipliers = target_skill_multipliers
        self.character_element = character_element
        self.reaction = reaction
        self.forced_set = forced_set
        self.skill_type = skill_type
        self.damage_type = damage_type
        self.params = kwargs

        # 预处理：按部位分类圣遗物
        self.artifacts_by_slot = {s: [a for a in artifacts_data if a["slot"] == s] for s in self.SLOTS}
        # 预处理：ID 查找表
        self.art_lookup = {a["id"]: a for a in artifacts_data}

        # 预处理：强制套装池
        if self.forced_set:
            self.forced_by_slot = {s: [a for a in artifacts_data if a["slot"] == s and a["set"] == self.forced_set] for
                                   s in self.SLOTS}

    def _format_stat_value(self, stat_type, value):
        """格式化数值显示，使用 :.1% 自动处理乘100逻辑"""
        is_percent = any(x in stat_type for x in ["percent", "crit", "recharge", "bonus"])
        return f"{value:.1%}" if is_percent else f"{int(value)}"

    def _calculate_panel_and_bonus(self, selected: List[Dict[str, Any]], skill_type: str = "") -> Dict[str, float]:
        sums = {
            "atk_pct": 0.0, "atk_flat": 0.0, "hp_pct": 0.0, "hp_flat": 0.0,
            "def_pct": 0.0, "def_flat": 0.0, "em": 0.0,
            "crit_rate": 0.0, "crit_dmg": 0.0,
            "energy_recharge": 0.0,
            "universal_dmg": 0.0,  # 🟢 细分增伤：通用
            "ele_dmg": 0.0,  # 🟢 细分增伤：元素
            "act_dmg": 0.0,  # 🟢 细分增伤：动作(重击/普攻等)
            "moon_dmg_bonus": 0.0
        }

        char_elem = self.character_element.lower()
        set_count = Counter(a["set"] for a in selected)

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
                            elif t == "hp_percent":
                                sums["hp_pct"] += v
                            elif t == "em":
                                sums["em"] += v
                            elif t == "crit_rate":
                                sums["crit_rate"] += v
                            elif t == "crit_dmg":
                                sums["crit_dmg"] += v
                            elif t == "energy_recharge":
                                sums["energy_recharge"] += v
                            elif t == "moon_dmg_bonus":
                                sums["moon_dmg_bonus"] += v
                            elif (e == "null" or e == char_elem):
                                if t == "damage_bonus":
                                    sums["universal_dmg"] += v
                                elif t == "elemental_bonus":
                                    sums["ele_dmg"] += v

                            # 🟢 [修正] 动作特定增伤分类，确保 15% 重击加成归类到动作区
                            if t == "skill_bonus" and skill_type == "ElementalSkill": sums["act_dmg"] += v
                            if t == "burst_bonus" and skill_type == "ElementalBurst": sums["act_dmg"] += v
                            if t == "attack_bonus" and skill_type == "NormalAttack": sums["act_dmg"] += v
                            if t == "charged_bonus" and skill_type == "ChargedAttack": sums["act_dmg"] += v

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
                elif st == "crit_dmg":
                    sums["crit_dmg"] += sv
                elif st == "energy_recharge":
                    sums["energy_recharge"] += sv

        # 🟢 [核心修复] 面板计算公式：移除 (1 + sums)，改用 sums 直乘 Base，避免 Base 被双倍计算
        panel = {
            "atk": self.base_info["base_atk"] * sums["atk_pct"] + sums["atk_flat"] + self.fixed_panel["atk"],
            "hp": self.base_info["base_hp"] * sums["hp_pct"] + sums["hp_flat"] + self.fixed_panel["hp"],
            "def": self.base_info["base_def"] * sums["def_pct"] + sums["def_flat"] + self.fixed_panel["def"],
            "em": sums["em"] + self.fixed_panel["em"],
            "crit_rate": sums["crit_rate"] + self.fixed_panel["crit_rate"],
            "crit_dmg": sums["crit_dmg"] + self.fixed_panel["crit_dmg"],
            "energy_recharge_bonus": sums["energy_recharge"] + self.fixed_panel.get("energy_recharge_bonus", 0.0),

            # 增伤汇总：all_damage_bonus 依然作为传给计算器的总加成
            "all_damage_bonus": sums["universal_dmg"] + sums["ele_dmg"] + sums["act_dmg"] + self.fixed_damage_bonus,

            # 为了让 main.py 打印正确，需要将圣遗物提供的分类增伤存入对应键名
            "elemental_bonus": sums["ele_dmg"] + self.params.get("elemental_bonus", 0.0),
            "moon_dmg_bonus": sums["moon_dmg_bonus"] + self.params.get("moon_dmg_bonus", 0.0)
        }

        # 🟢 修正动作加成的键名映射，确保 15% 显示在“动作加成”
        action_key = {
            "NormalAttack": "normal_bonus", "ChargedAttack": "charged_bonus",
            "ElementalSkill": "skill_bonus", "ElementalBurst": "burst_bonus"
        }.get(skill_type, "")
        if action_key:
            panel[action_key] = sums["act_dmg"] + self.params.get(action_key, 0.0)

        # 注入 params 中的其他队友 Buff
        for k, v in self.params.items():
            if k not in panel: panel[k] = v

        return panel

    def _evaluate(self, individual: List[int]) -> float:
        if self.forced_set:
            count = sum(1 for aid in individual if self.art_lookup[aid]["set"] == self.forced_set)
            if count < 4: return 0.0

        selected = [self.art_lookup[aid] for aid in individual]
        p = self._calculate_panel_and_bonus(selected, self.skill_type)

        return DamageCalculator.calculate_damage(
            skill_multipliers=self.skill_multipliers,
            damage_type=self.damage_type,
            final_atk=p["atk"],
            final_hp=p["hp"],
            final_def=p["def"],
            final_em=p["em"],
            final_er_bonus=p["energy_recharge_bonus"],
            all_damage_bonus=p["all_damage_bonus"],
            crit_rate=p["crit_rate"],
            crit_dmg=p["crit_dmg"],
            reaction=self.reaction,
            **self.params
        )

    # ... (其余 optimize, _repair_individual, _tournament_selection 保持逻辑不变) ...

    def _repair_individual(self, individual: List[int]) -> List[int]:
        if not self.forced_set: return individual
        current_set_indices = [idx for idx, aid in enumerate(individual) if
                               self.art_lookup[aid]["set"] == self.forced_set]
        if len(current_set_indices) >= 4: return individual
        new_ind = individual[:]
        off_piece_indices = [idx for idx in range(5) if idx not in current_set_indices]
        random.shuffle(off_piece_indices)
        for idx in off_piece_indices[:4 - len(current_set_indices)]:
            pool = self.forced_by_slot.get(self.SLOTS[idx], [])
            if pool: new_ind[idx] = random.choice(pool)["id"]
        return new_ind

    def _tournament_selection(self, population, scores, k=3):
        candidates = random.sample(range(len(population)), k)
        return population[max(candidates, key=lambda i: scores[i])]

    def optimize(self, population_size=400, generations=100, top_n=5):
        population = []
        for _ in range(population_size):
            ind = []
            valid = True
            for idx, slot in enumerate(self.SLOTS):
                pool = self.forced_by_slot.get(slot, []) if (
                            self.forced_set and random.random() > 0.2) else self.artifacts_by_slot.get(slot, [])
                if not pool: pool = self.artifacts_by_slot.get(slot, [])
                if not pool:
                    valid = False; break
                else:
                    ind.append(random.choice(pool)["id"])
            if valid: population.append(self._repair_individual(ind))
        if not population: return []

        for gen in range(generations):
            scored = [(self._evaluate(ind), ind) for ind in population]
            scores_list = [s[0] for s in scored]
            scored_sorted = sorted(scored, key=lambda x: x[0], reverse=True)
            elite_count = max(2, int(population_size * 0.05))
            next_gen = [ind for s, ind in scored_sorted[:elite_count]]
            seen_hashes = set(tuple(ind) for ind in next_gen)
            while len(next_gen) < population_size:
                p1 = self._tournament_selection(population, scores_list)
                p2 = self._tournament_selection(population, scores_list)
                child = [p1[i] if random.random() < 0.5 else p2[i] for i in range(5)]
                if random.random() < (0.3 - 0.2 * gen / generations):
                    idx = random.randint(0, 4)
                    pool = self.artifacts_by_slot[self.SLOTS[idx]]
                    if pool: child[idx] = random.choice(pool)["id"]
                child = self._repair_individual(child)
                child_tuple = tuple(child)
                if child_tuple not in seen_hashes:
                    next_gen.append(child)
                    seen_hashes.add(child_tuple)
            population = next_gen

        final_scored = sorted([(self._evaluate(ind), ind) for ind in population], key=lambda x: x[0], reverse=True)
        results = []
        seen = set()
        slot_cn = {"flower": "花", "plume": "羽", "sands": "沙", "goblet": "杯", "circlet": "头"}
        for score, ind in final_scored:
            if score <= 0: continue
            combo = tuple(sorted(ind))
            if combo not in seen:
                selected_arts = [self.art_lookup[aid] for aid in ind]
                art_details = []
                for a in selected_arts:
                    m_stat = a["main_stat"]
                    main_str = f"{self.STAT_MAP.get(m_stat['type'], m_stat['type'])} {self._format_stat_value(m_stat['type'], m_stat['value'])}"
                    sub_strs = [
                        f"{self.STAT_MAP.get(s['type'], s['type'])} {self._format_stat_value(s['type'], s['value'])}"
                        for s in a.get("substats", [])]
                    art_details.append(
                        f"   [{slot_cn[a['slot']]}] {a['set']} | {main_str} | 副: {' / '.join(sub_strs)}")
                results.append({
                    "damage": score,
                    "panel": self._calculate_panel_and_bonus(selected_arts, self.skill_type),
                    "sets": dict(Counter(a["set"] for a in selected_arts)),
                    "artifact_strings": art_details,
                    "artifacts": selected_arts
                })
                seen.add(combo)
            if len(results) >= top_n: break
        return results