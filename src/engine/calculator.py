# src/engine/calculator.py
"""
极简版伤害计算器（优化器专用）
设计理念：
- 调用方已提前计算好所有面板数值（最终攻击力、生命值、防御力、精通、暴击等）
- 调用方已汇总好总增伤 all_damage_bonus
- 技能倍率由调用方传入一个列表，支持多属性转化（atk/hp/def/em 等）
- calculator 只负责：
  1. 根据列表计算出技能基础倍率部分（base_multiplier）
  2. 加上激化/蔓激化平伤（如果有）
  3. 严格按照 buff_types.md 乘区相乘
- 极简、高效、适合遗传算法大量调用
"""

from typing import List, Dict, Optional, Literal

# 元素反应类型
ReactionType = Literal[
    None,
    "vaporize_hydro", "vaporize_pyro",
    "melt_pyro", "melt_cryo",
    "aggravate", "spread"
]


class DamageCalculator:
    LEVEL_MULTIPLIER_90 = 1446.858
    AGGRAVATE_COEFF = 1.15
    SPREAD_COEFF = 1.25

    @staticmethod
    def calculate_damage(
            skill_multipliers: List[Dict[str, float]],
            final_atk: float,
            final_hp: float,
            final_def: float,
            final_em: float,
            all_damage_bonus: float,
            crit_rate: float,
            crit_damage: float,
            base_multiplier_add: float = 0.0,  # 新增：来自队友或技能的固定基础伤害加成
            reaction: Optional[ReactionType] = None,
            reaction_bonus_buff: float = 0.0,  # 修改：激化类额外加成（原transformative_bonus）
            reaction_specific_bonus: float = 0.0,  # 新增：增幅类（蒸发融化）套装加成（如魔女4）
            def_reduction: float = 0.0,
            def_ignore: float = 0.0,
            resistance_percent: float = 0.0,
            enemy_level: int = 103,
            enemy_base_res: float = 0.10,
            attacker_level: int = 95,
    ) -> float:
        # 1. 计算技能基础倍率部分
        base_mult = 0.0
        for m in skill_multipliers:
            typ = m["type"]
            val = m["value"]
            if typ == "atk_percent":
                base_mult += val / 100.0 * final_atk
            elif typ == "hp_percent":
                base_mult += val / 100.0 * final_hp
            elif typ == "def_percent":
                base_mult += val / 100.0 * final_def
            elif typ == "em":
                base_mult += val / 100.0 * final_em

        # 融入队友带来的基础倍率区加成
        base_mult += base_multiplier_add

        # 2. 激化/蔓激化平伤
        transformative_flat = 0.0
        if reaction == "aggravate":
            transformative_flat = DamageCalculator.LEVEL_MULTIPLIER_90 * DamageCalculator.AGGRAVATE_COEFF * (
                        1 + 5 * final_em / (final_em + 1200) + reaction_bonus_buff)
        elif reaction == "spread":
            transformative_flat = DamageCalculator.LEVEL_MULTIPLIER_90 * DamageCalculator.SPREAD_COEFF * (
                        1 + 5 * final_em / (final_em + 1200) + reaction_bonus_buff)

        base_mult += transformative_flat

        # 3. 元素反应区（增幅反应：蒸发/融化）
        reaction_mult = 1.0
        if reaction in ["vaporize_hydro", "vaporize_pyro", "melt_pyro", "melt_cryo"]:
            base = 2.0 if reaction in ["vaporize_hydro", "melt_pyro"] else 1.5
            em_bonus = 2.78 * final_em / (final_em + 1400)
            # 引入 reaction_specific_bonus (增幅加成)
            reaction_mult = base * (1 + em_bonus + reaction_specific_bonus)

        # 4. 增伤区
        dmg_bonus =1+ all_damage_bonus

        # 5. 暴击区
        crit_rate = max(0.0, min(1.0, crit_rate))
        crit_mult = 1+crit_rate * crit_damage

        # 6. 防御区
        def_mult = (attacker_level + 100) / (
                (attacker_level + 100) + (enemy_level + 100) * (1 - def_reduction) * (1 - def_ignore)
        )

        # 7. 抗性区
        res = enemy_base_res - resistance_percent
        if res < 0:
            res_mult = 1 - res / 2
        elif res < 0.75:
            res_mult = 1 - res
        else:
            res_mult = 1 / (1 + 4 * res)

        return base_mult * reaction_mult * dmg_bonus * crit_mult * def_mult * res_mult


# ==================== 测试调用示例 ====================
if __name__ == "__main__":
    final_atk, final_hp, final_def, final_em = 800, 50683, 700, 980
    crit_rate, crit_damage, all_damage_bonus = 0.986, 3.725, 3.326
    skill_multipliers_demo = [{"type": "hp_percent", "value": 28.048}]

    damage = DamageCalculator.calculate_damage(
        skill_multipliers=skill_multipliers_demo,
        final_atk=final_atk,
        final_hp=final_hp,
        final_def=final_def,
        final_em=final_em,
        all_damage_bonus=all_damage_bonus,
        crit_rate=crit_rate,
        crit_damage=crit_damage,
        base_multiplier_add=2728,  # 队友提供的基础倍率加成
        reaction_bonus_buff=0,  # 激化反应加成
        reaction_specific_bonus=0.0,  # 增幅反应加成
        def_reduction=0,
        def_ignore=0,
        resistance_percent=0.85,  # 减抗30%
    )

    print(f"最终期望伤害 ≈ {damage:,.0f}")