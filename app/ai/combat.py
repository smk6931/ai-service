from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from app.models.combat import BattleActionResponse, BattleStateForAI
from app.utils.loader import skills, prompt_combat_rules, prompt_combat_state_template

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
                
                # dmg_mult 필드로 변경
                dmg_mult = skill_data.get('dmg_mult', 0)
                damage_text = f"{dmg_mult}x ATK" if dmg_mult > 0 else "없음"
                info += f"  피해량: {damage_text}\n"
                
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
        
        # 템플릿 사용하여 전투 상태 생성
        prompt_combat_state = prompt_combat_state_template.format(
            cycle=state.cycle,
            turn=state.turn,
            terrain=state.terrain,
            weather=state.weather,
            monster_text=monster_text,
            player_text=player_text,
            target_id=target.id,
            target_name=target.name,
            target_skills_info=target_skills_info
        )
        
        print(prompt_combat_state)
        return prompt_combat_state

    async def get_monster_action(self, battle_state: BattleStateForAI) -> BattleActionResponse:
        """몬스터의 다음 행동을 AI로 결정합니다"""
        prompt_text = self.convert_state_to_prompt_text(battle_state)
        result = await self.chain.ainvoke({"battle_state": prompt_text})
        return result
