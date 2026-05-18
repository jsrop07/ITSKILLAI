import random
from collections import Counter
from ai.questions.explanation_repair import build_safe_multiple_choice_explanation
def get_target_answer_positions(count: int) -> list[int]:
    """
    객관식 정답 위치를 랜덤으로 배치하되,
    1,2번에만 몰리거나 특정 번호에 과도하게 몰리는 것을 방지한다.
    예:
    - count=3: [1, 4, 2], [3, 3, 5], [2, 5, 4] 가능
    - count=5: [1, 2, 5, 3, 4], [3, 3, 4, 5, 2] 가능
    """
    if count <= 0:
        return []
    if count == 1:
        return [random.randint(1, 5)]
    def is_valid_positions(positions: list[int]) -> bool:
        counter = Counter(positions)
        unique_count = len(counter)
        max_repeat = max(counter.values())
        # 1,2번에만 몰리는 패턴 방지
        if set(positions).issubset({1, 2}):
            return False
        # 전부 같은 번호 방지
        if unique_count == 1:
            return False
        if count == 2:
            return unique_count == 2
        if count == 3:
            # 예: [3,3,4] 허용, [1,1,1] 금지, [1,2,1] 금지
            return unique_count >= 2 and max_repeat <= 2
        if count == 4:
            # 최소 3개 번호는 섞이게 함
            return unique_count >= 3 and max_repeat <= 2
        if count == 5:
            # 예: [3,3,4,5,2] 허용, [1,1,1,2,2] 방지
            return unique_count >= 4 and max_repeat <= 2
        # 6개 이상 생성 시에도 특정 번호 과반 쏠림 방지
        return unique_count >= 4 and max_repeat <= max(2, (count // 2))
    for _ in range(100):
        positions = [random.randint(1, 5) for _ in range(count)]
        if is_valid_positions(positions):
            return positions
    # 혹시 100번 안에 적절한 패턴을 못 찾으면 안전하게 셔플 기반으로 생성
    fallback = []
    while len(fallback) < count:
        bag = [1, 2, 3, 4, 5]
        random.shuffle(bag)
        fallback.extend(bag)
    return fallback[:count]

def rebalance_answer_positions(questions: list[dict], question_type: str) -> list[dict]:
    """
    객관식 문제의 정답 위치가 1,2번에 몰리지 않도록 choices 순서를 코드에서 재배치한다.
    - 정답 텍스트는 유지한다.
    - choices 배열 순서만 바꾼다.
    - answer 번호와 explanation의 정답 번호를 함께 수정한다.
    """
    if question_type != "multiple_choice":
        return questions
    if not questions:
        return questions
    target_positions = get_target_answer_positions(len(questions))
    rebalanced = []
    for idx, q in enumerate(questions):
        choices = q.get("choices", [])
        answer = q.get("answer")
        if not isinstance(choices, list) or len(choices) != 5:
            rebalanced.append(q)
            continue
        try:
            current_answer = int(answer)
        except Exception:
            rebalanced.append(q)
            continue
        if current_answer < 1 or current_answer > 5:
            rebalanced.append(q)
            continue
        correct_choice = choices[current_answer - 1]
        wrong_choices = [
            choice for i, choice in enumerate(choices)
            if i != current_answer - 1
        ]
        target_answer = target_positions[idx % len(target_positions)]
        # 오답 순서는 매번 조금씩 섞어서 보기 패턴이 고정되지 않게 한다.
        random.shuffle(wrong_choices)
        new_choices = []
        wrong_index = 0
        for position in range(1, 6):
            if position == target_answer:
                new_choices.append(correct_choice)
            else:
                new_choices.append(wrong_choices[wrong_index])
                wrong_index += 1
        q["choices"] = new_choices
        q["answer"] = target_answer
        # choices 재배치 후 기존 explanation의 오답 번호 설명은 깨질 수 있으므로
        # 번호 기반 오답 설명을 제거하고 안전한 해설로 정리한다.
        q["explanation"] = build_safe_multiple_choice_explanation(q, target_answer)
        rebalanced.append(q)
    return rebalanced

def has_answer_position_bias(questions: list, question_type: str) -> bool:
    if question_type != "multiple_choice":
        return False
    if len(questions) < 3:
        return False
    try:
        answers = [int(q.get("answer")) for q in questions]
    except Exception:
        return False
    counter = Counter(answers)
    unique_count = len(counter)
    max_repeat = max(counter.values())
    # 전부 같은 번호면 편향
    if unique_count == 1:
        return True
    # 정답이 1,2번에만 몰리면 편향
    if set(answers).issubset({1, 2}):
        return True
    # 3문제는 [3,3,4] 같은 중복은 허용하되, 전부 같거나 1/2에만 몰리는 것은 위에서 차단
    if len(answers) == 3:
        return False
    # 4문제는 최소 3개 이상의 번호가 섞이게 함
    if len(answers) == 4:
        return unique_count < 3 or max_repeat > 2
    # 5문제는 최소 4개 이상의 번호가 섞이게 함
    if len(answers) == 5:
        return unique_count < 4 or max_repeat > 2
    # 6문제 이상은 특정 번호가 60% 이상이면 편향
    if max_repeat / len(answers) >= 0.6:
        return True
    return False