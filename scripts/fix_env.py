"""Fix .env file to have actual multi-line PEM values instead of escaped \\n sequences."""
import os

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")

with open(env_path, encoding="utf-8") as f:
    content = f.read()

# Check if the file has quoted single-line values with \\n
# Pattern: JWT_PRIVATE_KEY="-----BEGIN...\n...\n..."
# The regex needs to match the whole quoted value on a single line
# Since the file is read as text, \\n appears as two chars: backslash (0x5C) then n (0x6E)

# Replace JWT_PRIVATE_KEY="..." (quoted, single-line with \n escapes)
# We need to capture the content between the first " after = and the last " before end of line
lines = content.split('\n')
new_lines = []
for line in lines:
    if line.startswith("JWT_PRIVATE_KEY="):
        # Extract the value between quotes
        eq_pos = line.find("=")
        rest = line[eq_pos+1:]
        if rest.startswith('"') and rest.endswith('"'):
            val = rest[1:-1]  # Remove surrounding quotes
            # Replace \n with actual newlines
            val = val.replace('\\n', '\n')
            new_lines.append("JWT_PRIVATE_KEY=" + val)
        else:
            new_lines.append(line)
    elif line.startswith("JWT_PUBLIC_KEY="):
        eq_pos = line.find("=")
        rest = line[eq_pos+1:]
        if rest.startswith('"') and rest.endswith('"'):
            val = rest[1:-1]
            val = val.replace('\\n', '\n')
            new_lines.append("JWT_PUBLIC_KEY=" + val)
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

new_content = '\n'.join(new_lines)

with open(env_path, "w", encoding="utf-8") as f:
    f.write(new_content)

# Verify
with open(env_path, encoding="utf-8") as f:
    verify = f.read()
print(f"File size: {len(verify)} bytes")
print(f"Number of lines: {len(verify.split(chr(10)))}")
print("First line:", repr(verify.split(chr(10))[0][:80]))
print("Contains BEGIN PRIVATE KEY:", "BEGIN PRIVATE KEY" in verify)
print("Contains literal \\n (backslash-n):", "\\n" in verify)
