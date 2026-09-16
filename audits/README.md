# 敵対的検証

この検証は、不正入力・通信切断・保存失敗・環境設定失敗を意図的に発生させます。テスト成功は指定した条件で期待結果を確認したという意味であり、製品完成や実行ファイル配布の承認ではありません。

## 判定ルール

- コマンドが終了し、終了コードと出力を確認するまで成功と記載しない。
- 中断・タイムアウト・実行エラー・未実施を成功に数えない。
- 失敗を `skip` や `expectedFailure` に変えて成功扱いにしない。
- 修正後は同じ期待条件で再検証する。修正後に成功した場合、最初の失敗記録の保持は必須ではない。
- モックで確認した動作を、実サービス・実モデル・実インストーラーで確認したと書かない。

## 再実行

```powershell
.\.venv\Scripts\python.exe -X utf8 audits/run.py adversarial -- .\.venv\Scripts\python.exe -X utf8 -m unittest discover -s audits -p test_adversarial.py -v
.\.venv\Scripts\python.exe -X utf8 audits/run.py regression -- .\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 audits/run.py dependencies -- .\.venv\Scripts\python.exe -X utf8 -m pip check
```

`run.py` は実行ごとに `evidence/` 内へ新規フォルダーを作り、開始時のソースハッシュ、コマンド、生出力、終了状態を記録します。既存記録を上書きしません。終了記録がない実行は中断または状態不明です。既定の180秒制限を超えた場合は `timed_out` として終了し、成功扱いにしません。この仕組みは監査用であり、アプリのジョブ永続化機能ではありません。

生ログはローカルに保持し、端末固有の絶対パスを含むためGitでは除外します。テストコードと検証報告はGitで管理します。

通常テストだけではこのフォルダーの19項目は実行されないため、上記の両テストコマンドを実行してください。

結果: [2026-09-16の検証報告](../docs/ADVERSARIAL_REVIEW_20260916.md)
