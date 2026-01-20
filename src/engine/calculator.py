# src/engine/calculator.py
import math
import re
from typing import List, Dict, Optional, Literal, Union, Set


class DamageCalculator:
    LEVEL_MULTIPLIER_90 = 1446.858
    AGGRAVATE_COEFF = 1.15
    SPREAD_COEFF = 1.25

    # 体系注册表
    MOON_SYSTEM_TYPES: Set[str] = {
        "MoonBloom", "MoonElectro", "MoonBurn"
    }

    @staticmethod
    def _get_moon_curve_multiplier(damage_type: str, em: float) -> float:
        """[Internal] 月体系精通曲线计算 (返回包含1.0的系数)"""
        if damage_type == "MoonBloom":
            return 1.0 + (6.0 * em) / (2000.0 + em)
        elif damage_type == "MoonElectro":
            return 1.0 + (3.0 * em) / (1500.0 + em)
        return 1.0

    @staticmethod
    def _get_moon_def_ignore(damage_type: str) -> float:
        """[Internal] 月体系防御穿透规则"""
        if damage_type == "MoonBloom": return 1.0
        return 0.0

    @staticmethod
    def resolve_dynamic_value(value: Union[float, str], context: Dict[str, float]) -> float:
        """核心解析器：解析动态公式"""
        if isinstance(value, (int, float)): return float(value)
        if isinstance(value, str):
            try:
                expr = value
                local_ctx = context.copy()
                if "def" in local_ctx:
                    local_ctx["def_val"] = local_ctx["def"]
                    expr = re.sub(r'\bdef\b', 'def_val', expr)
                safe_globals = {"min": min, "max": max, "math": math}
                return float(eval(expr, {"__builtins__": None}, {**safe_globals, **local_ctx}))
            except Exception:
                return 0.0
        return 0.0

    @staticmethod
    def calculate_damage(
            skill_multipliers: List[Dict[str, float]],
            damage_type: str,
            final_atk: float, final_hp: float, final_def: float, final_em: float,
            final_er_bonus: float,
            all_damage_bonus: float,  # 外部传入的 fixed_dmg (含基数1.0)
            crit_rate: float, crit_dmg: float,
            **kwargs
    ) -> float:
        # --- 1. 增伤聚合 ---
        extra_dmg_bonus = 0.0
        extra_dmg_bonus += kwargs.get("elemental_bonus", 0.0)
        extra_dmg_bonus += kwargs.get("physical_bonus", 0.0)

        # 动作类型增伤
        action_bonuses = {
            "NormalAttack": "normal_bonus",
            "ChargedAttack": "charged_bonus",
            "PlungingAttack": "plunging_bonus",
            "ElementalSkill": "skill_bonus",
            "ElementalBurst": "burst_bonus"
        }
        bonus_key = action_bonuses.get(damage_type)
        if bonus_key:
            extra_dmg_bonus += kwargs.get(bonus_key, 0.0)

        # --- 2. 基础倍率区 ---
        raw_base_mult = 0.0
        for m in skill_multipliers:
            typ, val = m["type"], m["value"]
            if typ == "atk_percent":
                raw_base_mult += val / 100.0 * final_atk
            elif typ == "hp_percent":
                raw_base_mult += val / 100.0 * final_hp
            elif typ == "def_percent":
                raw_base_mult += val / 100.0 * final_def
            elif typ == "em":
                raw_base_mult += val / 100.0 * final_em
            elif typ == "flat":
                raw_base_mult += val

        # --- 3. 体系/反应分支处理 ---
        base_multiplier_add = kwargs.get("base_multiplier_add", 0.0)
        reaction = kwargs.get("reaction", None)
        reaction_map = kwargs.get("reaction_bonus_map", kwargs)

        enemy_level, attacker_level = kwargs.get("enemy_level", 103), kwargs.get("attacker_level", 90)
        enemy_base_res, res_pen = kwargs.get("enemy_base_res", 0.10), kwargs.get("resistance_percent", 0.0)
        def_red, def_ign = kwargs.get("def_reduction", 0.0), kwargs.get("def_ignore", 0.0)
        ascension_mult = kwargs.get("ascension_mult", 0.0)

        final_base_mult = raw_base_mult
        final_dmg_multiplier = 1.0
        reaction_mult = 1.0

        if damage_type in DamageCalculator.MOON_SYSTEM_TYPES:
            # === 月体系逻辑 ===
            moon_base_flat = kwargs.get("moon_base_flat", 0.0)
            moon_base_pct = kwargs.get("moon_base_pct", 0.0)
            # 基础伤害：(倍率 + 月Flat + 倍率提升) * (1 + 月百分比)
            final_base_mult = (raw_base_mult + moon_base_flat ) * (1 + moon_base_pct)

            # 增伤区：精通曲线 + 静态月增伤
            curve_val = DamageCalculator._get_moon_curve_multiplier(damage_type, final_em)
            moon_static = kwargs.get("moon_dmg_bonus", 0.0)
            final_dmg_multiplier = curve_val + moon_static

            # 防御区：强制破防
            def_ign = DamageCalculator._get_moon_def_ignore(damage_type)
        else:
            # === 常规体系逻辑 ===
            final_base_mult = raw_base_mult + base_multiplier_add
            # 增伤乘数：传入的 all_damage_bonus (含1.0) + 额外增伤
            final_dmg_multiplier = all_damage_bonus + extra_dmg_bonus

            if reaction in ["aggravate", "spread"]:
                coeff = DamageCalculator.AGGRAVATE_COEFF if reaction == "aggravate" else DamageCalculator.SPREAD_COEFF
                bonus = reaction_map.get(reaction.split('_')[0], 0.0)
                final_base_mult += 1446.858 * coeff * (1 + 5 * final_em / (final_em + 1200) + bonus)
            elif reaction and ("vaporize" in reaction or "melt" in reaction):
                base = 2.0 if reaction in ["vaporize_hydro", "melt_pyro"] else 1.5
                em_b = 2.78 * final_em / (final_em + 1400)
                bonus = reaction_map.get("vaporize" if "vaporize" in reaction else "melt", 0.0)
                reaction_mult = base * (1 + em_b + bonus + kwargs.get("reaction_specific_bonus", 0.0))

        # --- 4. 结算 ---
        crit_rate = max(0.0, min(1.0, crit_rate))
        crit_mult = 1.0 + crit_rate * crit_dmg

        def_ign = min(1.0, def_ign)
        def_denominator = (attacker_level + 100) + (enemy_level + 100) * (1 - def_red) * (1 - def_ign)
        def_mult = (attacker_level + 100) / def_denominator

        res = enemy_base_res - res_pen
        res_mult = 1 - res / 2 if res < 0 else (1 - res if res < 0.75 else 1 / (1 + 4 * res))

        return final_base_mult * reaction_mult * final_dmg_multiplier * crit_mult * def_mult * res_mult * (
                    1.0 + ascension_mult)
# ==========================================
# 🟢 [测试用例] 模拟真实输入 (预乘 1.6x)
# ==========================================
if __name__ == "__main__":
    print("\n=== 🔮 伤害计算内核测试 (龙王重击) ===")

    # 假设 JSON 中已填入乘过 1.6 的倍率: 14.47 * 1.6 = 23.15
    test_multipliers = [{"type": "hp_percent", "value": 28.048}]

    params = {
        "skill_multipliers": test_multipliers,
        "damage_type": "ChargedAttack",
        "final_atk": 1510.0, "final_hp": 50683.0, "final_def": 597.0, "final_em": 16.0, "final_er_bonus": 0.0,
        "crit_rate": 0.986, "crit_dmg": 3.725,

        # 增伤: 通用246% + 元素30% + 重击42% + 逐影15% = 333% (3.33)
        # 传入值 = 1.0 + 3.33 = 4.33
        "all_damage_bonus": 2.46,  # 基础 1.0 + 2.46
        "elemental_bonus": 0.30,
        "charged_bonus": 0.42+0.15 ,

        "base_multiplier_add": 2850,

        # 🟢 [移除] 不再传入 ascension_mult，因为倍率已包含
        "ascension_mult": 0.0,

        "attacker_level": 90, "enemy_level": 103, "enemy_base_res": 0.10, "resistance_percent": 0.85,
        "reaction": None,
    }

    dmg = DamageCalculator.calculate_damage(**params)

    print(f"基础数据: HP {params['final_hp']:.0f} | CD {params['crit_dmg']:.1%}")
    print(
        f"增伤参数: 通用 {params['all_damage_bonus'] - 1:.0%} | 元素 {params['elemental_bonus']:.0%} | 重击 {params['charged_bonus']:.0%}")
    print(f"倍率加成: +{params['base_multiplier_add']}")
    print("-" * 40)
    print(f"💥 单段期望伤害: {dmg:,.0f}")