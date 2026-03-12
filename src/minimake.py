"""
minimake - シンプルなビルドシステム

このファイルには、ビルドシステムの基本的な機能を実装します。
TODO コメントがある箇所を実装してください。
"""

import sys


def load_build_file(path: str) -> dict:
    """
    ビルド定義ファイル（JSON）を読み込んで辞書として返す

    Args:
        path: ファイルパス（例: "build.json"）

    Returns:
        パースされた辞書
    """
    # TODO: ここを実装してください
    # ヒント: json.load() を使います
    pass


def build_target(config: dict, target: str) -> bool:
    """
    指定されたターゲットをビルドする

    Args:
        config: load_build_file で読み込んだ設定
        target: ビルドするターゲット名（例: "hello.o"）

    Returns:
        ビルド成功なら True、失敗なら False
    """
    targets = config.get("targets", {})

    # ターゲットが存在するか確認
    if target not in targets:
        print(f"Error: Unknown target '{target}'", file=sys.stderr)
        return False

    target_config = targets[target]
    command = target_config.get("command")

    # コマンドが指定されているか確認
    if not command:
        print(f"Error: No command for target '{target}'", file=sys.stderr)
        return False

    print(f"Building {target}...")
    print(f"  $ {command}")

    # TODO: ここでコマンドを実行してください
    # ヒント: subprocess.run() を使います
    # shell=True を指定すると、シェルコマンドとして実行できます
    # result.returncode が 0 でなければビルド失敗です
    pass


def main():
    if len(sys.argv) < 2:
        print("Usage: minimake <target>... [--file build_file]", file=sys.stderr)
        sys.exit(1)

    # TODO: 引数をパースして、複数のターゲットを順番にビルドできるようにしてください
    # --file オプションでビルド定義ファイルを指定できるようにしてください
    #
    # ヒント:
    # - targets: ビルドするターゲットのリスト
    # - build_file: ビルド定義ファイルのパス（デフォルト: "build.json"）
    pass


if __name__ == "__main__":
    main()
