from ai.services.question_generator import generate_questions

questions = generate_questions(
    topic="Java 기초",
    difficulty="초급",
    count=3,
    score=1
)

for q in questions:
    print(q)