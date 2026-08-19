# import os
# import subprocess
# import time
# import webbrowser

# def find_file(start_path, target_filename, ignore_dirs=None):
#     """指定したファイルを探し、その絶対パスを返す"""
#     if ignore_dirs is None:
#         # node_modules などの不要なフォルダは探索から除外
#         ignore_dirs = ['node_modules', '.git', '__pycache__', 'venv', '.venv']
        
#     for root, dirs, files in os.walk(start_path):
#         dirs[:] = [d for d in dirs if d not in ignore_dirs]
#         if target_filename in files:
#             return os.path.join(root, target_filename)
#     return None

# def start_new_terminal(title, command, cwd):
#     """Windowsの新しいコマンドプロンプトを開いてコマンドを実行する"""
#     print(f"[*] Launching {title}...")
#     print(f"    - 実行フォルダ: {cwd}")
#     print(f"    - コマンド: {command}\n")
    
#     # start コマンドで新しいウィンドウを開く
#     # cmd /k を使うことで、エラーが起きてもウィンドウが閉じずに残る
#     cmd_str = f'start "{title}" cmd /k "cd /d {cwd} && {command}"'
#     subprocess.Popen(cmd_str, shell=True)

# def main():
#     base_dir = os.path.dirname(os.path.abspath(__file__))
#     print("===")
#     print("  Starting All Services (別ウィンドウ起動モード)")
#     print("===\n")

#     # ===
#     # 1. Python Backend (AI Server) の探索と起動
#     # ===
#     ai_server_path = find_file(base_dir, "ai_server.py")
#     if ai_server_path:
#         # backendフォルダの親ディレクトリをカレントディレクトリとする
#         backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(ai_server_path)))
#         start_new_terminal(
#             title="Backend: Python (AI)",
#             command="python -m backend.api.ai_server",
#             cwd=backend_dir
#         )
#     else:
#         print("[ERROR] ai_server.py が見つかりませんでした。")
        
#     time.sleep(4)

#     # ===
#     # 2. Frontend (Vite) の探索と起動
#     # ===
#     package_json_path = find_file(base_dir, "package.json")
#     frontend_dir = None
#     if package_json_path:
#         frontend_dir = os.path.dirname(package_json_path)
#         start_new_terminal(
#             title="Frontend: Vite",
#             command="npm run dev -- --force",
#             cwd=frontend_dir
#         )
#     else:
#         print("[ERROR] package.json が見つかりませんでした。")
        
#     time.sleep(6)

#     # ===
#     # 3. api.py (FastAPI Server) の探索と起動
#     # ===
#     api_py_path = None
#     if frontend_dir:
#         api_py_path = find_file(frontend_dir, "api.py")
    
#     if not api_py_path:
#         api_py_path = find_file(base_dir, "api.py")

#     if api_py_path:
#         fastapi_dir = os.path.dirname(api_py_path)
#         start_new_terminal(
#             title="API Server: FastAPI",
#             command="python api.py",
#             cwd=fastapi_dir
#         )
#     else:
#         print("[ERROR] FastAPI用の api.py が見つかりませんでした。")

#     # ===
#     # 完了とブラウザ起動
#     # ===
#     print("===")
#     print("  すべてのプロセスを別ウィンドウで起動しました。")
#     print("  各黒い画面（ターミナル）のエラー文を確認してください。")
#     print("===")
    
#     time.sleep(2)
#     # ポートはご自身の環境に合わせて変更してください (例: 5173, 8080 など)
#     port = "5173" 
#     print(f"[*] ブラウザを開きます: http://localhost:{port}")
#     webbrowser.open(f'http://localhost:{port}')

# if __name__ == "__main__":
#     main()

# ↑昔のコード

import os
import subprocess
import time
import webbrowser

def start_new_terminal(title, command, cwd):
    """Windowsの新しいコマンドプロンプトを開いてコマンドを実行する"""
    print(f"[*] Launching {title}...")
    print(f"    - 実行フォルダ: {cwd}")
    print(f"    - コマンド: {command}\n")
    
    cmd_str = f'start "{title}" cmd /k "cd /d {cwd} && {command}"'
    subprocess.Popen(cmd_str, shell=True)

def main():
    # StartApp.pyがある To/ フォルダ
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("===")
    print("  Starting All Services (Base System + Plugins)")
    print("===\n")

    # ==========================================
    # 🌟 1. Base Backend (To/backend/api/ai_server.py など)
    # ==========================================
    base_backend_dir = os.path.join(base_dir, "backend")
    if os.path.exists(base_backend_dir):
        # もし以前 ai_server を起動していたならこのコマンド
        start_new_terminal(
            title="Base Backend: Python",
            command="python -m api.ai_server",  # 適切な起動コマンドに書き換えてください
            cwd=base_backend_dir
        )
    else:
        print(f"[WARN] Base Backend フォルダが見つかりません: {base_backend_dir}")
        
    time.sleep(2)

    # ==========================================
    # 🌟 2. Base Frontend (To/frontend)
    # ==========================================
    base_frontend_dir = os.path.join(base_dir, "frontend")
    if os.path.exists(base_frontend_dir) and os.path.exists(os.path.join(base_frontend_dir, "package.json")):
        start_new_terminal(
            title="Base Frontend: Vite",
            command="npm run dev -- --force --port 5174", # ポート衝突を避けるために 5174 を指定
            cwd=base_frontend_dir
        )
    else:
        print(f"[WARN] Base Frontend フォルダが見つかりません: {base_frontend_dir}")

    time.sleep(4)

    # ==========================================
    # 🌟 3. Plugin Backend (To/plugins/Tokyo_hackson_23/backend)
    # ==========================================
    plugin_backend_dir = os.path.join(base_dir, "plugins", "Tokyo_hackson_23", "backend")
    if os.path.exists(plugin_backend_dir) and os.path.exists(os.path.join(plugin_backend_dir, "api.py")):
        start_new_terminal(
            title="Plugin API Server: FastAPI",
            command="python api.py",
            cwd=plugin_backend_dir
        )
    else:
        print(f"[WARN] Plugin Backend フォルダが見つかりません: {plugin_backend_dir}")

    time.sleep(2)

    # ==========================================
    # 🌟 4. Plugin Frontend (To/plugins/Tokyo_hackson_23/renderer)
    # ==========================================
    plugin_renderer_dir = os.path.join(base_dir, "plugins", "Tokyo_hackson_23", "renderer")
    if os.path.exists(plugin_renderer_dir) and os.path.exists(os.path.join(plugin_renderer_dir, "package.json")):
        start_new_terminal(
            title="Plugin Frontend: Vite",
            command="npm run dev -- --force", # こちらはデフォルトの 5173
            cwd=plugin_renderer_dir
        )
    else:
        print(f"[WARN] Plugin Frontend フォルダが見つかりません: {plugin_renderer_dir}")

    # ===
    # 完了とブラウザ起動
    # ===
    print("===")
    print("  すべてのプロセスを別ウィンドウで起動しました。")
    print("===")
    
    time.sleep(5) 
    # メインで見たい画面のポートを開く（プラグイン側なら5173）
    port = "5173" 
    print(f"[*] ブラウザを開きます: http://localhost:{port}")
    webbrowser.open(f'http://localhost:{port}')

if __name__ == "__main__":
    main()