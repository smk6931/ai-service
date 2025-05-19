from typing import List, Optional, Tuple, Literal, Dict
from pydantic import BaseModel

class Character(BaseModel):
    id: str
    name: str
    type: Literal["player", "monster"]
    traits: List[str]
    skills: List[str]
    position: Tuple[int, int]
    hp: int
    ap: int
    mov: int
    status_effects: List[str]

class ActionPlan(BaseModel):
    move_to: Optional[Tuple[int, int]]
    skill: Optional[str]
    target_character_id: Optional[str]
    reason: Optional[str]
    remaining_ap: Optional[int]
    remaining_mov: Optional[int]
    dialogue: Optional[str] = None

class LangGraphBattleState(BaseModel):
    cycle: int
    turn: int
    terrain: str
    weather: str
    current_character_id: str
    characters: List[Character]

    resource_info: Optional[Dict[str, int]] = None
    personality_weights: Optional[Dict[str, float]] = None

    battle_log: List[str] = []
    battle_summary: Optional[str] = None

    strategy: Optional[str] = None
    target_character_id: Optional[str] = None
    action_plan: Optional[ActionPlan] = None
    dialogue: Optional[str] = None
    trace: Optional[List[str]] = None
    