# src/engine/analyzer.py
from typing import Dict, List, Any
from src.engine.calculator import DamageCalculator


class SubstatAnalyzer:
    # === 原神圣遗物副词条最大值 (Max Roll) ===
    # 增伤词条：虽然圣遗物副词条没有增伤，但为了对比收益，设定为与生命/攻击百分比同权的 5.8%
    STD_ROLLS = {
        "hp_percent": 0.058,  # 5.8%
        "atk_percent": 0.058,  # 5.8%
        "def_percent": 0.073,  # 7.3%
        "hp_flat": 299.0,
        "atk_flat": 19.0,
        "def_flat": 23.0,
        "em": 23.0,
        "crit_rate": 0.039,  # 3.9%
        "crit_dmg": 0.078,  # 7.8%
        "dmg_bonus": 0.058,  # [新增] 增伤词条 (等效 5.8%)
    }

    # 显示名称映射
    LABELS = {
        "hp_percent": "大生命 (HP%)",
        "atk_percent": "大攻击 (ATK%)",
        "def_percent": "大防御 (DEF%)",
        "hp_flat": "小生命",
        "atk_flat": "小攻击",
        "def_flat": "小防御",
        "em": "元素精通",
        "crit_rate": "暴击率",
        "crit_dmg": "暴击伤害",
        "dmg_bonus": "增伤 (Dmg%)"
    }

    @staticmethod
    def analyze(
            base_info: Dict[str, float],  # 角色白值
            current_panel: Dict[str, float],  # 当前最终面板
            calc_args: Dict[str, Any],  # 传递给计算器的其他参数
            others_params: Dict[str, float]  # 动态参数
    ) -> List[Dict]:
        """
        计算词条收益率 (基于最大词条值)
        """

        # 辅助函数：安全获取暴伤
        def get_cd(panel):
            return panel.get("crit_dmg", panel.get("crit_dmg", 0.0))

        # 1. 计算基准伤害
        base_dmg = DamageCalculator.calculate_damage(
            final_atk=current_panel["atk"],
            final_hp=current_panel["hp"],
            final_def=current_panel["def"],
            final_em=current_panel["em"],
            final_er_bonus=current_panel.get("energy_recharge_bonus", 0),
            crit_rate=current_panel["crit_rate"],
            crit_dmg=get_cd(current_panel),
            **calc_args,
            **others_params
        )

        if base_dmg == 0:
            return []

        results = []

        # 2. 遍历每一个标准词条
        for stat_key, roll_val in SubstatAnalyzer.STD_ROLLS.items():
            # 复制面板和参数，避免污染
            new_stats = current_panel.copy()
            local_calc_args = calc_args.copy()

            # --- 核心逻辑：模拟加成 ---
            if stat_key == "hp_percent":
                new_stats["hp"] += base_info["base_hp"] * roll_val
            elif stat_key == "atk_percent":
                new_stats["atk"] += base_info["base_atk"] * roll_val
            elif stat_key == "def_percent":
                new_stats["def"] += base_info["base_def"] * roll_val

            # 固定值属性
            elif stat_key == "hp_flat":
                new_stats["hp"] += roll_val
            elif stat_key == "atk_flat":
                new_stats["atk"] += roll_val
            elif stat_key == "def_flat":
                new_stats["def"] += roll_val
            elif stat_key == "em":
                new_stats["em"] += roll_val
            elif stat_key == "crit_rate":
                new_stats["crit_rate"] += roll_val
            elif stat_key == "crit_dmg":
                if "crit_dmg" in new_stats:
                    new_stats["crit_dmg"] += roll_val
                else:
                    new_stats["crit_dmg"] = new_stats.get("crit_dmg", 0.0) + roll_val

            # [新增] 增伤词条处理
            elif stat_key == "dmg_bonus":
                # 直接加到 calc_args 的 all_damage_bonus 参数中
                prev_bonus = local_calc_args.get("all_damage_bonus", 0.0)
                local_calc_args["all_damage_bonus"] = prev_bonus + roll_val

            # 3. 计算新伤害
            new_dmg = DamageCalculator.calculate_damage(
                final_atk=new_stats["atk"],
                final_hp=new_stats["hp"],
                final_def=new_stats["def"],
                final_em=new_stats["em"],
                final_er_bonus=new_stats.get("energy_recharge_bonus", 0),
                crit_rate=new_stats["crit_rate"],
                crit_dmg=get_cd(new_stats),
                **local_calc_args,  # 使用修改后的参数
                **others_params
            )

            # 4. 计算收益幅度
            gain = new_dmg - base_dmg
            gain_pct = gain / base_dmg if base_dmg != 0 else 0

            results.append({
                "key": stat_key,
                "label": SubstatAnalyzer.LABELS[stat_key],
                "roll_value": roll_val,
                "damage_increase": gain,
                "percent_increase": gain_pct
            })

        # 5. 排序
        results.sort(key=lambda x: x["percent_increase"], reverse=True)

        # 6. 计算相对权重 (Score)
        max_gain = results[0]["percent_increase"] if results else 0
        for item in results:
            if max_gain > 0:
                item["score"] = (item["percent_increase"] / max_gain) * 100
            else:
                item["score"] = 0.0

        return results

    @staticmethod
    def print_report(results: List[Dict]):
        print("\n" + "╔" + "═" * 70 + "╗")
        print("║ 📈 词条收益分析 (基于最大词条数值 Max Roll)                  ║")
        print("╠" + "═" * 70 + "╣")
        print(f"║ {'词条类型':<14} | {'提升幅度':<10} | {'绝对值':<8} | {'推荐权重':<8} ║")
        print("╟" + "─" * 70 + "╢")

        for r in results:
            if r['percent_increase'] < 0.0001: continue

            if "percent" in r['key'] or "crit" in r['key'] or "dmg" in r['key']:
                val_display = f"{r['roll_value']:.1%}"
            else:
                val_display = f"{r['roll_value']:.0f}"

            label_with_val = f"{r['label']} [{val_display}]"
            print(
                f"║ {label_with_val:<18} | {r['percent_increase']:>8.2%}  | +{r['damage_increase']:<6.0f} | {r['score']:>6.0f}分  ║")

        print("╚" + "═" * 70 + "╝")