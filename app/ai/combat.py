from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from app.models.combat import BattleActionResponse, BattleStateForAI, CharacterAction
from app.utils.loader import skills, traits, status_effects, prompt_combat_rules, prompt_battle_state_template
from app.utils.combat import calculate_manhattan_distance, calculate_action_costs

from dotenv import load_dotenv
# 환경 변수 로드
load_dotenv()


# LangChain 구성
class CombatAI:
    def __init__(
        self, 
        # model_name="gpt-4.1-nano", 
        model_name="gpt-4o-mini", 
        temperature=0.5
    ):
        self.parser = PydanticOutputParser(pydantic_object=BattleActionResponse)
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)
        self.prompt = PromptTemplate.from_template(prompt_combat_rules).partial(format=self.parser.get_format_instructions())
        
        self.chain = self.prompt | self.llm | self.parser

    # 현재 캐릭터와 각 캐릭터 사이의 거리 계산
    def calculate_distances_from_target(self, state: BattleStateForAI):
        """현재 캐릭터와 각 캐릭터 사이의 거리를 계산하여 설정합니다"""
        # 현재 캐릭터 찾기
        current = next((c for c in state.characters if c.id == state.current_character_id), None)
        if not current:
            print("현재 캐릭터를 찾을 수 없습니다.")
            return
        
        target_position = current.position
        
        # 각 캐릭터의 거리 계산
        for character in state.characters:
            character.distance = calculate_manhattan_distance(
                target_position, character.position
            )
            
        # 거리 정보를 포함하는 설명 추가
        print(f"현재 캐릭터와의 거리 계산 완료: {[(c.id, c.distance) for c in state.characters]}")

    # 현재 캐릭터의 스킬 정보 추출
    def get_current_character_skills_info(self, state: BattleStateForAI) -> str:
        """현재 캐릭터가 가진 스킬들의 정보를 추출하여 반환합니다"""
        # 현재 캐릭터 찾기
        current = next((c for c in state.characters if c.id == state.current_character_id), None)
        if not current or not current.skills:
            return "현재 캐릭터의 스킬 정보가 없습니다."
        
        # 현재 캐릭터의 스킬 정보 생성
        skill_info = []
        # skill_info.append(f"## ({target.name})의 스킬 정보:")
        
        for skill_name in current.skills:
            if skill_name in skills:
                skill_data = skills[skill_name]
                
                info = f"- {skill_name}:\n"
                info += f"  설명: {skill_data.get('description', '정보 없음')}\n"
                info += f"  AP 소모: {skill_data.get('ap', '정보 없음')}\n"
                info += f"  사거리: {skill_data.get('range', '정보 없음')}\n"
                
                # dmg_mult 필드로 변경
                dmg_mult = skill_data.get('dmg_mult', 0)
                damage_text = f"{dmg_mult} x ATK" if dmg_mult > 0 else "없음"
                info += f"  피해량: {damage_text}\n"
                
                if skill_data.get('effects'):
                    info += f"  상태 효과: {', '.join(skill_data.get('effects'))}\n"
                
                skill_info.append(info)
        
        return "\n".join(skill_info)

    
    # 현재 캐릭터의 스킬 효과 정보 추출
    def get_current_character_status_effects_info(self, state: BattleStateForAI) -> str:
        """현재 캐릭터의 스킬이 가진 효과들의 상세 정보를 추출하여 반환합니다"""
        # 현재 캐릭터 찾기
        current = next((c for c in state.characters if c.id == state.current_character_id), None)
        if not current or not current.skills:
            return "스킬 효과 정보가 없습니다."
        
        # 모든 스킬의 효과들을 수집
        all_effects = set()
        for skill_name in current.skills:
            if skill_name in skills:
                skill_data = skills[skill_name]
                if 'effects' in skill_data and skill_data['effects']:
                    for effect in skill_data['effects']:
                        all_effects.add(effect)
        
        if not all_effects:
            return "스킬 효과 정보가 없습니다."
        
        # 효과들의 상세 정보 생성
        effect_info = []
        for effect_name in sorted(all_effects):
            if effect_name in status_effects:
                effect_data = status_effects[effect_name]
                
                info = f"- {effect_name}: {effect_data.get('description', '정보 없음')}"
                
                
                effect_info.append(info)
        
        return "\n".join(effect_info)
    
    # 현재 캐릭터의 특성 정보 추출
    def get_current_character_traits_info(self, state: BattleStateForAI) -> str:
        """현재 캐릭터의 특성 정보를 추출하여 반환합니다"""
        # 현재 캐릭터 찾기
        current = next((c for c in state.characters if c.id == state.current_character_id), None)
        # print("CURRENT: ", current)
        # print("CURRENT TRAITS: ", current.traits)
        if not current or not current.traits:
            return "현재 캐릭터의 특성 정보가 없습니다."
        
        trait_info = []
        # trait_info.append("## 특성 정보:")
        
        for trait_name in current.traits:
            # print("TRAIT NAME: ", trait_name)
            if trait_name in traits:
                trait_data = traits[trait_name]
                
                info = f"- {trait_name}: {trait_data.get('description', '정보 없음')}"
                
                
                trait_info.append(info)
        
        return "\n".join(trait_info)

    # 거리 정보 추가 함수
    def get_distance_info(self, state: BattleStateForAI) -> str:
        """현재 캐릭터와 각 캐릭터 사이의 거리 정보를 문자열로 반환합니다"""
        current = next((c for c in state.characters if c.id == state.current_character_id), None)
        if not current:
            return "거리 정보를 계산할 수 없습니다."
        
        distance_info = []
        distance_info.append("## 거리 정보:")
        
        for character in state.characters:
            if character.id != state.current_character_id:
                distance_info.append(f"- [{character.id}] {character.name}: {character.distance} 칸")
        
        return "\n".join(distance_info)

    # 프롬프트 텍스트 생성 함수
    def convert_state_to_prompt_text(self, state: BattleStateForAI) -> str:
        # 먼저 현재 캐릭터와 각 캐릭터 사이의 거리 계산
        self.calculate_distances_from_target(state)
        
        characters = state.characters
        monsters = [c for c in characters if c.type == "monster"]
        players = [c for c in characters if c.type == "player"]

        def char_desc(c):
            base = f"- [{c.id}] {c.name} (HP: {c.hp}, AP: {c.ap}, MOV: {c.mov}, 위치: {c.position}, range: {c.distance})"
            
            if c.status_effects:
                base += f", 상태이상: {', '.join(c.status_effects)}"
            if c.skills:
                base += f", 스킬: {', '.join(c.skills)}"
            if c.traits:
                base += f", 특성: {', '.join(c.traits)}"
            return base

        monster_text = "\n".join([char_desc(m) for m in monsters])
        player_text = "\n".join([char_desc(p) for p in players])

        current = next((c for c in characters if c.id == state.current_character_id), None)
        if not current:
            raise ValueError("해당 ID의 캐릭터가 존재하지 않습니다")
        
        # 현재 캐릭터의 스킬 정보 가져오기
        current_skills_info = self.get_current_character_skills_info(state)
        
        # 현재 캐릭터의 특성 정보 가져오기
        current_traits_info = self.get_current_character_traits_info(state)
        
        # 현재 캐릭터의 스킬 효과 정보 가져오기
        current_status_effects_info = self.get_current_character_status_effects_info(state)
        
        # # 거리 정보 추가
        # distance_info = self.get_distance_info(state)
        
        # 템플릿 사용하여 전투 상태 생성
        prompt_battle_state = prompt_battle_state_template.format(
            cycle=state.cycle,
            turn=state.turn,
            terrain=state.terrain,
            weather=state.weather,
            monster_text=monster_text,
            player_text=player_text,
            current_id=current.id,
            current_name=current.name,
            current_skills_info=current_skills_info,
            current_traits_info=current_traits_info,
            current_status_effects_info=current_status_effects_info
        )
        
        print(prompt_battle_state)
        return prompt_battle_state

    async def get_character_action(self, battle_state: BattleStateForAI) -> BattleActionResponse:
        """캐릭터의 다음 행동을 AI로 결정합니다"""
        prompt_text = self.convert_state_to_prompt_text(battle_state)
        result = await self.chain.ainvoke({"battle_state": prompt_text})
        
        # 현재 캐릭터 ID를 항상 요청에서 받은 ID로 설정
        result.current_character_id = battle_state.current_character_id
        
        # 리소스 계산 로직 개선
        current_character = next((c for c in battle_state.characters if c.id == battle_state.current_character_id), None)
        if current_character and result.actions:
            # 초기 리소스 값 설정
            current_ap = current_character.ap
            current_mov = current_character.mov
            current_position = current_character.position
            
            # 각 행동마다 순차적으로 리소스 계산
            for i, action in enumerate(result.actions):
                # 스킬 AP 소모량 가져오기
                skill_ap_cost = 0  # 기본값
                if action.skill in skills:
                    skill_ap_cost = skills[action.skill].get('ap', 0)
                
                # 이동 및 행동 비용 계산
                costs = calculate_action_costs(
                    current_position=current_position,
                    target_position=action.move_to,
                    current_ap=current_ap,
                    current_mov=current_mov,
                    skill_ap_cost=skill_ap_cost
                )
                
                # 남은 리소스 설정 및 다음 행동을 위한 상태 업데이트
                action.remaining_ap = costs['remaining_ap']
                action.remaining_mov = costs['remaining_mov']
                
                # 행동 가능 여부 확인
                if not costs['can_perform']:
                    # 리소스 부족으로 행동 불가능한 경우 이 행동과 이후 행동 삭제
                    result.actions = result.actions[:i]
                    break
                
                # 다음 행동을 위한 상태 업데이트
                current_ap = action.remaining_ap
                current_mov = action.remaining_mov
                current_position = action.move_to
        
        # 디버깅 로그
        print(f"결정된 행동: 캐릭터 ID={result.current_character_id}, 행동 수={len(result.actions)}")
        for i, action in enumerate(result.actions):
            print(f"  행동 {i+1}: 스킬={action.skill}, 대상={action.target_character_id}, 남은 AP={action.remaining_ap}, 남은 MOV={action.remaining_mov}")
        
        return result
