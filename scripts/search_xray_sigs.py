"""Search for function signatures and key patterns in xray.py"""

with open("d:/BlueHub/modules/vpn/xray.py") as f:
    content = f.read()

# Find function definitions
patterns = [
    "write_server_config",
    "build_full_server_config",
    "generate_client_config",
    "add_user_via_config",
    "get_client_config",
    "collect_traffic_via_api",
    "provision_account",
    "suspend_account",
    "restore_account",
    "generate_inbound_config",
    "parse_traffic_from_log",
    "get_user_traffic",
    "XrayAPIConnectionError",
    "XRAY_BIN",
    "os.environ.get",
]

for pat in patterns:
    for i, line in enumerate(content.split('\n'), 1):
        if pat in line:
            # Print the line and next 2 lines for function defs
            if line.strip().startswith(('def ', 'class ')):
                print(f"Line {i}: {line}")
                next_lines = content.split('\n')[i:i+15]
                for j, nl in enumerate(next_lines):
                    if nl.strip().startswith(('"""', '\"\"\"')):
                        continue
                    if nl.strip() and not nl.strip().startswith('#'):
                        print(f"  -> Next code: Line {i+j+1}: {nl[:120]}")
                        break
            elif "XRAY_BIN" in line or "os.environ.get" in line:
                print(f"Line {i}: {line}")
