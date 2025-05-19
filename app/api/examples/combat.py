# /battle/start 요청 예시
BATTLE_START_REQUEST_EXAMPLE = {
  "characters": [
    {
      "id": "monster1",
      "name": "아이스 골렘",
      "type": "monster",
      "traits": ["충동적"],
      "skills": ["타격", "몸통 박치기", "생존 본능", "날카로운 발톱"]
    },
    {
      "id": "monster2",
      "name": "파이어 골렘",
      "type": "monster",
      "traits": ["겁쟁이"],
      "skills": ["타격", "포효", "방어 지휘"]
    },
    {
      "id": "player1",
      "name": "Player1",
      "type": "player",
      "traits": [],
      "skills": ["타격"]
    },
    {
      "id": "player2",
      "name": "Player2",
      "type": "player",
      "traits": [],
      "skills": ["타격"]
    }
  ],
  "terrain": "",
  "weather": ""
}

# /battle/start 응답 예시
BATTLE_START_RESPONSE_EXAMPLE = {
  "status": "success"
}

# /battle/action 요청 예시
BATTLE_ACTION_REQUEST_EXAMPLE = {
  "cycle": 1,
  "turn": 2,
  "current_character_id": "monster1",
  "characters": [
    {
      "id": "monster1",
      "position": [2, 14],
      "hp": 20,
      "ap": 4,
      "mov": 4,
      "status_effects": []
    },
    {
      "id": "monster2",
      "position": [2, 12],
      "hp": 80,
      "ap": 3,
      "mov": 4,
      "status_effects": []
    },
    {
      "id": "player1",
      "position": [1, 10],
      "hp": 90,
      "ap": 1,
      "mov": 4,
      "status_effects": []
    },
    {
      "id": "player2",
      "position": [3, 12],
      "hp": 100,
      "ap": 1,
      "mov": 4,
      "status_effects": []
    }
  ]
}

# /battle/action 응답 예시
BATTLE_ACTION_RESPONSE_EXAMPLE = {
  "current_character_id": "monster1",
  "action":
  {
      "move_to": [1, 11],
      "skill": "타격",
      "target_character_id": "player1",
      "reason": "충동적인 특성으로 인해 가까운 적인 Player1를 공격하는 것이 최적의 선택이며, 몸통 박치기는 근접 스킬로 유효한 공격입니다.",
      "remaining_ap": 4,
      "remaining_mov": 0
  }
}

# API 문서용 설명 텍스트

# /battle/start API 설명
BATTLE_START_DESCRIPTION = """
전투 시작 API - 캐릭터, 지형, 날씨 정보 설정

- **characters**: 전투에 참여하는 캐릭터 목록 (플레이어와 몬스터)
- **terrain**: 전투가 발생하는 지형
- **weather**: 전투 시 날씨 조건
"""

# /battle/action API 설명
BATTLE_ACTION_DESCRIPTION = """
전투 판단 API - 몬스터의 다음 행동 결정

- **characters**: 전투 참여 중인 캐릭터들의 현재 상태
- **cycle**: 현재 전투 사이클
- **turn**: 현재 턴 번호
- **current_character_id**: 현재 행동할 캐릭터의 ID
```
""" 