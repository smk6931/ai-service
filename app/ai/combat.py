from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from app.models.combat import BattleActionResponse, BattleStateForAI
from app.utils.loader import skills

from dotenv import load_dotenv
# 환경 변수 로드
load_dotenv()


# LangChain 구성
class CombatAI:
    def __init__(self, model_name="gpt-4.1-nano", temperature=0.5):
        self.parser = PydanticOutputParser(pydantic_object=BattleActionResponse)
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)
        self.prompt = PromptTemplate.from_template(
        """
        당신은 턴제 RPG 게임의 몬스터 AI입니다.
        아래의 전투 상황을 바탕으로, 몬스터가 이번 턴에 수행할 가장 적절한 행동들을 판단하고,
        JSON 형식으로 출력하세요.
        
        전투 규칙:
        1. 한 턴에 스킬을 여러 번 사용할 수 있습니다.
        2. 하나의 스킬은 한 턴에 여러 번 사용할 수 없습니다.
        3. 스킬은 AP를 소모하며, 스킬 사용에 필요한 AP가 부족하면 스킬을 사용할 수 없습니다.
        4. AP는 턴이 시작할 때 1씩 회복되며, 남은 AP는 다음 턴에 사용할 수 있습니다.
        5. 몬스터는 플레이어를 쓰러뜨리는 것을 목표로 행동합니다.

        전투 상황:
        {battle_state}

        출력 시 반드시 대상 캐릭터는 이름이 아닌 ID를 사용하세요.
        출력 형식:
        {format}
        """
        ).partial(format=self.parser.get_format_instructions())
        
        self.chain = self.prompt | self.llm | self.parser

    # 타겟 몬스터의 스킬 정보 추출
    def get_target_monster_skills_info(self, state: BattleStateForAI) -> str:
        """타겟 몬스터가 가진 스킬들의 정보를 추출하여 반환합니다"""
        # 타겟 몬스터 찾기
        target = next((m for m in state.characters if m.id == state.target_monster_id), None)
        if not target or not target.skills:
            return "타겟 몬스터의 스킬 정보가 없습니다."
        
        # 타겟 몬스터의 스킬 정보 생성
        skill_info = []
        skill_info.append(f"## ({target.name})의 스킬 정보:")
        
        for skill_name in target.skills:
            if skill_name in skills:
                skill_data = skills[skill_name]
                
                info = f"- {skill_name}:\n"
                info += f"  설명: {skill_data.get('description', '정보 없음')}\n"
                info += f"  AP 소모: {skill_data.get('ap', '정보 없음')}\n"
                info += f"  사거리: {skill_data.get('range', '정보 없음')}\n"
                info += f"  피해량: {skill_data.get('damage', '정보 없음')}\n"
                
                if skill_data.get('effects'):
                    info += f"  효과: {', '.join(skill_data.get('effects'))}\n"
                
                skill_info.append(info)
        
        return "\n".join(skill_info)

    # 프롬프트 텍스트 생성 함수
    def convert_state_to_prompt_text(self, state: BattleStateForAI) -> str:
        chars = state.characters
        monsters = [c for c in chars if c.type == "monster"]
        players = [c for c in chars if c.type == "player"]

        def char_desc(c):
            base = f"- [{c.id}] {c.name} (HP: {c.hp}, AP: {c.ap}, 위치: {c.position})"
            if c.status_effects:
                base += f", 상태이상: {', '.join(c.status_effects)}"
            if c.skills:
                base += f", 스킬: {', '.join(c.skills)}"
            if c.personality:
                base += f", 성격: {c.personality}"
            return base

        monster_text = "\n".join([char_desc(m) for m in monsters])
        player_text = "\n".join([char_desc(p) for p in players])

        target = next((m for m in monsters if m.id == state.target_monster_id), None)
        if not target:
            raise ValueError("해당 ID의 몬스터가 존재하지 않습니다")
        
        # 타겟 몬스터의 스킬 정보 가져오기
        target_skills_info = self.get_target_monster_skills_info(state)
        
        state_text = f"""
주기: {state.cycle}
턴: {state.turn}
지형: {state.terrain}
날씨: {state.weather}

몬스터 목록:
{monster_text}

플레이어 목록:
{player_text}

행동 대상 몬스터: [{target.id}] {target.name}

{target_skills_info}
"""
        print(state_text)
        return state_text

    async def get_monster_action(self, battle_state: BattleStateForAI) -> BattleActionResponse:
        """몬스터의 다음 행동을 AI로 결정합니다"""
        prompt_text = self.convert_state_to_prompt_text(battle_state)
        result = await self.chain.ainvoke({"battle_state": prompt_text})
        return result
    