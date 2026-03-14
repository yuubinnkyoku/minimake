import json
import re
import subprocess
import sys
from pathlib import Path


def load_build_file(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def parse_includes(file_path: str) -> list[str]:
    content = Path(file_path).read_text()

    # DONE: #include "..." の形式を抽出してください
    # ヒント: re.findall(r'#include\s+"([^"]+)"', content)


    result=re.findall(r'#include\s+"([^"]+)"', content)

    return result


def collect_all_includes(file_path: str, base_dir: str = ".") -> set[str]:
    collected = set()
    visited = set()

    def visit(path: str):
        # DONE: 再帰的に #include を収集してください
        # ヒント:
        # 1. 訪問済みならスキップ
        # 2. parse_includes でインクルードを取得
        # 3. 各インクルードに対して再帰的に visit を呼ぶ
        if path in visited:
            pass
        else:
            includes=parse_includes(path)
            for i in includes:
                collected.add(i)
                visit(i)
        


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
        print("Usage: minimake <target>... [--file build_file]", file=sys.stderr)
        sys.exit(1)

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
