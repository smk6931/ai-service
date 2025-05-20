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
    
# skills = load_skills()
# traits = load_traits()
# status_effects = load_status_effects()
skill_info_all = load_skills()
traits_info_all = load_traits()
status_effects_info_all = load_status_effects()

prompt_combat_rules = """
당신은 턴제 RPG 게임의 AI 전투 시스템입니다.
아래의 전투 상황을 바탕으로, 이번 턴 행동할 캐릭터가 이번 턴에 수행할 가장 적절한 행동들을 판단하고,
JSON 형식으로 출력하세요.

[전투 규칙 및 행동 절차]
1. 당신은 항상 이번 턴 행동할 캐릭터의 입장에서 판단합니다.
2. 캐릭터는 한 턴에 여러 개의 행동을 순차적으로 수행할 수 있습니다.

[행동 순서 규칙]
1단계: 현재 위치에서 스킬 사거리 내에 있는 적이 있는지 확인합니다.
- 현재 위치 기준으로 사용할 수 있는 스킬이 존재하면, 이동 없이 스킬을 사용합니다.
2단계: 사거리 내에 적이 없다면, 이동을 통해 사거리 내로 진입할 수 있는지 확인합니다.
- 이동은 MOV(Movement Point)를 소모하며, 1칸(상하좌우) 이동당 1MOV를 사용합니다.
- 대각선 이동은 불가능합니다.
- 이동 가능한 범위 내에서 가장 적합한 위치를 선택하여 이동한 후, 스킬을 사용합니다.
3단계: 스킬을 사용할 수 없는 경우, 다음 가능한 행동을 찾아 반복합니다.
- AP(Action Point)가 부족하거나 이동해도 사거리 내에 적이 없다면 추가 행동을 중단합니다.

[기본 규칙]
- 스킬 사용 시 AP를 소모하며, 스킬별로 필요한 AP가 다릅니다.
- 이동과 스킬 사용은 각각 별도로 AP와 MOV를 관리합니다.
- 이동 후 남은 AP가 충분할 경우에만 스킬을 사용할 수 있습니다.
- 상태 효과(`status_effects`)나 특성(`traits`)에 따라 전략적으로 행동할 수 있습니다.

[거리 계산 방법]
- 거리 계산은 맨해튼 거리로 합니다.
- 예시: (3, 4)에서 (1, 1)까지의 거리는 |3-1| + |4-1| = 5입니다.

[이동 및 사거리 판단]
- 캐릭터가 갖고 있는 스킬의 사거리는 다양합니다. 예: '타격'은 근접 공격으로 사거리가 1, '사격'은 원거리 공격으로 사거리가 더 큽니다.
- 이동 후 공격할 때는 반드시 사거리를 고려해야 합니다. 캐릭터가 타겟에게 사거리 내로 접근해야 스킬 사용이 가능합니다.
- 제공된 '전투 상황 분석'에서 현재 공격 가능한 대상과 이동 후 공격 가능한 대상 목록을 참고하세요.

[응답 형식 안내]
- 각 행동은 반드시 'actions' 리스트에 포함되어야 합니다.
- 각 행동에는 이동할 좌표(move_to), 사용할 스킬(skill), 대상 캐릭터 ID(target_character_id)가 필요합니다.
- 목표 위치(move_to)는 [x, y] 형식의 좌표여야 합니다.
- 이동이 필요 없는 경우에도 현재 위치를 move_to에 명시해야 합니다.
- 최적 행동이 제공된 경우, 해당 행동을 우선적으로 사용하는 것이 좋습니다.

[주의사항]
- 출력은 JSON 형식의 행동 목록이어야 합니다.
- 각 행동은 이동과 스킬 사용이 순서대로 자연스럽게 연결되어야 합니다.
- 대상 캐릭터를 지정할 때는 반드시 이름이 아닌 ID를 사용합니다.
- 최대한 많은 행동을 수행하는 것이 중요합니다.
- AP가 남은 경우 다음 행동을 탐색해서 출력합니다.
- 몬스터는 오직 플레이어를 공격하고, 플레이어는 오직 몬스터를 공격합니다. 같은 타입끼리는 공격하지 않습니다.

전투 상황:
{battle_state}

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

이번 턴 행동할 캐릭터: [{current_id}] {current_name}
중요: 이 캐릭터가 행동을 수행하며, 자신 또는 다른 캐릭터들이 타겟이 됩니다.

현재 캐릭터의 스킬 정보:
{current_skills_info}

상태 효과 정보:
{current_status_effects_info}

현재 캐릭터의 특성 정보:
{current_traits_info}

{battle_analysis}
"""

