import json
import subprocess
import sys


def load_build_file(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def build_target(config: dict, target: str) -> bool:
    targets = config.get("targets", {})

    if target not in targets:
        print(f"Error: Unknown target '{target}'", file=sys.stderr)
        return False

    target_config = targets[target]
    command = target_config.get("command")

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

    for target in targets:
        if not build_target(config, target):
            sys.exit(1)


if __name__ == "__main__":
    main()
