# 전투 시스템 노드 모듈 
import json
from typing import Dict, Any, Optional
import pprint

def debug_node(node_name: str, input_data: Optional[Dict[str, Any]] = None, output_data: Optional[Dict[str, Any]] = None, error: bool = False):
    """노드 입력/출력 데이터를 이쁘게 출력하는 디버깅 유틸리티
    
    Args:
        node_name: 노드 이름
        input_data: 입력 데이터 (없으면 출력 안함)
        output_data: 출력 데이터 (없으면 출력 안함)
        error: 에러 발생 여부 (True면 항상 출력)
    """
    # 마지막 노드인 경우 또는 에러가 있는 경우에만 출력
    if not (error or "응답 생성" in node_name):
        return
        
    print(f"\n{'=' * 50}")
    if error:
        print(f"[에러] 노드: {node_name}")
    else:
        print(f"노드: {node_name}")
    
    # 에러 발생 시 또는 마지막 노드인 경우에는 항상 입력 데이터 출력
    if input_data:
        print(f"\n입력 데이터:")
        # 핵심 정보만 선택적으로 표시
        filtered_input = {}
        
        # 상태 데이터는 너무 크므로 간소화
        if "battle_state" in input_data:
            filtered_input["battle_state"] = "(생략)"
        
        # 다른 필드들은 핵심만 추출
        for key, value in input_data.items():
            if key != "battle_state" and key != "messages":
                filtered_input[key] = value
                
        pprint.pprint(filtered_input, width=100, compact=True)
    
    if output_data:
        print(f"\n출력 데이터:")
        # 출력 데이터 간소화
        filtered_output = {}
        
        # 메시지는 마지막 메시지만 표시
        if "messages" in output_data and output_data["messages"]:
            last_message = output_data["messages"][-1]
            filtered_output["messages"] = f"마지막 메시지: {last_message.content[:100]}..." if len(last_message.content) > 100 else last_message.content
        
        # 다른 필드들 처리
        for key, value in output_data.items():
            if key != "messages":
                # 복잡한 구조는 요약 정보만 표시
                if isinstance(value, dict) and len(str(value)) > 500:
                    filtered_output[key] = f"(객체: {len(value)} 항목)"
                elif isinstance(value, list) and len(value) > 0:
                    filtered_output[key] = f"({len(value)}개 항목)"
                    # 행동 계획인 경우 요약 표시
                    if key == "planned_actions" or key == "final_actions":
                        filtered_output[f"{key}_summary"] = [
                            f"{a.skill} -> {a.target_character_id} (위치: {a.move_to})" 
                            for a in value
                        ]
                else:
                    filtered_output[key] = value
                    
        pprint.pprint(filtered_output, width=100, compact=True)
    
    print(f"{'=' * 50}\n") 