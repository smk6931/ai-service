# 전투 시스템 노드 모듈 
from typing import Dict, Any, Optional, List, Union
import json

# 길이 제한 상수
MAX_STRING_LENGTH = 2000
MAX_LIST_PREVIEW_LENGTH = 10
MAX_MESSAGE_PREVIEW_LENGTH = 3
MAX_DICT_LIST_LENGTH = 5
MAX_CONTENT_PREVIEW_LENGTH = 500

def debug_node(
    node_name: str,
    input_data: Optional[Dict[str, Any]] = None, 
    output_data: Optional[Dict[str, Any]] = None, 
    error: bool = False
) -> None:
    """노드 실행 디버깅 정보를 출력합니다.
    
    Args:
        node_name: 노드 이름
        input_data: 입력 데이터
        output_data: 출력 데이터
        error: 에러 발생 여부
    """
    # 에러 여부와 관계없이 항상 출력
    border = "=" * 50
    print(f"\n{border}")
    
    if error:
        print(f"[에러] 노드: {node_name}")
    else:
        print(f"[실행] 노드: {node_name}")
    
    if input_data:
        print(f"\n입력 데이터:")
        print_simple_summary(input_data)
    
    if output_data:
        print(f"\n출력 데이터:")
        print_simple_summary(output_data)
    
    print(f"{border}\n")


def truncate_with_ellipsis(text: str, max_length: int, suffix: str = "...(생략)") -> str:
    """문자열을 지정된 길이로 자르고 접미사를 추가합니다.
    
    Args:
        text: 원본 문자열
        max_length: 최대 길이
        suffix: 접미사
        
    Returns:
        잘린 문자열
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + suffix


def process_dict_for_output(data: Dict[str, Any]) -> Dict[str, Any]:
    """딕셔너리를 출력용으로 처리합니다.
    
    Args:
        data: 처리할 딕셔너리
    
    Returns:
        처리된 딕셔너리
    """
    result = {}
    
    for key, value in data.items():
        if key == "battle_state":
            result[key] = "(생략)"
        elif key == "messages":
            # 메시지 내용 일부 출력
            messages_preview = []
            for i, msg in enumerate(value[:MAX_MESSAGE_PREVIEW_LENGTH]):
                if hasattr(msg, 'content'):
                    # langchain 메시지 객체인 경우
                    content = msg.content
                    msg_type = msg.__class__.__name__
                    preview = f"{msg_type}: {truncate_with_ellipsis(content, MAX_CONTENT_PREVIEW_LENGTH, '...')}"
                    messages_preview.append(preview)
                elif isinstance(msg, dict) and 'content' in msg:
                    # 딕셔너리 형태의 메시지인 경우
                    content = msg['content']
                    msg_type = msg.get('type', 'Message')
                    preview = f"{msg_type}: {truncate_with_ellipsis(content, MAX_CONTENT_PREVIEW_LENGTH, '...')}"
                    messages_preview.append(preview)
                else:
                    # 그 외의 경우
                    messages_preview.append(truncate_with_ellipsis(str(msg), MAX_CONTENT_PREVIEW_LENGTH, '...'))
            
            if len(value) > MAX_MESSAGE_PREVIEW_LENGTH:
                messages_preview.append(f"... 외 {len(value) - MAX_MESSAGE_PREVIEW_LENGTH}개 메시지")
                
            result[key] = messages_preview
        elif isinstance(value, list) and len(value) > MAX_DICT_LIST_LENGTH:
            # 리스트가 지정된 개수 이상의 항목을 가지면 일부만 표시
            result[key] = value[:MAX_DICT_LIST_LENGTH] + [f"... 외 {len(value) - MAX_DICT_LIST_LENGTH}개 항목"]
        elif isinstance(value, dict):
            # 내부 딕셔너리도 재귀적으로 처리
            result[key] = process_dict_for_output(value)
        else:
            result[key] = value
            
    return result


def format_json_output(data: Any) -> str:
    """데이터를 JSON 문자열로 변환합니다.
    
    Args:
        data: 변환할 데이터
        
    Returns:
        JSON 문자열 또는 에러 메시지
    """
    try:
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        return truncate_with_ellipsis(json_str, MAX_STRING_LENGTH)
    except Exception as e:
        return f"JSON 변환 오류: {e}\n{truncate_with_ellipsis(str(data), 500)}"


def print_simple_summary(data: Union[Dict[str, Any], List, Any]) -> None:
    """데이터를 JSON 형식으로 출력합니다.
    
    Args:
        data: 출력할 데이터
    """
    if isinstance(data, dict):
        # 딕셔너리 전처리
        data_copy = process_dict_for_output(data)
        print(format_json_output(data_copy))
    elif isinstance(data, list):
        # 리스트가 너무 길면 앞부분만 출력
        if len(data) > MAX_LIST_PREVIEW_LENGTH:
            preview_data = data[:MAX_LIST_PREVIEW_LENGTH]
            print(format_json_output(preview_data))
            print(f"... 외 {len(data) - MAX_LIST_PREVIEW_LENGTH}개 항목")
        else:
            print(format_json_output(data))
    else:
        # 기본 타입은 그대로 출력
        print(str(data)) 
        