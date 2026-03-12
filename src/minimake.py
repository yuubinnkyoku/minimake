import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

CACHE_DIR = Path(".minimake-cache")


def load_build_file(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def get_tool_version(tool: str) -> str | None:
    try:
        if tool == "gcc":
            result = subprocess.run(["gcc", "--version"], capture_output=True, text=True)
            match = re.search(r"(\d+\.\d+\.\d+)", result.stdout)
            if match:
                return match.group(1)
        elif tool == "python":
            result = subprocess.run(
                ["python3", "--version"], capture_output=True, text=True
            )
            match = re.search(r"(\d+\.\d+\.\d+)", result.stdout)
            if match:
                return match.group(1)
    except FileNotFoundError:
        return None
    return None


def get_tool_path(tool: str) -> str | None:
    result = subprocess.run(["which", tool], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def parse_version(v: str) -> tuple:
    return tuple(map(int, v.split(".")))


def check_version_constraint(actual: str, constraint: str) -> bool:
    actual_tuple = parse_version(actual)

    if constraint.startswith(">="):
        required = parse_version(constraint[2:])
        return actual_tuple >= required
    elif constraint.startswith("<="):
        required = parse_version(constraint[2:])
        return actual_tuple <= required
    elif constraint.startswith("=="):
        required = parse_version(constraint[2:])
        return actual_tuple == required
    else:
        return actual == constraint


def compute_file_hash(path: str) -> str:
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"


def generate_lockfile(config: dict) -> dict:
    tools_config = config.get("tools", {})
    locked_tools = {}

    for tool, spec in tools_config.items():
        version = get_tool_version(tool)
        path = get_tool_path(tool)

        if version is None:
            raise ValueError(f"Tool not found: {tool}")

        constraint = spec.get("version", "")
        if constraint and not check_version_constraint(version, constraint):
            raise ValueError(
                f"Tool {tool} version {version} does not satisfy {constraint}"
            )

        locked_tools[tool] = {
            "version": version,
            "path": path,
            "hash": compute_file_hash(path) if path else None,
        }

    return {
        "tools": locked_tools,
        "generated_at": datetime.now().isoformat(),
    }


def save_lockfile(lockfile: dict, path: str = "build.lock"):
    with open(path, "w") as f:
        json.dump(lockfile, f, indent=2)


def verify_lockfile(lockfile: dict) -> list[str]:
    errors = []
    locked_tools = lockfile.get("tools", {})

    for tool, locked in locked_tools.items():
        current_version = get_tool_version(tool)
        current_path = get_tool_path(tool)

        if current_version is None:
            errors.append(f"{tool}: not installed")
            continue

        if current_version != locked["version"]:
            errors.append(
                f"{tool}: version mismatch "
                f"(locked: {locked['version']}, current: {current_version})"
            )

        if current_path and locked.get("hash"):
            current_hash = compute_file_hash(current_path)
            if current_hash != locked["hash"]:
                errors.append(f"{tool}: binary hash mismatch")

    return errors


def compute_cache_key(config: dict, target: str, dep_keys: dict[str, str]) -> str:
    targets = config.get("targets", {})
    target_config = targets[target]
    hasher = hashlib.sha256()

    command = target_config.get("command", "")
    hasher.update(command.encode())

    inputs = target_config.get("inputs", [])
    for input_file in sorted(inputs):
        if Path(input_file).exists():
            file_hash = compute_file_hash(input_file)
            hasher.update(f"{input_file}:{file_hash}".encode())

    deps = target_config.get("deps", [])
    for dep in sorted(deps):
        if dep in dep_keys:
            hasher.update(f"dep:{dep}:{dep_keys[dep]}".encode())

    return hasher.hexdigest()


def get_cache_path(cache_key: str) -> Path:
    return CACHE_DIR / cache_key


def save_to_cache(cache_key: str, target: str):
    cache_path = get_cache_path(cache_key)
    cache_path.mkdir(parents=True, exist_ok=True)

    target_path = Path(target)
    if target_path.exists():
        shutil.copy2(target_path, cache_path / target_path.name)

    metadata = {"target": target, "created_at": datetime.now().isoformat()}
    with open(cache_path / "metadata.json", "w") as f:
        json.dump(metadata, f)


def restore_from_cache(cache_key: str, target: str) -> bool:
    cache_path = get_cache_path(cache_key)

    if not cache_path.exists():
        return False

    cached_file = cache_path / Path(target).name
    if not cached_file.exists():
        return False

    shutil.copy2(cached_file, target)
    return True


def build_with_cache(config: dict, target: str, dep_keys: dict[str, str]) -> tuple[bool, str]:
    targets = config.get("targets", {})
    target_config = targets[target]

    cache_key = compute_cache_key(config, target, dep_keys)

    if cache_key and restore_from_cache(cache_key, target):
        print(f"Cache hit: {target} ({cache_key[:8]}...)")
        return True, cache_key

    command = target_config.get("command")
    if not command:
        print(f"Error: No command for target '{target}'", file=sys.stderr)
        return False, ""

    print(f"Building {target}..." + (f" ({cache_key[:8]}...)" if cache_key else ""))
    print(f"  $ {command}")

    result = subprocess.run(command, shell=True)

    if result.returncode != 0:
        print(f"Error: Build failed for '{target}'", file=sys.stderr)
        return False, ""

    if cache_key:
        save_to_cache(cache_key, target)

    return True, cache_key or ""


def build_all_with_cache(config: dict, target: str) -> bool:
    try:
        order = resolve_build_order(config, target)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return False

    print(f"Build order: {' -> '.join(order)}")

    dep_keys = {}

    for t in order:
        success, cache_key = build_with_cache(config, t, dep_keys)
        if not success:
            return False
        dep_keys[t] = cache_key

    return True


def cache_stats():
    if not CACHE_DIR.exists():
        print("No cache found")
        return

    total_size = 0
    entry_count = 0

    for entry in CACHE_DIR.iterdir():
        if entry.is_dir():
            entry_count += 1
            for file in entry.iterdir():
                total_size += file.stat().st_size

    print(f"Cache entries: {entry_count}")
    print(f"Total size: {total_size / 1024 / 1024:.2f} MB")


def cache_clean():
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
        print("Cache cleaned")


def parse_includes(file_path: str) -> list[str]:
    content = Path(file_path).read_text()
    pattern = r'#include\s+"([^"]+)"'
    return re.findall(pattern, content)


def collect_all_includes(file_path: str, base_dir: str = ".") -> set[str]:
    collected = set()
    visited = set()

    def visit(path: str):
        if path in visited:
            return
        visited.add(path)

        full_path = Path(base_dir) / path
        if not full_path.exists():
            return

        includes = parse_includes(str(full_path))
        for inc in includes:
            inc_path = Path(base_dir) / inc
            if inc_path.exists():
                collected.add(inc)
                visit(inc)

    visit(file_path)
    return collected


def auto_resolve_inputs(config: dict, base_dir: str = ".") -> dict:
    targets = config.get("targets", {})

    for target_name, target_config in targets.items():
        if "inputs" in target_config:
            continue

        command = target_config.get("command", "")
        c_files = re.findall(r'\b(\w+\.c)\b', command)

        all_inputs = set(c_files)

        for c_file in c_files:
            includes = collect_all_includes(c_file, base_dir)
            all_inputs.update(includes)

        target_config["inputs"] = list(all_inputs)

    return config


def needs_rebuild(config: dict, target: str) -> bool:
    targets = config.get("targets", {})
    target_config = targets[target]

    target_path = Path(target)

    if not target_path.exists():
        return True

    target_mtime = target_path.stat().st_mtime

    for input_file in target_config.get("inputs", []):
        input_path = Path(input_file)
        if input_path.exists() and input_path.stat().st_mtime > target_mtime:
            return True

    for dep in target_config.get("deps", []):
        dep_path = Path(dep)
        if dep_path.exists() and dep_path.stat().st_mtime > target_mtime:
            return True

    return False


def build_target(config: dict, target: str) -> bool:
    targets = config.get("targets", {})

    if target not in targets:
        print(f"Error: Unknown target '{target}'", file=sys.stderr)
        return False

    target_config = targets[target]
    command = target_config.get("command")

    if not needs_rebuild(config, target):
        print(f"Skipping {target} (up to date)")
        return True

    if not command:
        print(f"Error: No command for target '{target}'", file=sys.stderr)
        return False

    print(f"Building {target}...")
    print(f"  $ {command}")

    result = subprocess.run(command, shell=True)

    if result.returncode != 0:
        print(f"Error: Build failed for '{target}'", file=sys.stderr)
        return False

    return True


def resolve_build_order(config: dict, target: str) -> list[str]:
    targets = config.get("targets", {})

    visited = set()
    visiting = set()
    order = []

    def visit(t: str):
        if t in visited:
            return
        if t in visiting:
            raise ValueError(f"Circular dependency detected: {t}")

        if t not in targets:
            raise ValueError(f"Unknown target: {t}")

        visiting.add(t)

        for dep in targets[t].get("deps", []):
            visit(dep)

        visiting.remove(t)
        visited.add(t)
        order.append(t)

    visit(target)
    return order


def build_with_deps(config: dict, target: str) -> bool:
    try:
        order = resolve_build_order(config, target)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return False

    print(f"Build order: {' -> '.join(order)}")

    for t in order:
        if not build_target(config, t):
            return False

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: minimake <command> [args...]", file=sys.stderr)
        print("Commands: <target>, lock, verify, cache-stats, cache-clean", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "cache-stats":
        cache_stats()
        return

    if command == "cache-clean":
        cache_clean()
        return

    if command == "lock":
        build_file = "build.json"
        if len(sys.argv) > 2 and sys.argv[2] == "--file":
            build_file = sys.argv[3]
        config = load_build_file(build_file)
        lockfile = generate_lockfile(config)
        save_lockfile(lockfile)
        print("Generated build.lock")
        return

    if command == "verify":
        if not Path("build.lock").exists():
            print("Error: build.lock not found", file=sys.stderr)
            sys.exit(1)

        with open("build.lock") as f:
            lockfile = json.load(f)

        errors = verify_lockfile(lockfile)
        if errors:
            print("Verification failed:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            sys.exit(1)
        print("Verification passed")
        return

    targets = []
    build_file = "build.json"
    use_cache = False

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--file" and i + 1 < len(sys.argv):
            build_file = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--cache":
            use_cache = True
            i += 1
        else:
            targets.append(sys.argv[i])
            i += 1

    config = load_build_file(build_file)
    config = auto_resolve_inputs(config)

    for target in targets:
        if use_cache:
            if not build_all_with_cache(config, target):
                sys.exit(1)
        else:
            if not build_with_deps(config, target):
                sys.exit(1)


if __name__ == "__main__":
    main()
