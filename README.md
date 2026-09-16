# PDF → Markdown

DoclingでPDFをまとめてMarkdownに変換する、日本語のローカルWebアプリです。UIはStreamlit、変換は同じPythonプロセスで行います。

標準メニュー（再実行・自動再実行・キャッシュ消去・印刷・画面録画）、アップロード表示、補助ラベルも日本語化しています。`ui_ja.html` がStreamlit 1.63のUI部品だけを対象に表示文字列を置き換えます。変換文書の本文は変更しません。Streamlit更新時は標準部品の表示を再確認してください。

## 起動

Python 3.12（推奨）で、このフォルダーから実行してください。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\start.ps1
```

検証環境と同じ間接依存バージョンまで揃える場合は、`requirements.txt` の代わりに `requirements.lock.txt` を使用してください。ロックファイルはWindows / Python 3.12で生成しています。

ブラウザーで http://localhost:8501 を開きます。PowerShellのスクリプト実行が制限されている場合は、次のコマンドを直接実行してください。

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

初回はDoclingのレイアウト・表モデルとOCRモデルをダウンロードします。ネットワークとディスク空き容量が必要で、初回は数分以上かかる場合があります。以後、モデルキャッシュを再利用します。PDF本文を外部AI APIへ送る処理はありません。URL入力時には対象のWebサイトへアクセスします。

## 使い方

1. 「ファイル」で複数PDFを追加するか、「URL」に直接URLを1行ずつ入力するか、「ZIP」でPDF入りZIPを選びます。
2. サイドバーでOCR・言語・表復元・画像埋め込みを選びます。
3. 「Markdownに変換」を押します。各PDFを順番に処理し、個別の失敗は残りの変換を妨げません。
4. 結果一覧の「Markdownを保存」または「すべてZIPで保存」を1回押すと、サイドバーの保存先へ直接保存します。確認ダイアログは出ません。既定の保存先はプロジェクト内の `output` フォルダーで、画面から変更できます（セッション中保持）。同名の既存ファイルは上書きせず、連番を付けます。成功時は保存済みの絶対パスを表示します。結果を開くとMarkdownソースを確認できます。ZIPの `manifest.json` に使用設定・処理時間・状態・エラーを収録します。

一度に30件、PDF1件100 MB、合計300 MBまで。ZIP自体は100 MBまでで、展開後にも上限を適用します。ページ上限は標準200ページ、画面で変更できます。ページ数超過は失敗として扱い、黙って切り捨てません。変換のタイムアウト設定は1PDF600秒です（Doclingによる監視であり、OSプロセスの強制終了ではありません）。

公開HTTP(S) URL、拡張子のないPDF URL、最大5回のリダイレクトに対応します。認証・Cookie・共有ページからのスクレイピング・社内IPへのアクセスは非対応です。必要なPDFはブラウザーで取得し、ファイル入力を使ってください。URLの重複行はまとめます。URL取得失敗は入力順の「URL N」で報告し、署名付きURL自体をレポートに残しません。

ZIPのPDFはサブフォルダーも読み込みます。PDF以外は無視し、ファイルシステムには展開しません。同名の出力には連番を付けます。画像埋め込みを無効にすると画像位置はプレースホルダーとなり、有効にするとBase64入りMarkdownを生成します。表示対応は利用するMarkdownビューアによります。

## 環境チェック・インストール支援

画面下部の「環境チェック・インストール支援」に、Docling、EasyOCR、RapidOCR / ONNX Runtime、Tesseractの導入状態とバージョンを表示します。

- 「インストール・設定」: 不足パッケージを使用中の仮想環境へ導入し、別プロセスで読み込みを確認します。
- 「実行確認・設定」: 導入済みパッケージを変更せずに読み込みを確認します。Tesseractは本体の起動と言語データも確認します。
- 「不足分をまとめてインストール・設定」: 全項目を順番に処理します。途中の項目が失敗しても残りを確認し、最後に失敗を報告します。
- 「状態を再チェック」: 外部でインストールした後などに検出結果を更新します。

Tesseractの自動導入はWindows x64に対応します。UB Mannheim配布の5.4.0.20240606版を取得し、Microsoft winget公式リポジトリー掲載のSHA-256と照合してから実行します。本体の保存先は `.runtime/tesseract`、言語データは `.runtime/tessdata` です。既存の本体が見つかれば再利用します。英語 `eng`、日本語 `jpn`、簡体字 `chi_sim`、向き検出 `osd` のデータをTesseract公式リポジトリーから取得し、実行ファイルとデータディレクトリーをDoclingへ直接渡します。システムPATHの手動設定は不要です。Windowsの確認が表示された場合は操作が必要です。

インストールは背景プロセスで実行し、ログを画面に自動表示するとともに `.runtime/setup-*.log` へ保存します。同じアプリ内の変換とインストールは直列化します。ブラウザーを閉じてもアプリ本体が動いていれば処理を続けますが、環境設定中はアプリ本体を終了・再起動しないでください。パッケージを新規導入した後、読み込み済みの依存ライブラリーの反映に再起動が必要になる場合があります。その場合は変換結果を保存してから再起動してください。OCRの推論モデルはパッケージの導入状態とは別で、初回変換時にダウンロードされます。

`start.ps1` は仮想環境がなければ作成し、画面起動に必要なStreamlitがなければ導入します。Python自体はあらかじめインストールしてください。Docling等がなくても画面を起動して支援パネルから導入できます。

配布元・照合元:

- [UB Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
- [Microsoft wingetのインストーラーマニフェスト](https://github.com/microsoft/winget-pkgs/blob/master/manifests/u/UB-Mannheim/TesseractOCR/5.4.0.20240606/UB-Mannheim.TesseractOCR.installer.yaml)
- [Tesseract公式言語データ](https://github.com/tesseract-ocr/tessdata_fast)

## OCRの選定

**日本語＋英語が混在する通常の印刷文書を想定した既定値はEasyOCRです。** Windows上でpipから導入でき、日本語・英語を明示してDoclingから使えるため、導入の容易さと言語対応を優先しました。実文書の比較評価はまだ行っておらず、最高精度と断定する選定ではありません。

| エンジン／設定 | このアプリでの用途 | 留意点 |
| --- | --- | --- |
| EasyOCR（既定） | 日本語＋英語の混在文書。`ja,en` を指定 | CPUでも動作。処理時間・縦書き・低解像度原稿の品質は実物で確認 |
| RapidOCR / ONNX Runtime | 主言語別モデルで比較する候補 | 日本語は `japan`、英語は `en`、簡体字は `ch`。認識モデルは1言語分を選択。実測速度の優位性は未検証 |
| Tesseract CLI | 既存のTesseract環境や学習データを活用 | 本体と言語データが必要。環境支援パネルから導入すればPATHの手動登録は不要 |
| OCRなし | 選択・コピーできる文字情報を持つPDF | 余分なOCRを避ける。画像化された文字は認識しない |

「必要な領域にOCR」はDoclingの標準判定を使います。「全ページにOCR」はスキャン原稿や埋め込み文字情報が壊れた文書を試す設定です。表の構造復元はDoclingのTableFormer Accurateを使用し、OCRエンジンだけで表品質が決まるわけではありません。

最終的な最適エンジンを決めるには、実際の日本語・日英混在・表・スキャンを含む代表的な10〜20ページを各エンジンで変換し、文字誤り率、読み順、表のセル対応、所要時間を比較してください。手書きや複雑な縦書きを保証するものではありません。

公式情報（2026-09-11確認）:

- [Docling OCR対応・言語指定](https://docling-project.github.io/docling/concepts/OCR/)
- [EasyOCRの利用方法と言語対応](https://github.com/JaidedAI/EasyOCR)
- [Doclingの変換オプション](https://docling-project.github.io/docling/reference/pipeline_options/)
- [Doclingのインストール](https://docling-project.github.io/docling/getting_started/installation/)

## 検証と構成

2026-09-16にContext7を併用した敵対的検証を実施し、再現した9項目を修正しました。修正後は既存26テスト・敵対的検証19テストが成功しています。未解決のプロセス管理・時間制限・永続化と未検証範囲は [検証報告](docs/ADVERSARIAL_REVIEW_20260916.md) を参照してください。配布版の完成判定ではありません。再検証では [監査用コマンド](audits/README.md) の両テストを実行してください。

2026-09-11、Windows / Python 3.12.14で以下を確認しました。

- 自動テスト25件成功（UIでのURLバッチ入力と個別失敗、入力上限、ZIP、OCR設定、ボタン1回でのMarkdown／ZIP実保存、既存ファイルの保護、依存関係の不足検出、インストーラー照合、不足時の導入フローを含む）。
- `pip check` 成功。
- W3Cの公開 [サンプルPDF](https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf) をURL経由で取得。
- EasyOCRの日本語＋英語設定・全ページOCRで `## Dummy PDF file` を取得。1ページ、初回モデル準備込み157.59秒。日本語本文の認識精度やエンジン間の比較性能を示す数値ではありません。
- ブラウザーから同じ公開URLを標準OCR設定で変換し、完了1件・失敗0件、Markdown本文と個別／ZIP保存ボタンを確認。モデル準備後の総処理時間は約2.3秒でした（この単純な1ページのみの結果）。
- RapidOCRの設定生成は確認済みですが、追加モデル取得の実行が自動承認レビューの利用上限で拒否されたため、実変換は未検証です。Tesseract本体はこの環境には導入していません。
- 環境支援ボタンからRapidOCR / ONNX Runtimeの別プロセス読み込みとログ出力を確認しました。Tesseractの新規導入フローは通信・インストーラー実行を置き換えたテストで検証しており、この環境で本体インストーラーを実行した結果ではありません。

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

実モデルの確認は、用意したPDFを指定して次のように実行できます。初回はモデルをダウンロードします。`--expect` はそのPDFに含まれる期待文字列に置き換えてください。

```powershell
.\.venv\Scripts\python.exe smoke_test.py path\to\sample.pdf --expect "期待する文字列"
```

- `app.py`: 画面を組み立てる起動入口
- `ui/`: 設定、入力、バッチ進捗、変換器キャッシュ、結果・保存操作を機能別に分割
- `core/`: データ型、PDF検証、ZIP読込、URL取得、OCR設定、変換、Markdown/ZIP生成
- `environment/`: 環境検出、ダウンロード、導入、外部コマンド、設定ジョブを機能別に分割
- `inputs.py` / `conversion.py`: 既存スクリプト用の互換import
- `environment_support.py`: 環境設定CLIの入口。`environment_ui.py` は環境支援画面
- `saving.py`: ローカルフォルダーへの直接保存、UTF-8書き出し、既存ファイルとの衝突回避。保存先はアプリが動作しているPC上のフォルダーです。
- `tests/`: 入力上限・不正入力・URL制限・ZIP出力・変換失敗の分離・UIの検証。モデル推論自体の品質テストは含みません。

個人用のローカルアプリです。セッション中の入力・出力はメモリーに保持し、変換結果を共有DBに永続化しません。モデルはディスクキャッシュに保存されます。複数PDFはメモリー使用量を抑えるため逐次変換し、同じ変換器への呼び出しはロックで直列化します。設定変更により別の変換器が作られるため、複数ユーザー向けのリソース制御や認証、ジョブキュー、再起動後の復旧、実行中PDFのキャンセルは未実装です。ネットワークへ公開する用途は追加実装が必要です。

2026-09-14に機能別のモジュール分割を実施しました。変更前のファイルは `tmp/refactor-backup-20260914/` にSHA-256照合済みで保存しています。配置と復元方法は [機能別構成](docs/ARCHITECTURE.md) を参照してください。

実行ファイル化に必要な機能、Context7による公式資料との照合結果、実装順序は [実行ファイル配布の要件](docs/EXE_READINESS.md) に整理しています。現在はソースから起動する版です。配布用EXEはまだ生成していません。ソースは [K2R2F/PDF2Markdown](https://github.com/K2R2F/PDF2Markdown) で管理します。
