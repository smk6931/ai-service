import json
from pathlib import Path

def load_skills(path='app/data/skills.json'):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
    
skills = load_skills()

prompt_combat_rules = """
당신은 턴제 RPG 게임의 몬스터 AI입니다.
아래의 전투 상황을 바탕으로, 몬스터가 이번 턴에 수행할 가장 적절한 행동들을 판단하고,
JSON 형식으로 출력하세요.

전투 규칙:
1. 한 턴에 몬스터는 AP가 허용하는 한 **여러 개의 스킬을 순차적으로 사용할 수 있습니다.**
2. 모든 스킬은 한 번만 사용할 수 있으며, 남은 AP가 허용할 때까지 **최대한 많은 행동을 출력**하세요.
3. 스킬은 AP를 소모하며, 스킬 사용에 필요한 AP가 부족하면 스킬을 사용할 수 없습니다.
4. AP는 턴이 시작할 때 1씩 회복되며, 남은 AP는 다음 턴에 사용할 수 있습니다.
5. 몬스터는 플레이어를 쓰러뜨리는 것을 목표로 행동합니다.

전투 상황:
{battle_state}

출력 시 반드시 대상 캐릭터는 이름이 아닌 ID를 사용하세요.
출력 형식:
{format}
"""

prompt_combat_state_template = """
주기: {cycle}
턴: {turn}
지형: {terrain}
날씨: {weather}

몬스터 목록:
{monster_text}

플레이어 목록:
{player_text}

행동 대상 몬스터: [{target_id}] {target_name}

{target_skills_info}
"""

