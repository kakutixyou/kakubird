import os
import subprocess
import time
import argparse
import sys

# ==========================================
# 0. 実行場所の自動調整
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)
print(f"📁 実行ディレクトリ: {SCRIPT_DIR}")

# ==========================================
# 1. 設定部分（処理するテーマの一覧）
# ==========================================
CSV_URL = "https://data.storage.data.metro.tokyo.lg.jp/digitalservice/130001_open_data_list.csv"

# 施設・街テーマ
THEMES = [
    ("park", "公園"),
    ("aed", "AED"),
    ("disaster", "防災・避難所"),
    ("sports", "スポーツ施設"),
    ("library", "図書館"),
    ("shopping", "買い物・スーパー"),
    ("downtown", "繁華街"),
    ("entertainment", "娯楽施設（博物館・遊園地・動物園など）"),
    ("security", "治安・防犯")
]

# # 職業テーマ
# OCCUPATION_THEMES = [
#     ("occupation_game_designer", "ゲームデザイナー（数学・理科カードゲーム）"),
#     ("occupation_nurse", "看護師"),
#     ("occupation_architect", "建築士"),
#     ("occupation_weather_forecaster", "気象予報士"),
#     ("occupation_patissier", "パティシエ"),
# ]

# ==========================================
# 2. 画面表示とコマンド実行の関数
# ==========================================
def print_manual(title, text):
    print("\n" + "="*60)
    print(f"📘 【{title}】")
    print("-" * 60)
    print(text)
    print("="*60 + "\n")

def run_command(command):
    print(f"▶ 実行中: {command}")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"\n❌ エラーが発生しました。処理を中断します。")
        sys.exit(1)
    print("✅ 完了\n")

# ==========================================
# 3. 処理フロー関数
# ==========================================
def run_facility_themes():
    """施設・街テーマの処理（サブメニュー）"""
    print("\n" + "="*42)
    print("🔍 どのテーマのデータを収集・更新しますか？")
    print("="*42)
    for i, (t_id, t_name) in enumerate(THEMES, start=1):
        print(f"[{i}] {t_name} ({t_id})")
    print(f"[{len(THEMES) + 1}] すべてのテーマを実行")
    print("="*42)
    
    target_themes = []
    while True:
        choice = input("👉 実行したい番号を入力してください (キャンセルは 0): ")
        if choice == "0":
            return
        if choice.isdigit():
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(THEMES):
                target_themes = [THEMES[choice_idx]]
                target_text = f"対象: {target_themes[0][1]}"
                break
            elif choice_idx == len(THEMES):
                target_themes = THEMES
                target_text = "対象: 全てのテーマ"
                break
        print("❌ 無効な入力です。正しい番号を入力してください。")

    print_manual("処理開始", f"{target_text} のデータ収集とスコア計算を行います。")
    time.sleep(1)

    for theme_id, theme_name in target_themes:
        print(f"\n--- 🚀 {theme_name} ({theme_id}) の処理を開始 ---")
        run_command(f'python opendata_workflow.py import_csv --theme {theme_id} --csv-url "{CSV_URL}"')
        run_command(f'python opendata_workflow.py download --theme {theme_id}')
        run_command(f'python opendata_workflow.py normalize_schema --theme {theme_id}')
        
        if theme_id == "entertainment":
            run_command(f'python opendata_workflow.py entertainment_score --theme {theme_id}')
        elif theme_id == "population":
            run_command(f'python opendata_workflow.py population_score --theme {theme_id}')
        else:
            run_command(f'python opendata_workflow.py score --theme {theme_id}')
        time.sleep(1)
        
    print_manual("🎉 完了", f"{target_text} のデータ準備が整いました！")

# def run_occupation_themes():
#     """職業テーマの処理"""
#     if not OCCUPATION_THEMES:
#         print("⚠️ OCCUPATION_THEMESが空のためスキップします。")
#         return

#     print_manual("職業テーマ処理開始", "単元と職業のつながりデータを構築します。")
#     time.sleep(1)

#     for theme_id, theme_name in OCCUPATION_THEMES:
#         print(f"\n--- 🚀 {theme_name} ({theme_id}) の処理を開始 ---")
#         run_command(f'python opendata_workflow.py import_occupation --theme {theme_id}')
#         run_command(f'python opendata_workflow.py build_curriculum_map --theme {theme_id}')
#         time.sleep(1)
        
#     print_manual("🎉 完了", "すべての職業テーマのデータ準備が整いました！")
def start_servers():
    """バックエンドとフロントエンドを同時に起動する"""
    backend_dir = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
    
    # 変更前: renderer_dir = os.path.abspath(os.path.join(SCRIPT_DIR, "../../renderer"))
    # 変更後: 2つ上の階層（Tokyo_hackson_23 直下）をフロントエンドの場所として指定
    frontend_dir = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))

    print_manual(
        "ローカルサーバー起動", 
        f"以下の2つを同時に起動します。\n"
        f"・APIサーバー ({backend_dir}/api.py)\n"
        f"・フロントエンド ({frontend_dir} で npm run dev)"
    )

    try:
        # Popenを使って、処理をブロックせずに裏で同時に走らせる
        api_proc = subprocess.Popen(["python", "api.py"], cwd=backend_dir)
        # npm_proc も cwd を frontend_dir に変更
        npm_proc = subprocess.Popen("npm run dev", shell=True, cwd=frontend_dir)

        print("\n🟢 サーバーが起動しました！")
        print("💡 終了するにはこのターミナルで [Ctrl + C] を押してください。\n")
        
        # ユーザーがCtrl+Cを押すまでここで待機し続ける
        api_proc.wait()
        npm_proc.wait()
        
    except KeyboardInterrupt:
        # Ctrl+C が押されたら、両方のプロセスを安全に終了させる
        print("\n\n🛑 停止信号を受け取りました。サーバーを終了します...")
        api_proc.terminate()
        npm_proc.terminate()
        api_proc.wait()
        npm_proc.wait()
        print("✅ サーバーを安全に停止しました。")

# ==========================================
# 4. メインメニュー
# ==========================================
def main():
    # コマンドライン引数（--theme）が直接指定された場合は施設フローに直行（元の機能を維持）
    parser = argparse.ArgumentParser(description="オープンデータ収集・サーバー起動スクリプト")
    parser.add_argument("--theme", type=str, help="実行したいテーマのIDを指定してください")
    args = parser.parse_args()

    if args.theme:
        target_themes = [t for t in THEMES if t[0] == args.theme]
        if not target_themes:
            print(f"❌ エラー: テーマ '{args.theme}' は見つかりませんでした。")
            return
        run_command(f'python opendata_workflow.py import_csv --theme {args.theme} --csv-url "{CSV_URL}"')
        run_command(f'python opendata_workflow.py download --theme {args.theme}')
        run_command(f'python opendata_workflow.py normalize_schema --theme {args.theme}')
        run_command(f'python opendata_workflow.py score --theme {args.theme}')
        return

    # 通常起動時の対話メニュー
    while True:
        print("\n" + "="*45)
        print(" 🛠️ TOKYO 23 SNIPER 運用メニュー")
        print("="*45)
        print("[1] 🏢 施設・街テーマのデータ更新")
        print("[2] 🧑‍🏫 職業・単元テーマのデータ更新")
        print("[3] 🚀 開発サーバー同時起動 (api.py & npm run dev)")
        print("[0] 👋 終了")
        print("="*45)

        choice = input("👉 実行したい番号を入力してください: ")

        if choice == "1":
            run_facility_themes()
        # elif choice == "2":
        #     run_occupation_themes()
        elif choice == "3":
            start_servers()
            break # サーバー起動後はメニューを抜ける（Ctrl+Cでスクリプト自体が終わるため）
        elif choice == "0":
            print("👋 終了します。お疲れ様でした！")
            break
        else:
            print("❌ 無効な入力です。")

if __name__ == "__main__":
    main()