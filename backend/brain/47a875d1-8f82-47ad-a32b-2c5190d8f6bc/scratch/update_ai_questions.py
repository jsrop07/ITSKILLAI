import sys

path = r'c:\itskillAI\backend\routers\ai_questions.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Update first occurrence (General)
found_first = False
for i in range(len(lines)):
    if 'save_generated_questions(' in lines[i] and i > 150:
        # Search for closing parenthesis
        for j in range(i, i + 15):
            if ')' in lines[j] and 'ai_generation_type' not in ''.join(lines[i:j+1]):
                lines[j-1] = lines[j-1].rstrip() + '\n'
                lines.insert(j, '            ai_generation_type="general",\n')
                found_first = True
                break
        if found_first:
            break

# Update second occurrence (RAG)
found_second = False
start_index = 0
if found_first:
    start_index = i + 20

for i in range(start_index, len(lines)):
    if 'save_generated_questions(' in lines[i]:
        # Search for closing parenthesis
        for j in range(i, i + 15):
            if ')' in lines[j] and 'ai_generation_type' not in ''.join(lines[i:j+1]):
                lines[j-1] = lines[j-1].rstrip() + '\n'
                lines.insert(j, '            ai_generation_type="rag",\n')
                found_second = True
                break
        if found_second:
            break

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"Updated General: {found_first}, Updated RAG: {found_second}")
