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
1. 한 턴에 몬스터는 AP가 허용하는 한 **여러 개의 스킬을 순차적으로 사용할 수 있습니다.**
2. 모든 **스킬은 최대 한 번만 사용**할 수 있습니다.
3. 남은 AP가 허용할 때까지 **최대한 많은 행동을 출력**하세요. 만약 AP가 남았다면 사용할 수 있는 다른 스킬을 탐색하세요.
4. AP가 0인 스킬을 제외한 스킬은 AP를 소모하며, 스킬 사용에 필요한 AP가 부족하면 스킬을 사용할 수 없습니다.
5. 행동을 할 때 **사용한 AP와 남은 AP를 주의**하여 행동하세요.
6. AP는 턴이 시작할 때 1씩 회복되며, 남은 AP는 다음 턴에 사용할 수 있습니다.
7. 몬스터는 플레이어와의 전투에서 승리하는 것을 목표로 행동합니다.
8. 몬스터의 스킬 정보와 특성 정보를 반영하여 행동하세요.
9. 상태 효과 정보를 활용하여 전략적으로 행동하세요.

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

행동 대상 몬스터: [{target_id}] {target_name}

몬스터의 스킬 정보:
{target_skills_info}

상태 효과 정보:
{status_effects_info}

몬스터의 특성 정보:
{target_traits_info}
"""

