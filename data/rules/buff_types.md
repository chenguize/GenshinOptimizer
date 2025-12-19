# 原神伤害计算规则终极版

engine 默认攻击角色可吃到所有 Buff，所有 Buff 类型严格落到乘区计算。

---

# 一、伤害公式总览

# 超激化 / 蔓激化类（TransformativeReaction）
FinalDamage_Transformative =
(BaseMultiplier + TransformativeReactionBonus)
× (1 + ΣStatPercent + ΣFlatBonus)
× (1 + ΣDamageBonus)
× (1 + CritRate × CritDamage)
× DefenseMultiplier
× ResistanceMultiplier

# 增幅类（Amplifying / Vaporize / Melt）
FinalDamage_Amplifying =
BaseMultiplier
× ReactionMultiplier
× (1 + ΣStatPercent + ΣFlatBonus)
× (1 + ΣDamageBonus)
× (1 + CritRate × CritDamage)
× DefenseMultiplier
× ResistanceMultiplier



---

# 二、公式拆解

## 1. BaseMultiplier（基础倍率区）

### 1.1 技能基础倍率

BaseMultiplier_skill =
SkillMultiplier
+ Σ(skill_type_bonus)

- `SkillMultiplier`：技能自带倍率（普攻/重击/下落/战技/爆发）
- `Σ(skill_type_bonus)`：队友技能带来的专属加成  

---

### 1.2 激化 / 蔓激化 / 超激化提升值公式

Reaction_Flat_DMG = LevelMultiplier * Reaction_Coefficient * (1 + 5 * EM / (EM + 1200) + reaction_bonus_buff)

**参数说明**：

| 参数 | 描述 |
|------|------|
| LevelMultiplier | 角色等级系数，例如 90级：1446.858，80级：1077.44 |
| Reaction_Coefficient | 反应倍率系数：蔓激化 (Spread)=1.25，超激化 (Aggravate)=1.15 |
| EM | 攻击角色元素精通面板值 |
| reaction_bonus_buff | Buff 增加的激化加成，例如「如雷的盛怒」4件套 20% |

> ⚠️ 注：每次计算只选择一个反应类型，激化/蔓激化/超激化二选一。

---

### 1.3 BaseMultiplier 总和

BaseMultiplier_total = 
    BaseMultiplier_skill * (Total_ATK or Total_HP or Total_DEF or Total_EM or multiple_stats)
    + Reaction_Flat_DMG
    + skill_type_bonus


- `Reaction_Flat_DMG`：根据当前触发的反应类型选择 **蔓激化/超激化**  
- 保证 **同一计算只选择一个 TransformativeReaction**

---

### 1.4 LevelMultiplier 示例表

| 角色等级 | LevelMultiplier |
|----------|----------------|
| 90       | 1446.858       |
| 80       | 1077.44        |
| 70       | 847.52         |
| 60       | 659.08         |
默认就拿90级的数据

## 2. ReactionMultiplier（元素反应区）

本乘区仅在触发 **蒸发 (Vaporize)** 或 **融化 (Melt)** 反应时生效。

### 2.1 核心计算公式

Reaction_Multiplier_Total = Base_Reaction_Multiplier * (1 + EM_Bonus + Reaction_Specific_Bonus)

### 2.2 数值常量说明

#### A. 基础反应倍率 (Base_Reaction_Multiplier)
根据触发元素和附着元素的先后顺序，存在“强反应”和“弱反应”之分：

| 反应类型 | 触发顺序 | 基础倍率 K |
|----------|----------|------------|
| 融化 (Melt) | 火打击冰 (Pyro on Cryo) | 2.0 |
| 蒸发 (Vaporize) | 水打击火 (Hydro on Pyro) | 2.0 |
| 融化 (Melt) | 冰打击火 (Cryo on Pyro) | 1.5 |
| 蒸发 (Vaporize) | 火打击水 (Pyro on Hydro) | 1.5 |

#### B. 元素精通收益 (EM_Bonus)

精通对增幅反应的加成是非线性的，公式如下：

EM_Bonus = 2.78 * EM / (EM + 1400)

- 注意：此处的 `EM` 是加上所有 `elemental_mastery_buff` 后的最终面板精通  
- 示例：若角色最终精通为 200，则  
EM_Bonus = 2.78 * 200 / (200 + 1400) ≈ 0.3475 (即 34.75%)

### 2.3 Buff 类型处理逻辑

| Buff 类型 | 描述 | 处理方式 |
|-----------|------|---------|
| elemental_mastery_buff | 提供的额外精通数值 | 直接加到角色精通面板上，再代入 EM_Bonus 公式 |
| reaction_multiplier | 特定的反应系数加成（如「炽烈的炎之魔女」4件套、「饰金之梦」） | 直接加到 `Reaction_Specific_Bonus` 中，例如提升蒸发/融化伤害 15% |

> ⚠️ 激化/蔓激化不在此区，直接加到 BaseMultiplier

---

## 3. Stat Scaling（属性区）

- Buff 类型：
  - `atk_percent`, `atk_flat`  
  - `hp_percent`, `hp_flat`  
  - `def_percent`, `def_flat`  
  - `em`, `bonus_stat`

公式示例：

StatContribution =
(BaseATK × (1 + Σatk_percent) + Σatk_flat)

(BaseHP × (1 + Σhp_percent) + Σhp_flat) * hp_to_atk_ratio

...


> ⚠️ 可支持多属性数组，例如雷 + 草组合，元素精通影响增幅类反应

---

## 4. Damage Bonus（增伤区）

- 功能：所有百分比增伤叠加（普攻 /重击/ 下落/战技 / 爆发 / 元素）  
- Buff 类型：
  - `damage_bonus`：通用增伤  
  - `elemental_bonus`：元素伤害增伤  
  - `skill_bonus`：元素战技增伤  
  - `burst_bonus`：元素爆发增伤
  - `attack_bonus`：普攻增伤
  - `charged_bonus`：重击增伤
  - `plunging_bonus`：下落攻击增伤

### 4.1 核心计算公式

DamageBonusMultiplier = 1 + Σ(all_damage_bonus)

- `all_damage_bonus`：指所有作用在**目标角色**上的增伤加成  
- ⚠️ 关键说明：在计算角色圣遗物或 Buff 时，必须明确 **计算的目标角色**，保证不同角色的增伤互不混淆

### 4.2 示例

- 雷神计算元素爆发伤害时：
  - 元素爆发增伤 +20%（来自圣遗物）  
  - 元素伤害增伤 +15%（来自队伍 Buff）  
  - 总增伤加成：
    ```
    DamageBonusMultiplier = 1 + 0.2 + 0.15 = 1.35
    ```
- 注意：如果目标是雷神的元素战技，则需重新收集该角色面板的增伤 Buff



---

## 5. CritMultiplier（暴击区）

- Buff 类型：
  - `crit_rate`, `crit_dmg`

公式：

CritMultiplier = 1 + CritRate × CritDmg

---

## 6. DefenseMultiplier（防御区）

公式：

DefenseMultiplier =
(AttackerLevel + 100)
/
((AttackerLevel + 100) + (EnemyLevel + 100) * (1 - DefReduction) * (1 - DefIgnore))

- Buff 类型：
  - `def_reduction`, `def_ignore`  
- 注意：减防与无视防御 **乘算，不相加**

---

## 7. ResistanceMultiplier（抗性区）

公式：

if res < 0:
ResistanceMultiplier = 1 - res / 2
elif res < 0.75:
ResistanceMultiplier = 1 - res
else:
ResistanceMultiplier = 1 / (1 + 4 * res)


- Buff 类型：
  - , `resistance_percent`

---

# 三、技能类型分类

| 技能类型 | 描述 |
|----------|------|
| NormalAttack | 普攻伤害 |
| ChargedAttack | 重击伤害 |
| PlungeAttack | 下落伤害 |
| ElementalSkill | 元素战技 |
| ElementalBurst | 元素爆发 |

- Buff 类型 `skill_type_bonus` 可针对某个技能类型

---

# 四、元素反应类型

| 类型 | 落区 | 可暴击 |
|------|------|---------|
| Vaporize / Melt | ReactionMultiplier | ❌ |
| Overload / Electro-Charged | ReactionMultiplier | ❌ |
| Superconduct | ReactionMultiplier | ❌ |
| Swirl / Spread | ReactionMultiplier | ❌ |
| Aggravate / Bloom | BaseMultiplier | ✅ |
| Crystallize | ReactionMultiplier | ❌ |

- 激化/蔓激化 (TransformativeReaction) 加到基础乘区，
- 增幅类（蒸发/融化）加到 ReactionMultiplier

---

# 五、Buff 类型枚举

## 1. BaseMultiplier

| 类型 | 描述 |
|------|------|
| base_multiplier_add | 技能倍率/固定伤害/激化/蔓激化加成 |
| skill_type_bonus    | 对特定技能类型加成 |
| transformative_reaction | 激化/蔓激化类，乘到基础倍率区，可暴击 |

## 2. Stat Scaling

| 类型 | 描述 |
|------|------|
| atk_percent | 攻击力百分比加成 |
| atk_flat    | 固定攻击力加成 |
| hp_percent  | 生命百分比加成 |
| hp_flat     | 固定生命加成 |
| def_percent | 防御百分比加成 |
| def_flat    | 固定防御加成 |
| em         | 元素精通 |
| bonus_stat | 其他面板加成（充能、元素精通等） |

## 3. Damage Bonus

| 类型 | 描述 |
|------|------|
| damage_bonus   | 通用增伤 |
| elemental_bonus| 特定元素增伤 |
| physical_bonus | 物理伤害增伤 |
| skill_bonus    | 技能专属增伤 |
| burst_bonus    | 元素爆发增伤 |

## 4. Crit

| 类型 | 描述 |
|------|------|
| crit_rate   | 暴击率加成 |
| crit_damage | 暴击伤害加成 |

## 5. Defense

| 类型 | 描述 |
|------|------|
| def_reduction | 减防百分比 |
| def_ignore    | 无视防御百分比 |

## 6. Resistance

| 类型 | 描述 |
|------|------|

| resistance_percent | 百分比抗性调整（可负） |


## 7. Reaction Multiplier

| 类型 | 描述 |
|------|------|
| reaction_multiplier       | 增幅类（蒸发/融化）增伤，乘到元素反应区 |
| transformative_reaction   | 激化/蔓激化类，乘到基础倍率区，可暴击 |

## 8. 其他特殊 Buff

| 类型 | 描述 |
|------|------|
| energy_recharge_bonus | 充能效率加成 |
| cooldown_reduction    | 技能冷却缩减 |
| elemental_mastery_buff| 元素精通增益（影响扩散/激化/反应倍率） |
| shield_bonus          | 盾加成（辅助防御，不直接算伤） |

---

# 六、使用原则

1. engine 默认攻击角色可吃到所有 Buff  
2. 每个 Buff 的 `effect.type` 决定落区  
3. 落区与公式一一对应，保证计算可控  
4. 激化/蔓激化加到基础倍率区，可暴击  
5. 增幅类加到元素反应区，不可暴击