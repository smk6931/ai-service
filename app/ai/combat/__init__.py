from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import logging

from app.models.combat import BattleActionResponse, BattleStateForAI, CharacterAction
from app.utils.loader import skills, traits, status_effects, prompt_combat_rules, prompt_battle_state_template
from app.utils.combat import calculate_manhattan_distance, calculate_action_costs
from app.ai.combat.graph import create_combat_graph
from app.ai.combat.states import CombatState

from dotenv import load_dotenv
# 환경 변수 로드
load_dotenv()

# 로거 설정
logger = logging.getLogger("combat_ai")


# LangGraph 활용 전투 AI 구성
class CombatAI:
    """전투 AI 클래스
    
    LangGraph를 사용하여 전투 행동을 결정하고, 실패 시 기존 체인을 폴백으로 사용합니다.
    """
    
    def __init__(
        self, 
        model_name="gpt-4o-mini", 
        temperature=0.5
    ):
        """CombatAI 인스턴스를 초기화합니다.
        
        Args:
            model_name: 사용할 LLM 모델명
            temperature: LLM 온도 설정 (높을수록 다양한 응답 생성)
        """
        # LangGraph 그래프 생성
        self.combat_graph = create_combat_graph()
        
        # 폴백을 위한 기존 체인 설정
        self.parser = PydanticOutputParser(pydantic_object=BattleActionResponse)
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)
        self.prompt = PromptTemplate.from_template(prompt_combat_rules).partial(
            format=self.parser.get_format_instructions()
        )
        self.chain = self.prompt | self.llm | self.parser
        
        # 모델 설정
        self.model_name = model_name
        self.temperature = temperature

    def calculate_distances_from_target(self, state: BattleStateForAI) -> None:
        """현재 캐릭터와 각 캐릭터 사이의 거리를 계산하여 설정합니다.
        
        Args:
            state: 전투 상태 객체
        """
        current = next((c for c in state.characters if c.id == state.current_character_id), None)
        if not current:
            logger.warning("현재 캐릭터를 찾을 수 없습니다.")
            return
        
        target_position = current.position
        
        # 각 캐릭터의 거리 계산
        for character in state.characters:
            character.distance = calculate_manhattan_distance(
                target_position, character.position
            )
            
        logger.debug(f"현재 캐릭터와의 거리 계산 완료: {[(c.id, c.distance) for c in state.characters]}")

    def get_current_character_skills_info(self, state: BattleStateForAI) -> str:
        """현재 캐릭터가 가진 스킬들의 정보를 추출하여 반환합니다.
        
        Args:
            state: 전투 상태 객체
            
        Returns:
            스킬 정보 텍스트
        """
        current = next((c for c in state.characters if c.id == state.current_character_id), None)
        if not current or not current.skills:
            return "현재 캐릭터의 스킬 정보가 없습니다."
        
        skill_info = []
        
        for skill_name in current.skills:
            if skill_name in skills:
                skill_data = skills[skill_name]
                
                info_parts = [
                    f"- {skill_name}:",
                    f"  설명: {skill_data.get('description', '정보 없음')}",
                    f"  AP 소모: {skill_data.get('ap', '정보 없음')}",
                    f"  사거리: {skill_data.get('range', '정보 없음')}"
                ]
                
                # 피해량 정보 추가
                dmg_mult = skill_data.get('dmg_mult', 0)
                damage_text = f"{dmg_mult} x ATK" if dmg_mult > 0 else "없음"
                info_parts.append(f"  피해량: {damage_text}")
                
                # 상태 효과 추가
                if skill_data.get('effects'):
                    info_parts.append(f"  상태 효과: {', '.join(skill_data.get('effects'))}")
                
                skill_info.append("\n".join(info_parts))
        
        return "\n".join(skill_info)
        
    def get_current_character_status_effects_info(self, state: BattleStateForAI) -> str:
        """현재 캐릭터의 스킬이 가진 효과들의 상세 정보를 추출합니다.
        
        Args:
            state: 전투 상태 객체
            
        Returns:
            상태 효과 정보 텍스트
        """
        current = next((c for c in state.characters if c.id == state.current_character_id), None)
        if not current or not current.skills:
            return "스킬 효과 정보가 없습니다."
        
        # 모든 스킬의 효과 수집
        all_effects = set()
        for skill_name in current.skills:
            if skill_name in skills:
                skill_effects = skills[skill_name].get('effects', [])
                all_effects.update(skill_effects)
        
        if not all_effects:
            return "스킬 효과 정보가 없습니다."
        
        # 효과 상세 정보 생성
        effect_info = []
        for effect_name in sorted(all_effects):
            if effect_name in status_effects:
                effect_data = status_effects[effect_name]
                effect_info.append(
                    f"- {effect_name}: {effect_data.get('description', '정보 없음')}"
                )
        
        return "\n".join(effect_info)
    
    def get_current_character_traits_info(self, state: BattleStateForAI) -> str:
        """현재 캐릭터의 특성 정보를 추출합니다.
        
        Args:
            state: 전투 상태 객체
            
        Returns:
            특성 정보 텍스트
        """
        current = next((c for c in state.characters if c.id == state.current_character_id), None)
        if not current or not current.traits:
            return "현재 캐릭터의 특성 정보가 없습니다."
        
        trait_info = []
        for trait_name in current.traits:
            if trait_name in traits:
                trait_data = traits[trait_name]
                trait_info.append(
                    f"- {trait_name}: {trait_data.get('description', '정보 없음')}"
                )
        
        return "\n".join(trait_info)

    def convert_state_to_prompt_text(self, state: BattleStateForAI) -> str:
        """전투 상태를 프롬프트 텍스트로 변환합니다 (폴백용).
        
        Args:
            state: 전투 상태 객체
            
        Returns:
            프롬프트 텍스트
        """
        # 거리 계산
        self.calculate_distances_from_target(state)
        
        # 캐릭터 분류
        characters = state.characters
        monsters = [c for c in characters if c.type == "monster"]
        players = [c for c in characters if c.type == "player"]

        def char_desc(c):
            """캐릭터 설명 생성"""
            parts = [
                f"- [{c.id}] {c.name} (HP: {c.hp}, AP: {c.ap}, MOV: {c.mov}, "
                f"위치: {c.position}, range: {c.distance})"
            ]
            
            if c.status_effects:
                parts.append(f"상태이상: {', '.join(c.status_effects)}")
            if c.skills:
                parts.append(f"스킬: {', '.join(c.skills)}")
            if c.traits:
                parts.append(f"특성: {', '.join(c.traits)}")
            
            return ", ".join(parts)

        monster_text = "\n".join([char_desc(m) for m in monsters])
        player_text = "\n".join([char_desc(p) for p in players])

        current = next((c for c in characters if c.id == state.current_character_id), None)
        if not current:
            raise ValueError("해당 ID의 캐릭터가 존재하지 않습니다")
        
        # 각종 정보 가져오기
        current_skills_info = self.get_current_character_skills_info(state)
        current_traits_info = self.get_current_character_traits_info(state)
        current_status_effects_info = self.get_current_character_status_effects_info(state)
        
        # 전투 상황 분석 정보 생성 (폴백용 레거시 코드 활용)
        from app.ai.combat_backup import CombatAI as LegacyCombatAI
        legacy_ai = LegacyCombatAI()
        battle_analysis = legacy_ai.generate_battle_analysis(state)
        
        # 템플릿 적용
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
            battle_analysis=battle_analysis
        )
        
        logger.debug("전투 상태 프롬프트 생성 완료")
        return prompt_battle_state

    async def get_character_action(self, battle_state: BattleStateForAI) -> BattleActionResponse:
        """캐릭터의 다음 행동을 결정합니다.
        
        Args:
            battle_state: 전투 상태 객체
            
        Returns:
            결정된 행동 응답
        """
        try:
            logger.info("LangGraph 기반 전투 결정 시작")
            
            # 거리 계산 적용
            self.calculate_distances_from_target(battle_state)
            
            # 초기 상태 설정
            combat_state = CombatState(
                battle_state=battle_state,
                situation_analysis={},
                strategy_decision={},
                target_selection={},
                planned_actions=[],
                resource_calculation={},
                final_actions=[],
                messages=[],
                response=None
            )
            
            # 그래프 실행
            try:
                result = await self.combat_graph.ainvoke(combat_state)
                
                # 응답 확인
                if result.get("response"):
                    logger.info("LangGraph 결정 완료")
                    response = result["response"]
                    
                    # 현재 캐릭터 ID 확인
                    response.current_character_id = battle_state.current_character_id
                    
                    # 디버깅 로그
                    actions_info = ", ".join([
                        f"{a.skill}->{a.target_character_id}@{a.move_to}" 
                        for a in response.actions
                    ])
                    logger.debug(f"결정된 행동: {actions_info}")
                    
                    return response
                else:
                    raise ValueError("LangGraph 응답이 없습니다")
            except Exception as e:
                logger.error(f"LangGraph 판단 실패, 기존 체인으로 폴백: {str(e)}")
                return await self._fallback_chain_decision(battle_state)
                
        except Exception as e:
            logger.error(f"전투 결정 중 에러 발생: {str(e)}")
            return await self._fallback_chain_decision(battle_state)

    async def _fallback_chain_decision(self, battle_state: BattleStateForAI) -> BattleActionResponse:
        """폴백용 기존 체인 방식으로 결정을 수행합니다."""
        logger.info("폴백: 기존 체인 방식으로 전투 결정")
        
        try:
            prompt_text = self.convert_state_to_prompt_text(battle_state)
            response = await self.chain.ainvoke({"state_text": prompt_text})
            
            # 현재 캐릭터 ID 확인
            response.current_character_id = battle_state.current_character_id
            
            # 행동 비용 계산 및 유효성 검증
            for action in response.actions:
                remaining_resources = calculate_action_costs(
                    action=action,
                    skill_name=action.skill,
                    current_ap=action.remaining_ap,
                    current_mov=action.remaining_mov
                )
                
                action.remaining_ap = remaining_resources["remaining_ap"]
                action.remaining_mov = remaining_resources["remaining_mov"]
            
            return response
            
        except Exception as e:
            logger.error(f"폴백 체인 결정 중 에러: {str(e)}")
            
            # 최종 폴백: 비어있는 응답 반환
            return BattleActionResponse(
                current_character_id=battle_state.current_character_id,
                actions=[]
            )
