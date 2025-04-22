from sqlalchemy.orm import Session
from uuid import UUID

from app.db.characters import Character, CharacterStats
from app.models.characters import CharacterCreateRequest

def create_character(data:CharacterCreateRequest, db: Session) -> Character:
    character = Character(
        user_id=data.user_id,
        character_name=data.character_name,
        job=data.job,
        gender=data.gender
    )
    
    db.add(character)
    # character_id 확보
    db.flush()

    # 직업별 기본 스탯 세팅
    base_stats = {
        "warrior": dict(hp=120, attack=20, defense=15, resistance=10, critical_rate=0.05, critical_damage=1.5, move_range=4, speed=8, points=0),
        "archer": dict(hp=90, attack=25, defense=8, resistance=5, critical_rate=0.10, critical_damage=2.0, move_range=6, speed=12, points=0),
    }

    stats = CharacterStats(
        character_id=character.character_id,
        **base_stats[data.job.value]
    )
    
    db.add(stats)
    db.commit()
    db.refresh(character)


