# models.py
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any, Union
from enum import Enum


# --- 0. 枚举定义 ---
class ElementType(str, Enum):
    Physical = "Physical"
    Pyro = "Pyro"
    Hydro = "Hydro"
    Electro = "Electro"
    Cryo = "Cryo"
    Dendro = "Dendro"
    Anemo = "Anemo"
    Geo = "Geo"
    Null = "null"


class SkillType(str, Enum):
    Normal = "NormalAttack"
    Charged = "ChargedAttack"
    Plunging = "PlungingAttack"
    Skill = "ElementalSkill"
    Burst = "ElementalBurst"
    MoonBloom = "MoonBloom"


# 🟢 [修改] 属性类型枚举 (已精简与补全)
class StatType(str, Enum):
    # --- 基础属性 ---
    HP = "hp"
    HP_Flat = "hp_flat"
    HP_Percent = "hp_percent"

    ATK = "atk"
    ATK_Flat = "atk_flat"
    ATK_Percent = "atk_percent"

    DEF = "def"
    DEF_Flat = "def_flat"
    DEF_Percent = "def_percent"

    EM = "em"
    ER = "energy_recharge"
    ER_Bonus = "energy_recharge_bonus"  # 兼容部分数据源

    # --- 双暴 ---
    CritRate = "crit_rate"
    CritDmg = "crit_dmg"

    # --- 高级属性 ---
    HealBonus = "healing_bonus"
    DmgBonus = "damage_bonus"  # 全伤害加成
    AllDmgBonus = "all_damage_bonus"  # 别名

    # --- 元素增伤 (统一入口) ---
    # 配合 element 字段使用，如 element="Pyro"
    ElementalBonus = "elemental_bonus"

    # --- 动作增伤 ---
    NormalBonus = "normal_bonus"
    ChargedBonus = "charged_bonus"
    PlungingBonus = "plunging_bonus"
    SkillBonus = "skill_bonus"
    BurstBonus = "burst_bonus"

    # --- 反应系数加成 (之前缺失的) ---
    Vaporize = "vaporize"  # 蒸发
    Melt = "melt"  # 融化
    Aggravate = "aggravate"  # 超激化
    Spread = "spread"  # 蔓激化

    # --- 特殊/削弱/倍率区 ---
    IgnoreDef = "ignore_def"  # 无视防御
    DefReduction = "def_reduction"  # 减防 (如草二)
    ResReduction = "resistance_percent"  # 减抗
    BaseMultAdd = "base_multiplier_add"  # 基础倍率区增加 (如昔时之歌、云堇)

    # --- 月体系 (自定义) ---
    MoonDmgBonus = "moon_dmg_bonus"
    MoonBasePct = "moon_base_pct"
    MoonBaseFlat = "moon_base_flat"
    AscensionMult="ascension_mult"

# --- 1. 基础组件模型 ---
class Multiplier(BaseModel):
    # 🟢 支持 StatType 枚举或字符串
    type: Union[StatType, str] = Field(..., description="倍率类型，如 atk_percent")
    value: Union[float, str] = Field(..., description="数值(兼容公式)")


# --- 2. 技能详细属性 ---
class SkillAttributes(BaseModel):
    multipliers: List[Multiplier] = Field(default_factory=list)
    element: Union[ElementType, str] = Field(default=ElementType.Physical)
    damage_type: Union[SkillType, str] = Field(default=SkillType.Skill)

    @validator('element', pre=True)
    def clean_element(cls, v):
        if not v or v == "": return "Physical"
        return v

    @validator('damage_type', pre=True)
    def clean_damage_type(cls, v):
        mapping = {
            "attack": SkillType.Normal,
            "Charged": SkillType.Charged,
            "Skill": SkillType.Skill,
            "Burst": SkillType.Burst,
            "plunging": SkillType.Plunging,
            "MoonBloom": SkillType.MoonBloom,
            "": SkillType.Skill
        }
        return mapping.get(v, v)


# --- 3. 技能组包装器 ---
class SkillGroup(BaseModel):
    default: SkillAttributes = Field(default_factory=SkillAttributes)


# --- 4. 技能集合 ---
class Skills(BaseModel):
    NormalAttack: SkillGroup = Field(default_factory=SkillGroup, alias="NormalAttack")
    ChargedAttack: SkillGroup = Field(default_factory=SkillGroup, alias="ChargedAttack")
    PlungingAttack: SkillGroup = Field(default_factory=SkillGroup, alias="PlungingAttack")
    ElementalSkill: SkillGroup = Field(default_factory=SkillGroup, alias="ElementalSkill")
    ElementalBurst: SkillGroup = Field(default_factory=SkillGroup, alias="ElementalBurst")

    class Config:
        populate_by_name = True


# --- 5. 基础面板 ---
class BaseStats(BaseModel):
    elements: List[str] = Field(default=["Physical"])
    atk: float = Field(default=0.0)
    hp: float = Field(default=0.0)
    defense: float = Field(default=0.0, alias="def")
    crit_rate: float = Field(default=0.05)
    crit_dmg: float = Field(default=0.5)
    em: float = Field(default=0.0)
    energy_recharge_bonus: float = Field(default=0.0)

    class Config:
        populate_by_name = True


# --- 6. Buff 模型 ---
class Buff(BaseModel):
    # 🟢 支持 StatType 枚举或字符串
    type: Union[StatType, str] = Field(..., description="Buff类型")
    value: Union[float, str] = Field(..., description="数值或动态表达式")
    scope: str = "self"
    element: str = "null"


# --- 7. 聚合数据 ---
class CharacterData(BaseModel):
    base_stats: BaseStats = Field(default_factory=BaseStats)
    skills: Skills = Field(default_factory=Skills)
    buffs: List[Buff] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class CalculationRequest(BaseModel):
    target_char: str
    teammates: List[str] = []
    skill_type: str = "ElementalBurst"
    reaction: Optional[str] = ""
    forced_set: Optional[str] = None