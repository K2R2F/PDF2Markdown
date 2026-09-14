# 機能ごとの保守構成

2026-09-14。機能分割を実施。実行方法と保存形式は維持しています。

| ファイル | 担当する機能 |
| --- | --- |
| `app.py` | 画面の組み立てと起動入口 |
| `ui/theme.py` | ページ設定・日本語化リソース・見出し |
| `ui/settings_panel.py` | OCR、言語、保存先の設定画面 |
| `ui/input_panel.py` | ファイル・URL・ZIPの入力画面 |
| `ui/batch_panel.py` | バッチ実行の操作・進捗表示 |
| `ui/converter_cache.py` | Streamlitの変換器キャッシュ |
| `ui/result_panel.py` | 結果表示と保存操作 |
| `environment_ui.py` | 環境チェック・設定の画面 |
| `core/models.py` | 入力・変換設定・結果のデータ型 |
| `core/pdf_validation.py` | PDF検証、件数・容量制限、名前の正規化 |
| `core/zip_input.py` | ZIPからのPDF読み込み |
| `core/url_input.py` | 公開URLの検証とPDF取得 |
| `core/ocr_options.py` | DoclingのOCR・表・画像オプション |
| `core/converter.py` | Docling変換の実行と結果への変換 |
| `core/markdown_export.py` | 出力名の重複回避とレポート付きZIP生成 |
| `saving.py` | UTF-8ファイル保存・上書き防止 |
| `environment/catalog.py` | 検証済み依存バージョン・取得元・配置設定 |
| `environment/detection.py` | パッケージ・Tesseract・言語データの検出 |
| `environment/downloads.py` | ダウンロード・サイズ制限・ハッシュ照合 |
| `environment/process.py` | タイムアウト付き外部コマンド実行 |
| `environment/installer.py` | コンポーネントごとの導入手順 |
| `environment/jobs.py` | 設定ジョブ・ログ・子プロセスの管理 |
| `environment/locks.py` | 同一プロセス内の変換と導入の排他 |
| `environment/worker.py` | 設定用子プロセスのCLI処理 |
| `environment_support.py` | 設定CLIの入口と既存importの互換窓口 |
| `inputs.py`, `conversion.py` | 既存スクリプト向けの互換import |

新しい処理は担当モジュールに追加し、互換窓口に実装を戻さないでください。`core` と `environment` はStreamlitに依存しません。画面がそれらを呼び出します。`core/ocr_options.py` はTesseractの検出設定を、変換器は共通ロックを利用します。別プロセス化する際は、この境界を明示的な要求・結果の受け渡しに置き換えます。

テストのモックは、互換窓口ではなく実際に依存を参照するモジュールを対象にします。通常の起動入口 `app.py`、環境設定CLI `environment_support.py`、モデル検証用 `smoke_test.py` は変更していません。

## 検証

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
```

画面の順序・入力・個別エラー・保存をAppTestで検証し、URLアクセス制限、ZIP容量制限、環境検出・導入失敗、子プロセス入口と排他解除を個別に検証します。OCR品質と配布版の動作は別の受入試験です。

今回の検証結果: 分割後の既存25テストすべて成功。子プロセス入口・排他解除のテストを追加後、環境関連9テストすべて成功（テスト総数26件）。`pip check` 成功。`environment_support.py rapidocr` から実際の別プロセスimportが成功し、既存パッケージの再インストールは発生していません。Tesseract本体の未導入も検出しました。

## Gitへの登録

リモートは [K2R2F/PDF2Markdown](https://github.com/K2R2F/PDF2Markdown)、既定の開発ブランチは `main` です。`.gitignore` で仮想環境、入力・出力PDF、ランタイム、モデル、一時ファイル、秘密情報、ビルド成果物を除外します。コミット前には登録対象を確認してください。

今後は「機能＋対応テスト＋説明」を1つの変更単位にします。今回の分割を基準版とし、保存場所の分離、永続設定、ワーカー分離、モデル管理、ランチャー、配布ビルドを順に独立したコミットで進めます。完成した実行ファイルはソースの履歴に入れず、リリース成果物として扱います。

## 復元

変更前ファイルは `tmp/refactor-backup-20260914/` に保存済みです。`manifest.json` に元の絶対パス、バックアップの絶対パス、SHA-256を記録し、コピー時に一致を確認しました。復元する場合はアプリを終了し、manifestに記載した元の位置へファイルをコピーします。新設の `core/`、`environment/`、`ui/` は旧入口から参照されなくなるため、復元のために削除する必要はありません。ユーザーの `output/` と `.runtime/` は変更していません。
