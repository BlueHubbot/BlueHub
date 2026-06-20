import os
import re

# Try to find tasks.md
possible_paths = [
    'd:/BlueHub/.Blue/specs/tasks.md',
    'g:/BlueHub/.Blue/specs/tasks.md',
    '.Blue/specs/tasks.md',
]

tasks_path = None
for p in possible_paths:
    if os.path.exists(p):
        tasks_path = p
        break

if not tasks_path:
    print("ERROR: Could not find tasks.md")
    exit(1)

print(f"Reading: {tasks_path}")
content = open(tasks_path, encoding='utf-8').read()

# Split into task blocks - handle both formats:
# Format A: ### TASK-XXX: Title ...
# Format B: ### Some Title ... followed by **ID:** TASK-XXX
# We'll use the --- separator as block delimiters

# First, find all TASK-XXX entries and their positions
all_tasks = []  # List of (task_id, block_text, start_pos)

# Pattern for Format A: ### TASK-XXX: Title
for m in re.finditer(r'### TASK-(\d{3})', content):
    task_id = f'TASK-{m.group(1)}'
    start = m.start()
    # Find the end of this block (next "### " or "---" or end of file)
    end = content.find('\n### ', start + 1)
    if end == -1:
        end = len(content)
    block = content[start:end]
    all_tasks.append((task_id, block, start))

# Pattern for Format B: **ID:** TASK-XXX (tasks not already found)
for m in re.finditer(r'\*\*ID:\*\*\s*TASK-(\d{3})', content):
    task_id = f'TASK-{m.group(1)}'
    # Check if already captured
    if any(t[0] == task_id for t in all_tasks):
        continue
    # Find the start of this task's section (preceding ## heading or ### heading)
    # Go backwards to find the nearest ### heading
    pos = m.start()
    preceding = content.rfind('### ', 0, pos)
    if preceding == -1:
        preceding = 0
    # Find the end (next "---" or next ### heading after this one, or end)
    end = content.find('\n---', pos)
    if end == -1:
        # Try next ### heading
        end = content.find('\n### ', pos + 1)
    if end == -1:
        end = len(content)
    block = content[preceding:end]
    all_tasks.append((task_id, block, preceding))

# Sort by position in file
all_tasks.sort(key=lambda x: x[2])

# First, collect all completed tasks
completed = set()

def parse_status(block):
    """Extract status from a task block. Returns lowercase status word or None."""
    # Try **Status:** word or **Status:** emoji word
    m = re.search(r'\*\*Status:\*\*\s*(?:✅|⚠️|❌|🔴|🟡|🟢|⏳|🚧)?\s*(\w+)', block)
    if m:
        return m.group(1).lower()
    return None

def parse_deps(block):
    """Extract dependency list from a task block."""
    # Try **Dependencies:** or **Dependencies:** list
    m = re.search(r'\*\*Dependencies:\*\*\s*(.+)', block)
    if m:
        deps_raw = m.group(1).strip()
        return re.findall(r'TASK-\d{3}', deps_raw)
    return []

def parse_priority(block):
    """Extract priority from a task block."""
    m = re.search(r'\*\*Priority:\*\*\s*(\S+)', block)
    if m:
        return m.group(1)
    return 'unknown'

def parse_title(block):
    """Extract title from a task block."""
    # Try ### heading first
    m = re.search(r'###\s+(.+)', block)
    if m:
        title = m.group(1).strip()
        # If it starts with TASK-XXX:, extract the rest
        title = re.sub(r'^TASK-\d{3}:?\s*', '', title)
    else:
        # Use description line
        m = re.search(r'\*\*Description:\*\*\s*\n\s*(.+)', block)
        title = m.group(1).strip() if m else 'N/A'

    # Strip emojis and non-ASCII
    title = title.encode('ascii', errors='ignore').decode('ascii')
    return title[:100]

print("=== COMPLETED TASKS ===")
for task_id, block, _ in all_tasks:
    status = parse_status(block)
    if status and status in ('complete', 'completed'):
        completed.add(task_id)

if completed:
    for t in sorted(completed):
        print(f"  {t}")
else:
    print("  None")
print()

# Find next ready task
print("=== FINDING NEXT TASK ===")
found = None
for task_id, block, _ in all_tasks:
    # Skip completed
    if task_id in completed:
        continue

    status = parse_status(block) or 'unknown'
    priority = parse_priority(block)
    title = parse_title(block)
    deps = parse_deps(block)

    deps_completed = all(d in completed for d in deps)

    print(f'{task_id}: [{status}] [{priority}] {title}')
    print(f'   Dependencies: {deps if deps else "None"}')
    if deps_completed:
        print('   >>> ALL DEPS SATISFIED - READY TO EXECUTE! <<<')
        found = task_id
        break
    else:
        missing = [d for d in deps if d not in completed]
        print(f'   Missing deps: {missing}')
    print()

if not found:
    print("No next task found (all tasks complete or all blocked).")

print()
print("=== STATUS SUMMARY ===")
status_counts = {}
for task_id, block, _ in all_tasks:
    status = parse_status(block) or 'NO_STATUS'
    status_counts[status] = status_counts.get(status, 0) + 1

for s, c in sorted(status_counts.items()):
    print(f"  {s}: {c}")
