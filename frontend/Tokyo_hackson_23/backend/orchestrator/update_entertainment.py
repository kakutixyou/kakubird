
import subprocess
import time

def run_command(command):
    """コマンドを実行し、エラーがあれば停止する関数"""
    print(f"▶ 実行中: {command}")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"\n❌ エラーが発生しました。処理を中断します。")
        exit(1)
    print("✅ 完了\n")

def main():
    print("=" * 60)
    print("🎢 娯楽施設（entertainment）専用データ更新ツール")
    print("=" * 60)
    print("このスクリプトは東京都のサーバーへの負荷を最小限に抑え、")
    print("娯楽施設のデータ取得とアクセススコアの計算のみを実行します。\n")
    
    input("👉 準備ができたら Enter キーを押して開始してください...")
    print("\n")

    # 1. カタログからインポート
    csv_url = "https://data.storage.data.metro.tokyo.lg.jp/digitalservice/130001_open_data_list.csv"
    run_command(f'python opendata_workflow.py import_csv --theme entertainment --csv-url "{csv_url}"')
    time.sleep(1)

    # 2. ダウンロード
    run_command('python opendata_workflow.py download --theme entertainment')
    time.sleep(1)

    # 3. 施設の正規化（データベースでカウントできるようにする）
    run_command('python opendata_workflow.py normalize_schema --theme entertainment')
    time.sleep(1)

    # 4. 娯楽施設専用のアクセススコアを計算
    run_command('python opendata_workflow.py entertainment_score --theme entertainment')

    print("=" * 60)
    print("🎉 娯楽施設のデータ更新とスコア計算がすべて完了しました！")
    print("npm run dev で画面を確認してみてください。")
    print("=" * 60)

if __name__ == "__main__":
    main()