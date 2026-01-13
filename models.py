from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union

# --- 基础组件模型 ---
class Multiplier(BaseModel):
    type: str
    value: float

class SkillDetail(BaseModel):
    element: str = "Physical"
    damage_type: str = "Skill"
    multipliers: List[Multiplier] = []

class SkillGroup(BaseModel):
    default: SkillDetail = Field(default_factory=SkillDetail)

class BaseStats(BaseModel):
    elements: List[str] = ["Physical"]
    atk: int = 300
    hp: int = 12000
    defense: int = Field(700, alias="def") # JSON中是def，Python中是defense
    crit_rate: float = 0.05
    crit_dmg: float = 0.5
    em: int = 0

    class Config:
        populate_by_name = True

class Buff(BaseModel):
    type: str
    value: float
    scope: str = "self"     # self 或 team
    element: str = "null"   # 触发元素

# --- 聚合模型 ---
class CharacterData(BaseModel):
    base_stats: BaseStats = Field(default_factory=BaseStats)
    skills: Dict[str, SkillGroup] = {}
    buffs: List[Buff] = []

class CalculationRequest(BaseModel):
    target_char: str
    teammates: List[str] = []
    skill_type: str
    reaction: Optional[str] = None