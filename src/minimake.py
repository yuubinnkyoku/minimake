import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def load_build_file(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def get_tool_version(tool: str) -> str | None:
    # TODO: ツールのバージョンを取得してください
    # ヒント:
    # - gcc: `gcc --version` の出力から抽出
    # - python: `python3 --version` の出力から抽出
    # - 正規表現 r'(\d+\.\d+\.\d+)' でバージョン番号を抽出できます
    pass


def get_tool_path(tool: str) -> str | None:
    result = subprocess.run(["which", tool], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def parse_version(v: str) -> tuple:
    return tuple(map(int, v.split(".")))


def check_version_constraint(actual: str, constraint: str) -> bool:
    # TODO: バージョン制約を満たしているかチェックしてください
    # ヒント:
    # - ">=X.Y.Z": actual が X.Y.Z 以上
    # - "==X.Y.Z": actual が X.Y.Z と一致
    # - parse_version() でタプルに変換すると比較しやすくなります
    pass


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
        print("Commands: <target>, lock, verify", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

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

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--file" and i + 1 < len(sys.argv):
            build_file = sys.argv[i + 1]
            i += 2
        else:
            targets.append(sys.argv[i])
            i += 1

    config = load_build_file(build_file)
    config = auto_resolve_inputs(config)

    for target in targets:
        if not build_with_deps(config, target):
            sys.exit(1)


if __name__ == "__main__":
    main()
