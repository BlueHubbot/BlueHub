"""Download Python packages from PyPI and save them for offline installation.
Platform-aware: filters wheels for current Python version and OS."""

import json
import os
import re
import sys
import urllib.request

PACKAGES = [
    "passlib",
    "bcrypt",
    "python-jose",
    "python-multipart",
    "pytest",
    "pytest-asyncio",
]

PACKAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "_packages")
os.makedirs(PACKAGE_DIR, exist_ok=True)

# Python version info for filtering
PY_MAJOR = sys.version_info.major
PY_MINOR = sys.version_info.minor

# Detect platform tags
import platform

MACHINE = platform.machine().lower()
if MACHINE in ("amd64", "x86_64"):
    PLATFORM_TAG = "win_amd64"
elif MACHINE in ("i386", "i686", "x86"):
    PLATFORM_TAG = "win32"
elif MACHINE in ("arm64", "aarch64"):
    PLATFORM_TAG = "win_arm64"
else:
    PLATFORM_TAG = "any"

ABI_TAG = f"cp{PY_MAJOR}{PY_MINOR}"
PY_TAG = f"cp{PY_MAJOR}{PY_MINOR}"

print(f"Python {sys.version}")
print(f"Platform: {PLATFORM_TAG}, ABI: {ABI_TAG}")


def download_json(url):
    """Download JSON from a URL."""
    req = urllib.request.Request(url, headers={"User-Agent": "bluehub-installer/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def download_file(url, dest_path):
    """Download a file from URL to destination path."""
    print(f"  Downloading: {os.path.basename(dest_path)}")
    req = urllib.request.Request(url, headers={"User-Agent": "bluehub-installer/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
        with open(dest_path, "wb") as f:
            f.write(data)
    return dest_path


def is_compatible_wheel(filename) -> bool:
    """Check if a wheel filename is compatible with current Python/OS."""
    if not filename.endswith(".whl"):
        return False

    # Parse wheel filename: {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
    parts = filename.split("-")
    if len(parts) < 4:
        return False

    # Tags are the last 3 parts before .whl
    platform_tag_part = parts[-1].replace(".whl", "")
    abi_tag_part = parts[-2]
    py_tag_part = parts[-3]

    # Check platform compatibility
    platform_tags = platform_tag_part.split(".")
    if not any(t in ("any", PLATFORM_TAG, "win32", "win_amd64") for t in platform_tags):
        return False

    # Check Python version compatibility
    py_tags = py_tag_part.split(".")
    py_compatible = False
    for tag in py_tags:
        if tag in {"py3", "py2.py3", "py2.py3.py4"}:
            py_compatible = True
            break
        if tag == "py3-none":
            py_compatible = True
            break
        if tag.startswith("cp") and not tag.startswith("cp3"):
            continue
        if tag.startswith("cp"):
            # Extract version numbers
            nums = tag[2:]
            if len(nums) == 2:
                major = int(nums[0])
                minor = int(nums[1])
                if major == PY_MAJOR and minor <= PY_MINOR:
                    py_compatible = True
                    break
            elif len(nums) == 1:
                if int(nums) == PY_MAJOR:
                    py_compatible = True
                    break

    if not py_compatible:
        return False

    # Check ABI compatibility
    abi_tags = abi_tag_part.split(".")
    abi_compatible = False
    for tag in abi_tags:
        if tag == "none":
            abi_compatible = True
            break
        if tag.startswith("cp") and tag[2:].isdigit():
            # Accept if abi <= current Python version (e.g., cp39 works on cp310)
            nums = tag[2:]
            if len(nums) == 2:
                major = int(nums[0])
                minor = int(nums[1])
                if major == PY_MAJOR and minor <= PY_MINOR:
                    abi_compatible = True
                    break

    return abi_compatible


def get_best_download(info):
    """Get the best matching download for the current platform."""
    # First, try to find a compatible wheel
    for url_info in info.get("urls", []):
        filename = url_info.get("filename", "")
        if is_compatible_wheel(filename):
            return url_info

    # Fall back to source distribution
    for url_info in info.get("urls", []):
        filename = url_info.get("filename", "")
        if filename.endswith((".tar.gz", ".zip")):
            return url_info

    # Return first URL as last resort
    if info.get("urls"):
        return info["urls"][0]
    return None


def get_dependencies(info):
    """Get dependencies from requires_dist, filtering out extras."""
    requires = info.get("info", {}).get("requires_dist", []) or []
    # Handle case where requires_dist is a string
    if isinstance(requires, str):
        requires = [requires]

    deps = []
    for req in requires:
        if not isinstance(req, str):
            continue
        if "extra ==" in req:
            continue
        # Extract package name (before any version specifiers, markers, etc.)
        # Strip parenthesized extras like [extra]
        req_clean = re.split(r'[<>!=;[]', req)[0].strip()
        if req_clean and not req_clean.startswith("("):
            deps.append(req_clean.lower())
    return deps


def expand_dependencies(package_name, seen=None, depth=0):
    """Recursively expand all dependencies."""
    if seen is None:
        seen = set()
    pkg_lower = package_name.lower().strip()
    if pkg_lower in seen:
        return []
    seen.add(pkg_lower)

    indent = "  " * (depth + 1)
    print(f"{indent}{package_name}")

    try:
        info = download_json(f"https://pypi.org/pypi/{pkg_lower}/json")
    except Exception as e:
        print(f"{indent}  Warning: Could not fetch info for {pkg_lower}: {e}")
        return [pkg_lower]

    deps = get_dependencies(info)
    all_deps = [pkg_lower]
    for dep in deps:
        all_deps.extend(expand_dependencies(dep, seen, depth + 1))
    return all_deps


def main() -> None:
    print("Expanding dependency tree...")
    all_packages = []
    for pkg in PACKAGES:
        print(f"\n{pkg}:")
        all_packages.extend(expand_dependencies(pkg))

    # Remove duplicates while preserving order
    seen = set()
    all_packages_unique = []
    for pkg in all_packages:
        if pkg not in seen:
            seen.add(pkg)
            all_packages_unique.append(pkg)

    print(f"\nPackages to download (including deps): {len(all_packages_unique)}")
    for pkg in all_packages_unique:
        print(f"  - {pkg}")

    # Download each package
    for pkg in all_packages_unique:
        print(f"\nProcessing: {pkg}")
        try:
            info = download_json(f"https://pypi.org/pypi/{pkg}/json")
            best = get_best_download(info)
            if best:
                filename = best["filename"]
                file_url = best["url"]
                dest = os.path.join(PACKAGE_DIR, filename)
                if not os.path.exists(dest):
                    download_file(file_url, dest)
                else:
                    print(f"  Already exists: {filename}")
                # Also check if we need to download source dist if wheel isn't ideal
            else:
                print(f"  No suitable download found for {pkg}")
        except Exception as e:
            print(f"  Error downloading {pkg}: {e}")

    # Print summary
    wheel_files = sorted([f for f in os.listdir(PACKAGE_DIR) if f.endswith((".whl", ".tar.gz", ".zip"))])
    print(f"\n{'='*60}")
    print(f"Download complete - {len(wheel_files)} files in {PACKAGE_DIR}:")
    for f in wheel_files:
        size = os.path.getsize(os.path.join(PACKAGE_DIR, f))
        print(f"  {f} ({size:,} bytes)")

    print("\nTo install, run:")
    print(f'  pip install --no-index --find-links="{PACKAGE_DIR}" \\')
    for pkg in PACKAGES:
        print(f'    {pkg} \\')

    print("\nOr extract and install manually:")
    print(f'  cd "{PACKAGE_DIR}"')
    print('  python -m pip install --no-index --find-links="." "passlib" "bcrypt" "python-jose" "python-multipart"')


if __name__ == "__main__":
    main()
