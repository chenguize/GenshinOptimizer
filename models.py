from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union

# --- 1. 基础组件模型 (倍率) ---
class Multiplier(BaseModel):
    type: str = Field(..., description="倍率类型，如 atk_percent")
    value: float = Field(..., description="数值")

# --- 2. 技能详细属性 (对应 JSON 中的 "default": { ... } 内容) ---
class SkillAttributes(BaseModel):
    multipliers: List[Multiplier] = Field(default_factory=list, description="倍率列表")
    element: str = Field(default="Physical", description="伤害元素类型")
    damage_type: str = Field(default="Skill", description="伤害类型分类")

# --- 3. 技能组包装器 (对应 JSON 中的 "NormalAttack": { ... } 这一层) ---
class SkillGroup(BaseModel):
    # 对应 JSON 里的 "default" 键
    default: SkillAttributes = Field(default_factory=SkillAttributes)

# --- 4. 核心修复：显式定义所有技能类型 ---
# 之前是 Dict[str, SkillGroup]，导致 API 不知道具体有哪些技能
class Skills(BaseModel):
    NormalAttack: SkillGroup = Field(default_factory=SkillGroup, title="普通攻击")
    ChargedAttack: SkillGroup = Field(default_factory=SkillGroup, title="重击")
    PlungingAttack: SkillGroup = Field(default_factory=SkillGroup, title="下落攻击")
    ElementalSkill: SkillGroup = Field(default_factory=SkillGroup, title="元素战技 (E)")
    ElementalBurst: SkillGroup = Field(default_factory=SkillGroup, title="元素爆发 (Q)")

# --- 5. 基础面板 (BaseStats) ---
class BaseStats(BaseModel):
    elements: List[str] = Field(default=["Physical"], description="角色所属元素")
    atk: float = Field(default=300)
    hp: float = Field(default=12000)
    # 使用 def_ 避免 Python 关键字冲突，alias="def" 确保能读取 JSON 中的 def
    def_: float = Field(default=700, alias="def")
    crit_rate: float = Field(default=0.05)
    crit_dmg: float = Field(default=0.5)
    em: float = Field(default=0)
    # 之前漏掉了这个字段，导致读取时可能会丢数据
    energy_recharge_bonus: float = Field(default=0.0, description="元素充能效率")

    class Config:
        populate_by_name = True # 允许通过字段名(def_)或别名(def)赋值

# --- 6. Buff 模型 ---
class Buff(BaseModel):
    type: str
    value: float
    scope: str = "self"     # self 或 team
    element: str = "null"   # 触发元素限制

# --- 7. 聚合模型 (主入口) ---
class CharacterData(BaseModel):
    base_stats: BaseStats = Field(default_factory=BaseStats)
    # 这里引用上面定义的具体 Skills 类，而不是通用的 Dict
    skills: Skills = Field(default_factory=Skills)
    buffs: List[Buff] = Field(default_factory=list)

# --- 8. 计算请求模型 ---
class CalculationRequest(BaseModel):
    target_char: str
    teammates: List[str] = []
    skill_type: str = "ElementalBurst"
    reaction: Optional[str] = ""