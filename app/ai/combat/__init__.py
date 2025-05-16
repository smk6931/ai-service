from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import logging

from app.models.combat import BattleActionResponse, BattleStateForAI, CharacterAction
from app.utils.combat import calculate_manhattan_distance
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
    
    LangGraph를 사용하여 전투 행동을 결정합니다.
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
            return
        
        target_position = current.position
        
        # 각 캐릭터의 거리 계산
        for character in state.characters:
            character.distance = calculate_manhattan_distance(
                target_position, character.position
            )

    async def get_character_action(self, battle_state: BattleStateForAI) -> BattleActionResponse:
        """캐릭터의 다음 행동을 결정합니다.
        
        Args:
            battle_state: 전투 상태 객체
            
        Returns:
            결정된 행동 응답
        """
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
        result = await self.combat_graph.ainvoke(combat_state)
        
        # 응답 확인
        if result.get("response"):
            response = result["response"]
            
            # 현재 캐릭터 ID 확인
            response.current_character_id = battle_state.current_character_id
            
            return response
        else:
            # 응답이 없는 경우 기본 응답 생성
            current = next((c for c in battle_state.characters if c.id == battle_state.current_character_id), None)
            default_action = CharacterAction(
                move_to=current.position if current else (0, 0),
                skill="대기",
                target_character_id=current.id if current else "",
                reason="응답 생성 실패",
                remaining_ap=current.ap if current else 0,
                remaining_mov=current.mov if current else 0
            )
            
            return BattleActionResponse(
                current_character_id=battle_state.current_character_id,
                action=default_action
            )
