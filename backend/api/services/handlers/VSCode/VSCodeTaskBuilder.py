from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .VSCodeIntentParser import VSCodeIntent


class VSCodeTaskBuilder:
    """
    用途・言語・修正コンテキストに応じた `.vscode/tasks.json` を動的生成するクラス。
    - C/C++ (GCC), Python, TypeScript/React (npm/vite), Node.js のビルド・実行タスク生成
    - ProjectBuilderHandler の PartialPatch (1部分修正) 後の Diff 確認・テスト実行タスク生成にも対応
    """

    LANGUAGE_DEFAULTS: Dict[str, Tuple[str, str, List[str]]] = {
        "cpp": (
            "compile-cpp",
            "gcc",
            [
                "-Wall",
                "-fdiagnostics-color=never",
                "${file}",
                "-o",
                "${fileDirname}/${fileBasenameNoExtension}",
            ],
        ),
        "python": (
            "run-python",
            "python",
            ["${file}"],
        ),
        "typescript": (
            "build-ts",
            "npm",
            ["run", "build"],
        ),
        "javascript": (
            "run-node",
            "node",
            ["${file}"],
        ),
    }

    @classmethod
    def build_task_from_intent(
        cls,
        message: str,
        intent: Optional[VSCodeIntent] = None,
        base_label: Optional[str] = None,
        base_command: Optional[str] = None,
        base_args: Optional[List[str]] = None,
        last_patch: Optional[Any] = None,
    ) -> Dict[str, Any]:
        msg_lower = (message or "").lower()
        lang = intent.language if intent and intent.language != "general" else "cpp"
        default_label, default_cmd, default_args = cls.LANGUAGE_DEFAULTS.get(
            lang, cls.LANGUAGE_DEFAULTS["cpp"]
        )

        label = base_label or default_label
        command = base_command or default_cmd
        args = base_args if base_args is not None else list(default_args)

        task: Dict[str, Any] = {
            "label": label,
            "type": "npm" if ("npm" in msg_lower or command == "npm") else "shell",
            "command": command,
            "args": args,
        }

        # 1. group
        task["group"] = {
            "kind": "test" if ("test" in msg_lower or "テスト" in msg_lower) else "build",
            "isDefault": any(k in msg_lower for k in ("デフォルト", "default", "一発")),
        }

        # 2. options (cwd, env, shell)
        options: Dict[str, Any] = {"cwd": "${fileDirname}"}
        if "環境変数" in msg_lower or "env" in msg_lower:
            options["env"] = {"LANG": "ja_JP.UTF-8", "PYTHONIOENCODING": "utf-8"}
        if "powershell" in msg_lower:
            options["shell"] = {
                "executable": "powershell.exe",
                "args": ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"],
            }
        elif "bash" in msg_lower or "wsl" in msg_lower:
            options["shell"] = {"executable": "/bin/bash", "args": ["-c"]}
        task["options"] = options

        # 3. presentation
        is_silent = any(k in msg_lower for k in ("静か", "裏で", "silent", "邪魔しない"))
        task["presentation"] = {
            "echo": not is_silent,
            "reveal": "silent" if is_silent else "always",
            "focus": any(k in msg_lower for k in ("フォーカス", "focus", "入力")),
            "panel": "dedicated" if "専用" in msg_lower else "shared",
            "group": "build_group",
            "showReuseMessage": False,
            "clear": True,
            "revealProblems": "onProblem",
        }

        # 4. problemMatcher & background
        is_watch = any(
            k in msg_lower for k in ("watch", "監視", "バックグラウンド", "常駐", "background")
        )
        task["isBackground"] = is_watch

        if lang == "typescript":
            problem_matcher: Any = "$tsc-watch" if is_watch else "$tsc"
        elif lang == "python":
            problem_matcher = {
                "owner": "python",
                "fileLocation": ["relative", "${workspaceFolder}"],
                "pattern": {
                    "regexp": r'^\s*File "(.*)", line (\d+), in (.*)$',
                    "file": 1,
                    "line": 2,
                    "message": 3,
                },
            }
        else:
            problem_matcher = {
                "base": "$gcc",
                "owner": "cpp",
                "fileLocation": "autoDetect",
                "pattern": {
                    "regexp": r"^(.*):(\d+):(\d+):\s+(warning|error):\s+(.*)$",
                    "file": 1,
                    "line": 2,
                    "column": 3,
                    "severity": 4,
                    "message": 5,
                },
            }
            if is_watch and isinstance(problem_matcher, dict):
                problem_matcher["background"] = {
                    "activeOnStart": True,
                    "beginsPattern": r"^.*(?:Starting compilation|Watch mode).*$",
                    "endsPattern": r"^.*(?:Compilation complete|Watching for file changes).*$",
                }
                task["promptOnClose"] = True

        task["problemMatcher"] = problem_matcher

        # 5. dependsOn & dependsOrder
        if any(k in msg_lower for k in ("順番", "連続", "depends", "連携", "並列")):
            task["dependsOn"] = ["clean", "prepare"]
            task["dependsOrder"] = "parallel" if "並列" in msg_lower else "sequence"

        # 6. runOptions
        if any(k in msg_lower for k in ("自動実行", "開いた時", "folderopen", "起動時")):
            task["runOptions"] = {
                "reevaluateOnRerun": True,
                "runOn": "folderOpen",
            }

        # 7. OS別設定
        if any(k in msg_lower for k in ("os別", "windows", "mac", "osx", "linux")) and lang == "cpp":
            task["windows"] = {"command": "gcc.exe"}
            task["osx"] = {"command": "clang"}
            task["linux"] = {"command": "/usr/bin/gcc"}

        tasks_list: List[Dict[str, Any]] = [task]

        # 8. 1部分修正 (PartialPatchResult) がある場合は Diff 確認タスクも追加
        if last_patch is not None:
            patch_file = getattr(last_patch, "file_path", None) or (
                last_patch.get("file_path") if isinstance(last_patch, dict) else None
            )
            backup_file = getattr(last_patch, "backup_file_path", None) or (
                last_patch.get("backup_file_path") if isinstance(last_patch, dict) else None
            )
            if patch_file and backup_file:
                tasks_list.append(
                    {
                        "label": f"diff-last-patch ({Path(patch_file).name})",
                        "type": "shell",
                        "command": "code",
                        "args": ["--reuse-window", "--diff", str(backup_file), str(patch_file)],
                        "presentation": {"reveal": "silent", "panel": "shared"},
                        "problemMatcher": [],
                    }
                )

        return {
            "version": "2.0.0",
            "tasks": tasks_list,
        }