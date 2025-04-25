from sqlalchemy.orm import Session
from uuid import UUID

from app.db.characters import Character, CharacterStats
from app.db.users import Users
from app.models.characters import CharacterCreateRequest, CharacterUpdateRequest, CharacterStatsUpdateRequest, CharacterInfoRequest

def get_character(request: CharacterInfoRequest, db: Session) -> Character:
    character = db.query(Character).filter_by(user_id=request.user_id).order_by(Character.created_time.desc()).first()
    return character

def create_character(request: CharacterCreateRequest, db: Session) -> Character:
    # 사용자 존재 여부 체크
    user = db.query(Users).filter(Users.user_id == request.user_id).first()
    if not user:
        raise ValueError("등록되지 않은 사용자입니다.")
    
    # 캐릭터 이름 중복 체크
    character_name = db.query(Character).filter_by(character_name=request.character_name).first()
    if character_name:
        raise ValueError("이미 존재하는 캐릭터 이름입니다.")

    character = Character(
        user_id=request.user_id,
        character_name=request.character_name,
        job=request.job,
        gender=request.gender,
        traits=request.traits
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
        **base_stats[request.job.value]
    )
    
    db.add(stats)
    db.commit()
    db.refresh(character)
    
    return character

def update_character(request: CharacterUpdateRequest, db: Session) -> Character:
    character = db.query(Character).filter(Character.character_id == request.character_id).first()
    if not character:
        raise ValueError("캐릭터가 존재하지 않습니다.")
    
    update_fields = request.dict(exclude_unset=True, exclude={"character_id"})

    for field, value in update_fields.items():
        setattr(character, field, value)

    db.commit()
    db.refresh(character)

def update_character_stats(request: CharacterStatsUpdateRequest, db: Session):
    stats = db.query(CharacterStats).filter_by(character_id=request.character_id).first()

    if not stats:
        raise ValueError("해당 캐릭터의 스탯 정보가 없습니다.")

    update_fields = request.dict(exclude_unset=True, exclude={"character_id"})

    for field, value in update_fields.items():
        setattr(stats, field, value)

    db.commit()
    db.refresh(stats)
