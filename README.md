👑 原神全自动圣遗物遗传算法优化器 (Ultra-Detailed Guide)
本工具是一个基于遗传算法的工业级伤害模拟器。它通过自动装配圣遗物、判定套装效果、并结合角色自身天赋 (Self-Buff) 与 队友 Buff (Team-Buff)，在数以亿计的组合中寻找全局最优解。

🛠 一、 核心逻辑与数据流
本工具的运算核心分为两个阶段：

预处理阶段：加载角色白字，合并 Self-Buff 与 Team-Buff 形成“固定面板”。

进化搜索阶段：遗传算法不断尝试圣遗物组合，实时计算套装加成，并通过 DamageCalculator 输出期望伤害。

二、 参数配置详解：手动调参必读
1. main.py：实验场配置
在 main.py 中，你需要定义当前的战斗环境。

target_char: 对应 characters.json 中的键名（如 "leishen"）。

skill_type (重中之重): 决定了技能倍率的取值方向及圣遗物增伤匹配。

可选值: NormalAttack, ChargedAttack, ElementalSkill, ElementalBurst, PlugingAttack。

reaction (元素反应):

增幅类: vaporize_hydro (水蒸发), melt_pyro (火融化)。

剧变/平伤类: aggravate (超激化), spread (蔓激化)。

others (防御与抗性区):

enemy_level: 默认 100。

resistance_percent: 减抗后的敌人抗性（如 10% 初始减去 40% 翠绿 = -0.3）。

2. characters.json：Self-Buff 与 技能倍率
此文件定义角色自身的机制。

base_stats: 角色 90 级 + 武器 90 级的基础白字（攻击/生命/防御）。

skills: 存储不同技能类型的倍率。支持混合缩放（例如：atk_percent + em）。

buffs (Self): 只作用在角色自身的buff,当角色作为计算目标是会参考。
buffs (Team): 会作用到计算目标身上的buff。

示例：龙王的 30% 水伤天赋，在此添加 { "type": "elemental_bonus", "value": 0.30, "element": "Hydro" }。


三、 圣遗物自动化导入 (YAS + Parser)
本工具支持从游戏直接同步数据：

扫描: 使用 raw/yas.exe 扫描游戏内圣遗物。

生成: 得到 mona.json。

转换: 运行 parser(yas_converter).py。

该脚本会将莫娜格式转化为本项目标准的 artifacts.json。

注意: 转换时会保留 ID，方便你通过 ID 在游戏中定位那件“极品圣遗物”。

四、 关键字段查阅字典 (基于 buff_types.md)
如果你不确定在 set_effects.json 或 buffs 里该填什么，请务必严格遵守下表。填错一个字母都会导致该乘区失效。

乘区分类	字段名 (Type)	适用场景
基础区	atk_percent / atk_flat	攻击力加成（百分比按白字算）
hp_percent / hp_flat	生命值加成
em	元素精通
增伤区	damage_bonus	全元素/全伤害加成
elemental_bonus	对应 element 类型的元素伤害
charged_bonus	重击专属增伤 (需匹配 ChargedAttack)
skill_bonus	元素战技专属增伤 (需匹配 ElementalSkill)
双暴区	crit_rate / crit_dmg	暴击率 / 暴击伤害
特殊区	def_reduction	减防 (如雷神2命/草神2命)
resistance_percent	减抗 (如风套/钟离)

导出到 Google 表格

五、 套装效果配置说明 (set_effects.json)
本文件决定了“4件套”到底有多强。

关键点：4 件套效果中的 type 必须与 main.py 的 skill_type 逻辑闭环。

例子：如果你计算的是龙王重击，而圣遗物写的是 skill_bonus，那么龙王是吃不到这部分加成的。必须写 charged_bonus 或者通用的 damage_bonus。

六、 开发者调试建议
验证面板：运行后，观察控制台输出的 [4] 队友后固定面板。如果这里的攻击力或增伤和你手动算的对不上，请检查 team_buffs。

验证增伤：在 _calculate_panel_and_bonus 函数中，如果 p["all_damage_bonus"] 的数值异常（比如 1.0），说明圣遗物套装的 type 与 skill_type 不匹配。

算法效率：如果你圣遗物超过 1000 件，建议将 main.py 中的 population_size 调至 800 以上，以防止陷入局部最优解。

重中之重：所有参数的拼写（如 PlugingAttack 还是 PlungingAttack）必须全局统一。请参考 buff_types.md 作为最终真理。

七、直接运行app.py，支持直接修改哦