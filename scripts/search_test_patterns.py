"""Search for patterns in test_xray.py that may mismatch xray.py"""
with open("d:/BlueHub/tests/unit/test_xray.py", "r") as f:
    content = f.read()

patterns = [
    "get_client_config",
    "XRAY_EXECUTABLE",
    "output_dir",
    "server_addr",
    "XrayAPIConnectionError(",
    "generate_client_config",
    "build_full_server_config",
    "add_user_via_config",
    "write_server_config",
    "collect_traffic_via_api",
    "get_user_traffic",
    "generate_inbound_config",
    "provision_account",
    "suspend_account",
    "restore_account",
    "RealityKeyPair",
    "inbounds=",
    "inbound_configs=",
    "config_path",
]

for pat in patterns:
    for i, line in enumerate(content.split('\n'), 1):
        if pat in line:
            print(f"Line {i}: {line.strip()[:140]}")