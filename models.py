from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any, Union
from enum import Enum


# --- 0. 枚举定义 (核心规范) ---
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


# --- 1. 基础组件模型 (倍率) ---
class Multiplier(BaseModel):
    type: str = Field(..., description="倍率类型，如 atk_percent")
    value: float = Field(..., description="数值")


# --- 2. 技能详细属性 ---
class SkillAttributes(BaseModel):
    multipliers: List[Multiplier] = Field(default_factory=list)
    # 强制使用 Enum，如果 JSON 是空字符串或旧格式，通过 validator 修正
    element: Union[ElementType, str] = Field(default=ElementType.Physical)
    damage_type: Union[SkillType, str] = Field(default=SkillType.Skill)

    @validator('element', pre=True)
    def clean_element(cls, v):
        if not v or v == "": return "Physical"
        return v

    @validator('damage_type', pre=True)
    def clean_damage_type(cls, v):
        # 兼容旧版 JSON 的写法
        mapping = {
            "attack": SkillType.Normal,
            "Charged": SkillType.Charged,
            "Skill": SkillType.Skill,
            "Burst": SkillType.Burst,
            "plunging": SkillType.Plunging,
            "": SkillType.Skill
        }
        return mapping.get(v, v)


# --- 3. 技能组包装器 ---
class SkillGroup(BaseModel):
    default: SkillAttributes = Field(default_factory=SkillAttributes)


# --- 4. 技能集合 ---
class Skills(BaseModel):
    NormalAttack: SkillGroup = Field(default_factory=SkillGroup, title="普通攻击")
    ChargedAttack: SkillGroup = Field(default_factory=SkillGroup, title="重击")
    PlungingAttack: SkillGroup = Field(default_factory=SkillGroup, title="下落攻击")
    ElementalSkill: SkillGroup = Field(default_factory=SkillGroup, title="元素战技 (E)")
    ElementalBurst: SkillGroup = Field(default_factory=SkillGroup, title="元素爆发 (Q)")

    class Config:
        populate_by_name = True


# --- 5. 基础面板 ---
class BaseStats(BaseModel):
    elements: List[str] = Field(default=["Physical"])
    atk: float = Field(default=300)
    hp: float = Field(default=12000)
    def_: float = Field(default=700, alias="def")
    crit_rate: float = Field(default=0.05)
    crit_dmg: float = Field(default=0.5)
    em: float = Field(default=0)
    energy_recharge_bonus: float = Field(default=0.0)

    class Config:
        populate_by_name = True


# --- 6. Buff 模型 ---
class Buff(BaseModel):
    type: str
    value: float
    scope: str = "self"
    element: str = "null"


# --- 7. 聚合数据 ---
class CharacterData(BaseModel):
    base_stats: BaseStats = Field(default_factory=BaseStats)
    skills: Skills = Field(default_factory=Skills)
    buffs: List[Buff] = Field(default_factory=list)


class CalculationRequest(BaseModel):
    target_char: str
    teammates: List[str] = []
    skill_type: str = "ElementalBurst"
    reaction: Optional[str] = ""

# --- 8. 圣遗物模型 ---
class ArtifactStat(BaseModel):
    type: str = Field(..., description="属性类型，如 crit_rate")
    value: float = Field(..., description="数值")
    element: str = Field(default="null", description="元素类型，通常为 null，杯子可能有具体元素")

class Artifact(BaseModel):
    id: Optional[int] = Field(None, description="圣遗物唯一ID，添加时可不填，由后端生成")
    set: str = Field(..., description="套装名称，如 绝缘之旗印")
    slot: str = Field(..., description="部位: flower, plume, sands, goblet, circlet")
    main_stat: ArtifactStat = Field(..., description="主词条")
    substats: List[ArtifactStat] = Field(default_factory=list, description="副词条列表")

    class Config:
        populate_by_name = True