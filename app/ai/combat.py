from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from app.models.combat import BattleActionResponse, BattleStateForAI, CharacterAction
from app.utils.loader import skills, traits, status_effects, prompt_combat_rules, prompt_battle_state_template
from app.utils.combat import calculate_manhattan_distance, calculate_action_costs

from typing import List, Dict, Tuple, Any, Set
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

    # 스킬 사거리 내 공격 가능한 대상 찾기
    def find_targets_in_range(self, state: BattleStateForAI) -> Dict[str, List[str]]:
        """현재 캐릭터의 각 스킬에 대해 사거리 내에 있는 대상 목록을 찾습니다"""
        current = next((c for c in state.characters if c.id == state.current_character_id), None)
        if not current or not current.skills:
            return {}
        
        # 현재 캐릭터의 위치
        current_position = current.position
        
        # 스킬별 사거리 내 대상 목록
        targets_in_range = {}
        
        # 현재 캐릭터와 다른 타입의 캐릭터를 대상으로 함
        target_characters = [c for c in state.characters if c.id != current.id]
        
        # 각 스킬에 대해 사거리 확인
        for skill_name in current.skills:
            targets_in_range[skill_name] = []
            
            # 스킬 정보 가져오기
            skill_range = 1  # 기본 사거리
            if skill_name in skills:
                skill_range = skills[skill_name].get('range', 1)
            
            # 각 캐릭터와의 거리 계산하여 사거리 내에 있는지 확인
            for character in target_characters:
                distance = calculate_manhattan_distance(current_position, character.position)
                if distance <= skill_range:
                    targets_in_range[skill_name].append(character.id)
        
        return targets_in_range

    # 이동 가능한 위치 계산
    def calculate_movable_positions(self, state: BattleStateForAI) -> List[Tuple[int, int]]:
        """현재 캐릭터의 MOV 값을 기준으로 이동 가능한 모든 위치를 계산합니다"""
        current = next((c for c in state.characters if c.id == state.current_character_id), None)
        if not current:
            return []
        
        # 현재 위치와 이동력
        x, y = current.position
        mov = current.mov
        
        # 이동 가능한 모든 위치 (맨해튼 거리 이내)
        movable_positions = []
        
        # 맨해튼 거리로 이동 가능한 범위 계산 (상하좌우 이동만 가능)
        for dx in range(-mov, mov + 1):
            remaining_mov = mov - abs(dx)
            for dy in range(-remaining_mov, remaining_mov + 1):
                if abs(dx) + abs(dy) <= mov:  # 맨해튼 거리 확인
                    new_pos = (x + dx, y + dy)
                    movable_positions.append(new_pos)
        
        return movable_positions

    # 이동 후 스킬 사용 가능성 분석
    def analyze_move_and_skill(self, state: BattleStateForAI) -> Dict[str, Any]:
        """각 스킬별로 이동 후 사용 가능한 대상과 위치를 분석합니다"""
        current = next((c for c in state.characters if c.id == state.current_character_id), None)
        if not current or not current.skills:
            return {}
        
        # 현재 위치 및 리소스
        current_position = current.position
        current_ap = current.ap
        current_mov = current.mov
        
        # 이동 가능한 위치들
        movable_positions = self.calculate_movable_positions(state)
        
        # 결과 저장용 딕셔너리
        analysis = {
            "직접_공격_가능": {},  # 현재 위치에서 바로 공격 가능한 대상
            "이동_후_공격_가능": {},  # 이동 후 공격 가능한 대상과 위치
            "최적_행동_추천": []  # 추천 행동 목록
        }
        
        # 타겟 캐릭터들 (다른 캐릭터)
        target_characters = [c for c in state.characters if c.id != current.id]
        
        # 각 스킬에 대해 분석
        for skill_name in current.skills:
            # 스킬 정보 가져오기
            skill_data = skills.get(skill_name, {})
            skill_range = skill_data.get('range', 1)
            skill_ap = skill_data.get('ap', 0)
            
            # AP가 부족하면 이 스킬은 사용 불가
            if skill_ap > current_ap:
                continue
            
            # 직접 공격 가능한 대상 찾기
            direct_targets = []
            for character in target_characters:
                distance = calculate_manhattan_distance(current_position, character.position)
                if distance <= skill_range:
                    direct_targets.append(character.id)
            
            if direct_targets:
                analysis["직접_공격_가능"][skill_name] = direct_targets
            
            # 이동 후 공격 가능한 대상 및 위치 찾기
            movable_attacks = {}
            for character in target_characters:
                # 이미 직접 공격 가능한 대상은 제외
                if character.id in direct_targets:
                    continue
                
                target_position = character.position
                best_move_positions = []
                
                # 각 이동 가능한 위치에서
                for move_pos in movable_positions:
                    # 이동 비용 계산
                    move_distance = calculate_manhattan_distance(current_position, move_pos)
                    
                    # 이동력이 충분한지 확인
                    if move_distance <= current_mov:
                        # 이동 후 타겟과의 거리 계산
                        distance_to_target = calculate_manhattan_distance(move_pos, target_position)
                        
                        # 스킬 사거리 내에 있는지 확인
                        if distance_to_target <= skill_range:
                            best_move_positions.append({
                                "position": move_pos,
                                "move_cost": move_distance,
                                "distance_to_target": distance_to_target
                            })
                
                # 최적의 이동 위치 정렬 (이동 비용이 적은 순, 대상과의 거리가 가까운 순)
                best_move_positions.sort(key=lambda x: (x["move_cost"], x["distance_to_target"]))
                
                if best_move_positions:
                    movable_attacks[character.id] = best_move_positions[:3]  # 상위 3개 위치만 저장
            
            if movable_attacks:
                analysis["이동_후_공격_가능"][skill_name] = movable_attacks
        
        # 최적 행동 추천
        # 1. 현재 위치에서 직접 공격 가능한 경우
        for skill_name, targets in analysis["직접_공격_가능"].items():
            for target_id in targets:
                analysis["최적_행동_추천"].append({
                    "description": f"현재 위치에서 {skill_name} 스킬로 {target_id} 공격",
                    "skill": skill_name,
                    "target_id": target_id,
                    "move_to": current_position,
                    "priority": 1  # 높은 우선순위
                })
        
        # 2. 이동 후 공격 가능한 경우
        for skill_name, targets in analysis["이동_후_공격_가능"].items():
            for target_id, positions in targets.items():
                if positions:  # 이동 가능한 위치가 있는 경우
                    best_pos = positions[0]  # 최적의 위치
                    analysis["최적_행동_추천"].append({
                        "description": f"{best_pos['position']}(으)로 이동 후 {skill_name} 스킬로 {target_id} 공격",
                        "skill": skill_name,
                        "target_id": target_id,
                        "move_to": best_pos["position"],
                        "priority": 2  # 중간 우선순위
                    })
        
        # 우선순위에 따라 정렬
        analysis["최적_행동_추천"].sort(key=lambda x: x["priority"])
        
        return analysis

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
        if not current or not current.traits:
            return "현재 캐릭터의 특성 정보가 없습니다."
        
        trait_info = []
        
        for trait_name in current.traits:
            if trait_name in traits:
                trait_data = traits[trait_name]
                
                info = f"- {trait_name}: {trait_data.get('description', '정보 없음')}"
                
                trait_info.append(info)
        
        return "\n".join(trait_info)

    # 전투 상황 분석 정보 생성
    def generate_battle_analysis(self, state: BattleStateForAI) -> str:
        """현재 전투 상황에 대한 상세 분석 정보를 생성합니다"""
        # 사거리 내 공격 가능한 대상 찾기
        targets_in_range = self.find_targets_in_range(state)
        
        # 이동 후 스킬 사용 가능성 분석
        move_skill_analysis = self.analyze_move_and_skill(state)
        
        # 분석 정보 생성
        analysis_text = ["## 전투 상황 분석"]
        
        # 1. 현재 위치에서 직접 공격 가능한 대상
        analysis_text.append("\n### 현재 위치에서 공격 가능한 대상")
        if targets_in_range:
            for skill_name, target_ids in targets_in_range.items():
                if target_ids:
                    skill_ap = skills.get(skill_name, {}).get('ap', 0)
                    analysis_text.append(f"- {skill_name}(AP: {skill_ap})로 공격 가능한 대상: {', '.join(target_ids)}")
                else:
                    analysis_text.append(f"- {skill_name}으로 공격 가능한 대상 없음")
        else:
            analysis_text.append("- 현재 위치에서 바로 공격 가능한 대상이 없습니다.")
        
        # 2. 최적 행동 추천
        analysis_text.append("\n### 추천 행동")
        if move_skill_analysis.get("최적_행동_추천"):
            for i, action in enumerate(move_skill_analysis["최적_행동_추천"][:3], 1):  # 상위 3개만
                analysis_text.append(f"{i}. {action['description']}")
        else:
            analysis_text.append("- 유효한 행동 추천이 없습니다.")
        
        # 3. 이동 후 공격 가능한 대상과 위치 (상세 정보)
        analysis_text.append("\n### 이동 후 공격 가능한 대상과 위치")
        if move_skill_analysis.get("이동_후_공격_가능"):
            for skill_name, targets in move_skill_analysis["이동_후_공격_가능"].items():
                skill_ap = skills.get(skill_name, {}).get('ap', 0)
                analysis_text.append(f"\n- {skill_name}(AP: {skill_ap}) 사용 시:")
                
                for target_id, positions in targets.items():
                    if positions:
                        best_pos = positions[0]  # 최적의 위치
                        analysis_text.append(f"  - {target_id}에게 사용하려면: {best_pos['position']}로 이동 (이동 비용: {best_pos['move_cost']} MOV)")
        else:
            analysis_text.append("- 이동해도 공격 가능한 대상이 없습니다.")
        
        return "\n".join(analysis_text)

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
        
        # 전투 상황 분석 정보 생성
        battle_analysis = self.generate_battle_analysis(state)
        
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
            current_status_effects_info=current_status_effects_info,
            battle_analysis=battle_analysis  # 새로운 분석 정보 추가
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
            print(f"  행동 {i+1}: 스킬={action.skill}, 대상={action.target_character_id}, 이동={action.move_to}, 남은 AP={action.remaining_ap}, 남은 MOV={action.remaining_mov}")
        
        return result
