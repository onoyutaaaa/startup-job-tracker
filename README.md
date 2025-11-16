# スタートアップ求人トラッカー

LayerX、SmartHR、HERPの求人情報を自動収集・表示するWebアプリケーションです。

## 主な機能

- **自動クローリング**: 3社の採用ページから求人情報を自動収集
- **毎日自動更新**: 毎日12時に自動的に求人情報を更新
- **検索機能**: 社名・職種名で求人を検索
- **フィルター機能**: 年収範囲で求人を絞り込み
- **特別セクション**:
  - 今日の新着求人
  - 昨日のクローズ求人
  - 年収1,000万円以上の求人

## 技術スタック

- **バックエンド**: FastAPI
- **クローリング**: BeautifulSoup4、Requests
- **データベース**: SQLite + SQLAlchemy
- **スケジューリング**: APScheduler
- **フロントエンド**: HTML/CSS/JavaScript (Vanilla)

## プロジェクト構造

```
startup-job-tracker/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPIアプリケーション
│   ├── database.py          # データベースモデル
│   ├── scraper.py           # クローリングロジック
│   ├── scheduler.py         # スケジューラー設定
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── app.js
│   └── templates/
│       └── index.html
├── requirements.txt
├── run.py
└── README.md
```

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. アプリケーションの起動

```bash
python run.py
```

または

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. アクセス

ブラウザで以下にアクセス:
```
http://localhost:8000
```

## API エンドポイント

### 求人取得
```
GET /api/jobs
```
パラメータ:
- `search`: 検索キーワード
- `company`: 会社名フィルター
- `salary_min`: 最低年収
- `salary_max`: 最高年収
- `limit`: 取得件数 (デフォルト: 100)
- `offset`: オフセット (デフォルト: 0)

### 今日の新着求人
```
GET /api/jobs/new-today
```

### 昨日のクローズ求人
```
GET /api/jobs/closed-yesterday
```

### 高年収求人
```
GET /api/jobs/high-salary?min_salary=10000000
```

### 統計情報
```
GET /api/stats
```

### 手動更新
```
POST /api/scrape
```

## 使用方法

### 1. 初回の求人データ取得

アプリケーション起動後、画面上の「今すぐ更新」ボタンをクリックして、初回の求人データを取得します。

### 2. 検索とフィルタリング

- **検索窓**: 社名や職種名でキーワード検索
- **会社フィルター**: 特定の会社の求人のみを表示
- **年収フィルター**: 希望の年収範囲で絞り込み

### 3. 特別セクション

- **今日の新着**: 本日追加された求人を表示
- **昨日のクローズ**: 昨日終了した求人を表示
- **年収1000万円以上**: 高年収の求人を表示

## 自動更新スケジュール

- **頻度**: 毎日1回
- **時刻**: 12:00 (正午)
- **動作**: 全社の求人情報を自動的に更新

## データベーススキーマ

### jobs テーブル

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | Integer | 主キー |
| company | String | 会社名 |
| title | String | 職種名 |
| salary_min | Float | 最低年収 |
| salary_max | Float | 最高年収 |
| url | String | 求人URL (ユニーク) |
| description | Text | 求人詳細 |
| location | String | 勤務地 |
| employment_type | String | 雇用形態 |
| created_at | DateTime | 作成日時 |
| updated_at | DateTime | 更新日時 |
| is_active | Boolean | アクティブフラグ |
| first_seen | DateTime | 初回取得日時 |
| last_seen | DateTime | 最終確認日時 |

## カスタマイズ

### クローリング対象の追加

`app/scraper.py` に新しいScraperクラスを追加:

```python
class NewCompanyScraper(JobScraper):
    def __init__(self):
        super().__init__()
        self.careers_url = "https://example.com/careers"

    def scrape(self) -> List[Dict]:
        # クローリングロジックを実装
        pass
```

そして `scrape_all_jobs()` 関数に追加:

```python
def scrape_all_jobs() -> List[Dict]:
    scrapers = [
        LayerXScraper(),
        SmartHRScraper(),
        HERPScraper(),
        NewCompanyScraper()  # 追加
    ]
    # ...
```

### スケジュール変更

`app/scheduler.py` のCronTriggerを変更:

```python
# 例: 毎日午前9時に変更
scheduler.add_job(
    update_jobs,
    trigger=CronTrigger(hour=9, minute=0),
    # ...
)
```

## 注意事項

### クローリングについて

- 各企業の採用ページの構造は変更される可能性があります
- 実際の運用前に、各ScraperクラスのHTMLセレクタを最新のページ構造に合わせて調整する必要があります
- 過度なアクセスを避けるため、適切な間隔でクローリングを実行してください
- robots.txtを確認し、クローリングが許可されていることを確認してください

### 本番環境での使用

本番環境で使用する場合は、以下を推奨します:

1. **環境変数の使用**: データベースURLやAPIキーを環境変数で管理
2. **ログ設定**: より詳細なログ設定
3. **エラーハンドリング**: より堅牢なエラーハンドリング
4. **セキュリティ**: CORS設定、認証の追加
5. **パフォーマンス**: キャッシュ、データベースインデックスの最適化

## トラブルシューティング

### 求人が取得できない

1. インターネット接続を確認
2. 各企業の採用ページが変更されていないか確認
3. `app/scraper.py` のHTMLセレクタを最新のページ構造に合わせて更新

### データベースエラー

```bash
# データベースファイルを削除して再作成
rm jobs.db
python run.py
```

## ライセンス

MIT License

## 開発者

このプロジェクトは、スタートアップの求人情報を効率的に収集・管理するために開発されました。
