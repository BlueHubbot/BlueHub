import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('.Blue/specs/tasks.md', encoding='utf-8') as f:
    lines = f.readlines()

matches = [(i, l.rstrip()) for i, l in enumerate(lines) if 'TASK-027' in l or 'TASK-028' in l]
for i, l in matches:
    print(f"Line {i}: {l}")
