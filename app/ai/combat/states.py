from typing import List, Optional, Tuple, Literal, Dict
from pydantic import BaseModel, Field

class Character(BaseModel):
    id: str = Field(description="캐릭터의 고유 식별자")
    name: str = Field(description="캐릭터의 이름")
    type: Literal["player", "monster"] = Field(description="캐릭터의 타입 (플레이어 또는 몬스터)")
    traits: List[str] = Field(description="캐릭터가 가진 특성 목록")
    skills: List[str] = Field(description="캐릭터가 사용 가능한 스킬 목록")
    position: Tuple[int, int] = Field(description="캐릭터의 현재 위치 좌표 (x, y)")
    hp: int = Field(description="캐릭터의 현재 체력")
    ap: int = Field(description="캐릭터의 현재 행동력 (Action Points)")
    mov: int = Field(description="캐릭터의 현재 이동력 (Movement Points)")
    status_effects: List[str] = Field(description="캐릭터에게 적용된 상태 이상 효과 목록")

class ActionPlan(BaseModel):
    move_to: Optional[Tuple[int, int]] = Field(
        description="이동할 목표 위치 좌표 (x, y). 현재 위치를 유지하려면 현재 위치와 동일한 값을 사용하세요."
    )
    skill: Optional[str] = Field(
        description="사용할 스킬의 이름. 대기하려면 None을 사용하세요."
    )
    target_character_id: Optional[str] = Field(
        description="스킬의 대상이 되는 캐릭터의 ID. 자기 자신을 대상으로 할 경우 자신의 ID를 사용하세요."
    )
    reason: Optional[str] = Field(
        description="이 행동을 선택한 이유에 대한 간단한 설명"
    )
    remaining_ap: Optional[int] = Field(
        description="스킬 사용 후 남은 행동력 (AP)"
    )
    remaining_mov: Optional[int] = Field(
        description="이동 후 남은 이동력 (MOV)"
    )
    dialogue: Optional[str] = Field(
        default=None,
        description="캐릭터가 행동과 함께 말할 대사"
    )

class LangGraphBattleState(BaseModel):
    cycle: int = Field(description="현재 전투의 라운드 번호")
    turn: int = Field(description="현재 라운드 내의 턴 번호")
    terrain: str = Field(description="전투가 진행되는 지형의 종류")
    weather: str = Field(description="현재 날씨 상태")
    current_character_id: str = Field(description="현재 행동할 차례인 캐릭터의 ID")
    characters: List[Character] = Field(description="전투에 참여한 모든 캐릭터의 목록")

    resource_info: Optional[Dict[str, int]] = Field(
        default=None,
        description="현재 캐릭터의 자원 상태 정보 (HP 비율, AP, MOV 등)"
    )
    personality_weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="캐릭터의 성격 특성에 따른 행동 가중치"
    )

    battle_log: List[str] = Field(
        default_factory=list,
        description="전투 중 발생한 이벤트들의 로그"
    )
    battle_summary: Optional[str] = Field(
        default=None,
        description="현재까지의 전투 상황 요약"
    )

    strategy: Optional[str] = Field(
        default=None,
        description="현재 캐릭터가 선택한 전략"
    )
    target_character_id: Optional[str] = Field(
        default=None,
        description="현재 캐릭터가 주로 타겟으로 삼고 있는 캐릭터의 ID"
    )
    action_plan: Optional[ActionPlan] = Field(
        default=None,
        description="현재 캐릭터의 행동 계획"
    )
    dialogue: Optional[str] = Field(
        default=None,
        description="현재 캐릭터의 대사"
    )
    trace: Optional[List[str]] = Field(
        default=None,
        description="AI의 의사결정 과정을 추적하기 위한 로그"
    )
    