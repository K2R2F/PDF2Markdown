# 実行ファイル配布に向けた点検と要件

2026-09-14。Context7からDocling・Streamlit・PyInstallerの公式資料を取得し、現在のソースと照合しました。今回完了したのは機能分割と点検です。実行ファイル、インストーラー、配布用ランタイムはまだ作成していません。

## 推奨する配布方式

Windows x64向けに、ランチャーEXE、専用Pythonランタイム、アプリ、必要ライブラリをインストーラーにまとめる方式を推奨します。利用者によるPythonの事前導入を不要にし、OCRの追加導入を専用ランタイム内で行える構成です。モデルは初回セットアップで取得し、オフライン用モデルパックも別途用意します。

「インストーラーが1つのEXE」と「全機能が単一のポータブルEXE」は異なります。まず前者を想定します。後者を必須にすると、大きなモデルやTorchの展開時間、更新、書き込み場所、追加OCR導入を再設計する必要があります。PyInstallerのonefileは起動時に一時ディレクトリへ展開します。[PyInstallerの動作方式](https://pyinstaller.org/en/stable/operating-mode.html)

## Context7との照合結果

Context7で参照したライブラリIDは `/docling-project/docling`、`/streamlit/docs`、`/websites/pyinstaller_en_stable` です。資料は最新版を含むため、インストール済みDocling 2.126.0・Streamlit 1.63.0のコードおよびテスト結果と区別して評価しています。PyInstallerはまだ導入・ビルドしていません。

| 優先度 | 現在の実装と問題 | 対応方針 |
| --- | --- | --- |
| 配布前必須 | `environment/installer.py` は `sys.executable -m pip` / `-c`、`environment/jobs.py` はPythonスクリプトを起動する。凍結後の `sys.executable` はアプリEXEであり、通常のPython引数では動かない | 専用Pythonの絶対パスを管理して実行。全体凍結を選ぶなら明示的なworkerコマンドと依存追加方式を再設計 |
| 配布前必須 | `environment/catalog.py` と `saving.py` はアプリの隣に書き込む。Program Filesでは権限不足、onefileでは一時展開先の消失が問題になる | 読み取りリソースと、ユーザー別設定・モデル・ログ・結果保存場所を分離 |
| 配布前必須 | `ui/result_panel.py` / `ui/batch_panel.py` の結果はsession_stateのみ | 設定を原子的に保存し、結果・履歴を永続化。再読み込みや再起動後に復元 |
| 配布前必須 | `environment/detection.py` のPythonパッケージreadyはメタデータ上の存在判定。バージョン不一致でもreadyで、モデル準備済みとは限らない | 未導入・版不一致・import失敗・モデル不足・使用可能を分ける。検証失敗状態を保持し、修復ボタンにつなぐ |
| 配布前必須 | `environment/jobs.py` のジョブ・ロックはプロセス内のみ。親が終了した場合の復旧がない | OSレベル排他、永続ジョブ状態、起動時の中断検知、子プロセスの終了・回収 |
| 配布前必須 | `core/converter.py` は画面と同じプロセス。Doclingの600秒設定は強制終了保証ではない | 独立ワーカー、キャンセル、実時間上限、メモリ制限、失敗PDFの再試行 |
| 配布前必須 | `core/ocr_options.py` はモデル配置・オフライン取得方針を指定しない | Docling・OCRのモデルを管理。初回準備の進捗、容量、再試行、モデル不足の表示 |
| 更新時必須 | `ui_ja.html` はStreamlit 1.63のDOM部品に依存 | バージョン固定とブラウザー回帰確認。更新時に翻訳漏れ・文書非改変を確認 |

凍結時の実行ファイルとリソースパスの意味は公式仕様に基づきます。`__file__` による同梱リソース読み取り自体は使用可能ですが、リソースの収録設定が別途必要です。[PyInstaller runtime information](https://pyinstaller.org/en/stable/runtime-information.html)

Streamlitのキャッシュされた変換器はセッション間で共有されるため、今回も共通の排他ロックを維持しました。session_stateはWebSocketに結び付き、ブラウザー再読み込み時に失われます。[Streamlit caching](https://github.com/streamlit/docs/blob/main/content/develop/concepts/architecture/caching.md)、[Session State](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state)

Doclingはレイアウト・表モデルなどを必要とし、`artifacts_path` または `DOCLING_ARTIFACTS_PATH` でローカル配置を指定できます。EasyOCRには別のモデル配置・ダウンロード設定があります。インストール済みのオプション定義でも `artifacts_path`、`model_storage_directory`、`download_enabled` を確認しています。[Docling advanced options](https://github.com/docling-project/docling/blob/main/docs/usage/advanced_options.md)、[Docling FAQ](https://github.com/docling-project/docling/blob/main/docs/faq/index.md)

## 配布までの機能一覧と受入条件

「一部」は既存機能を配布向けに補強する必要がある状態です。

| ID | 項目 | 現状 | 完了条件 |
| --- | --- | --- | --- |
| A01 | 機能単位のコード・テスト | 実装済み | UI・変換・入力・保存・環境管理を個別に変更可能 |
| A02 | Python不要のインストール | 未実装 | PythonのないWindows x64の標準ユーザーで起動 |
| A03 | 起動と終了 | 未実装 | 起動進捗、ヘルスチェック、ブラウザー表示、明示終了、子プロセス回収 |
| A04 | ポート競合・二重起動 | 未実装 | 空きポート選択、既存アプリの識別、重複インストールを防止 |
| A05 | 保存場所の分離 | 未実装 | 読取専用のインストール先でも動作。日本語・空白を含むユーザー名でも保存可能 |
| A06 | 設定の永続化 | 未実装 | 保存先・OCR・言語を再起動後復元。破損時の初期化・設定移行 |
| A07 | 環境検出と修復 | 一部 | 依存版、DLL/import、本体、言語、モデルを別判定。修復後に再検証 |
| A08 | モデル準備 | 未実装 | 初回ウィザード、進捗・容量確認、固定版/照合、途中失敗から再取得 |
| A09 | オフライン運用 | 未実装 | モデル・依存パックの入出力。ネット切断状態で実変換成功 |
| A10 | 入力方法 | 実装済み | 複数PDF、複数公開URL、ZIP。既存の容量・件数・公開IP制限を維持 |
| A11 | 通信設定と停止 | 一部 | DNSや読み込みを含む期限、キャンセル。必要に応じプロキシ・企業証明書の設定支援 |
| A12 | OCR設定と選定 | 一部 | 日英・英・中英、OCR自動/全頁/なし。代表資料で精度と時間を比較 |
| A13 | 表・画像出力 | 実装済み | 表の構造復元、画像埋め込み、UTF-8のMarkdownを維持 |
| A14 | バッチ制御 | 一部 | 件数・ページ進捗、キャンセル、失敗だけ再試行。大容量で画面応答を維持 |
| A15 | 保存 | 一部 | 1クリックの個別MD/全件ZIPと上書き防止を維持。保存先選択・フォルダーを開く・空き容量不足対応 |
| A16 | 結果・履歴・復旧 | 未実装 | 直前結果の復元、中断ジョブの識別、履歴削除・保管期限。入力PDFの保持方針を表示 |
| A17 | ログと診断 | 一部 | 起動・変換・環境ログ、ローテーション、診断ZIP、本文/認証情報の除外 |
| A18 | ローカルアクセス保護 | 一部 | ループバック限定、必要なローカル認証/起動識別、CORS/XSRF設定維持。意図せずLANへ公開しない |
| A19 | 日本語操作とヘルプ | 一部 | 初回設定・エラー復旧案内・終了・バージョン画面。DPI/キーボード操作確認 |
| A20 | 再現可能なビルド | 未実装 | 固定依存、ランタイム・静的リソース・DLLの収録、ビルド手順とCI、成果物のハッシュ |
| A21 | 配布条件 | 未実装 | Docling・OCR・モデル・ランタイムのライセンス/再配布条件確認、同梱表記・SBOM、署名方針 |
| A22 | 更新・修復・削除 | 未実装 | 処理中の更新を防止、失敗時ロールバック、設定移行、利用者の出力を削除しないアンインストール |
| A23 | 配布版の受入試験 | 未実装 | Windows対象版、標準権限、Pythonなし、オフライン、ディスク不足、通信失敗、二重起動、更新/復旧 |

## 実装順序

1. 今回の機能分割を基準に、ユーザー別パスと設定の永続化を追加。
2. 専用Pythonの実行経路、変換ワーカー、ジョブ保存・キャンセル・回収を実装。
3. 環境の詳細判定・修復、モデル準備とオフラインパックを実装。
4. ネイティブランチャー、起動終了管理、インストーラー、配布ビルドを追加。
5. クリーンPCで実変換と導入・更新・復旧を検証し、ライセンス表示とリリース成果物を確定。

既存の入力制限・公開IP検証・ZIP非展開・排他保存は維持します。PDF本文を外部AI APIへ送る構成はありません。日本語OCRの最高精度、RapidOCRの実推論、実機Tesseract導入、実行ファイルでの動作は今回の自動テストでは保証していません。EasyOCRの既定採用は導入性と言語対応に基づく暫定選定です。
