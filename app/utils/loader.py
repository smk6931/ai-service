import json
from pathlib import Path

def load_skills(path='app/data/skill.json'):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
    
def load_traits(path='app/data/trait.json'):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
    
def load_status_effects(path='app/data/status_effect.json'):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
    
skills = load_skills()
traits = load_traits()
status_effects = load_status_effects()

prompt_combat_rules = """
당신은 턴제 RPG 게임의 몬스터 AI입니다.
아래의 전투 상황을 바탕으로, 몬스터가 이번 턴에 수행할 가장 적절한 행동들을 판단하고,
JSON 형식으로 출력하세요.

전투 규칙:
1. 캐릭터는 각 턴마다 여러 개의 행동을 순차적으로 수행할 수 있습니다.
2. 각 행동에는 다음과 같은 제약 조건이 존재합니다:
    - AP(Action Point): 행동 시 소모되며, 스킬 사용 시 반드시 필요합니다.
    - MOV(Movement Point): 이동 시 1칸당 1MOV를 소모합니다. 대각선 이동은 불가능하며, 한 턴에 여러 번 이동할 수 있습니다.
    - 현재 AP와 MOV 내에서만 행동할 수 있습니다.
3. 스킬 사용에는 다음 조건이 모두 충족되어야 합니다:
    - 해당 스킬의 이름이 현재 캐릭터가 보유한 `skills` 목록에 포함되어야 합니다.
    - 스킬을 사용할 대상이 존재해야 하며, 해당 대상은 스킬의 사거리(range) 내에 있어야 합니다.
    - 필요 시 `move_to` 필드를 통해 사거리 내로 먼저 이동한 후 스킬을 사용할 수 있습니다.
    - 이동한 후에도 남은 AP가 있어야 스킬을 사용할 수 있습니다.
4. 거리 계산 방식은 맨해튼 거리입니다.  
   예: (3, 4)에서 (1, 1)은 |3-1| + |4-1| = 5
5. 모든 캐릭터는 `(position)` 필드로 좌표가 주어지며, 스킬에는 사거리와 AP 소모량이 명시되어 있습니다.
6. `traits`, `status_effects`를 통해 캐릭터의 성격이나 상태 이상 정보를 활용하여 전략적으로 행동할 수 있습니다.
7. MonsterAction 필드:
   - move_to: 이동할 위치 좌표
   - skill: 사용할 스킬 이름
   - target_character_id: 타겟 캐릭터의 ID
   - reason: 행동 선택 이유
   - remaining_ap: 행동 후 남은 AP (시스템이 자동으로 계산)
   - remaining_mov: 행동 후 남은 MOV (시스템이 자동으로 계산)

전투 상황:
{battle_state}

출력 시 반드시 대상 캐릭터는 이름이 아닌 ID를 사용하세요.
출력 형식:
{format}
"""

prompt_battle_state_template = """
주기: {cycle}
턴: {turn}
지형: {terrain}
날씨: {weather}

몬스터 목록:
{monster_text}

플레이어 목록:
{player_text}

행동 대상 몬스터: [{current_id}] {current_name}

몬스터의 스킬 정보:
{target_skills_info}

상태 효과 정보:
{status_effects_info}

몬스터의 특성 정보:
{target_traits_info}
"""

