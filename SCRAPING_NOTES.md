# Webスクレイピングの現状と課題

## 実装済みの改善

### 1. 強化されたHTTPヘッダー
- 本物のブラウザに近いUser-Agent
- Accept、Accept-Language、Sec-Fetch-*などの完全なヘッダー
- セッション管理による効率的な接続

### 2. リトライメカニズム
- urllib3.Retryによる自動リトライ
- 429, 500, 502, 503, 504エラーに対応
- 403エラー時の代替ヘッダーフォールバック

### 3. プラットフォーム別スクレイパー
- **TalentioScraper**: API優先、HTMLフォールバック
  - 対象: LayerX, 10X, hacomono
- **HERPCareersScraper**: HERP Careers platform用
  - 対象: HERP, Nstock, Stract, SecureNavi, IVRy
- **個別スクレイパー**: SmartHR, Nealle, Shippio

### 4. Seleniumオプション
- `app/selenium_scraper.py`で実装済み
- ChromeDriver必須（環境により未インストール）

## 現在の課題

### Bot対策による403 Forbidden
ほとんどの採用サイトで強力なbot対策が実装されており、以下のエラーが発生：

```
403 Client Error: Forbidden
```

**影響を受けるサイト:**
- Talentio platform (LayerX, 10X, hacomono)
- HERP Careers (HERP, Nstock, Stract, SecureNavi, IVRy)
- Wantedly (すべてのドメイン: sg, www, en-jp)
- SmartHR, Nealle, Shippio 等

### テスト結果サマリー

| プラットフォーム | 対象企業 | 結果 | 備考 |
|---------|---------|------|------|
| Talentio | LayerX, 10X, hacomono | ❌ 403 Forbidden | API, HTML両方ブロック |
| HERP Careers | HERP, Nstock, Stract, SecureNavi, IVRy | ❌ 403 Forbidden | 全ページブロック |
| Wantedly | LayerX, SmartHR, HERP 他 | ❌ 403 Forbidden | 全ドメイン試行済 |
| 独自サイト | SmartHR, Nealle, Shippio | ❌ 403 Forbidden | 個別サイトもブロック |

## 実用的な代替アプローチ

### オプション1: 手動データ入力機能を追加
**推奨度: ★★★★★**

管理画面を作成し、手動で求人URLを追加できるようにする。

**メリット:**
- 確実に動作
- データの品質をコントロール可能
- 法的リスクなし

**実装例:**
```python
@app.post("/api/jobs/manual")
async def add_manual_job(job_data: JobCreate, db: Session = Depends(get_db)):
    """手動で求人を追加"""
    new_job = Job(**job_data.dict())
    db.add(new_job)
    db.commit()
    return new_job
```

### オプション2: Selenium + ChromeDriver
**推奨度: ★★★☆☆**

完全なブラウザエミュレーションでJavaScriptを実行。

**前提条件:**
```bash
apt-get install chromium-browser chromium-chromedriver
```

**使用方法:**
```python
from app.selenium_scraper import SeleniumLayerXScraper
scraper = SeleniumLayerXScraper(headless=True)
jobs = scraper.scrape()
```

**デメリット:**
- リソース消費が大きい
- 実行時間が長い
- 環境依存性が高い

### オプション3: 公式APIの使用
**推奨度: ★★★★☆**

各社が提供する公式求人APIを使用（利用可能な場合）。

**調査が必要:**
- 各企業のAPI公開状況
- APIキーの取得方法
- レート制限

### オプション4: Wantedlyなどのプラットフォーム
**推奨度: ★★★★☆**

企業独自サイトではなく、求人プラットフォームからスクレイピング。

**メリット:**
- より寛容なbot対策
- 統一されたデータ構造
- 複数企業の求人を一度に取得可能

**対象プラットフォーム:**
- Wantedly
- Green
- Findy

### オプション5: RSS/Atom Feeds
**推奨度: ★★★☆☆**

一部の企業がRSS/Atom feedsを提供している場合、それを使用。

**メリット:**
- 公式に提供されているため法的に安全
- 構造化されたデータ
- スクレイピング不要

## 推奨される実装戦略

### フェーズ1: 手動入力機能（即座に実装可能）
1. 管理画面で求人URLを手動追加
2. 基本情報（タイトル、URL、年収）を入力
3. データベースに保存

### フェーズ2: Selenium統合（オプション）
1. ChromeDriverがインストール済みの環境で動作
2. 夜間バッチで自動実行
3. 失敗時は手動入力にフォールバック

### フェーズ3: 公式API統合（長期的）
1. 各社に公式API提供を確認
2. 利用可能なものから順次統合

## robots.txtの確認

スクレイピング前に必ず確認すべきファイル：

- https://jobs.layerx.co.jp/robots.txt
- https://smarthr.co.jp/robots.txt
- https://herp.careers/robots.txt

**User-agent: * Disallow: /** の場合はスクレイピング禁止。

## 法的考慮事項

Webスクレイピングには以下のリスクがあります：

1. **利用規約違反**: 多くのサイトでスクレイピングを禁止
2. **著作権侵害**: コンテンツの無断複製
3. **偽計業務妨害**: 過度なアクセスでサーバーに負荷

**推奨:**
- 企業に直接連絡してデータ提供を依頼
- 公式APIの使用
- 手動データ入力

## まとめ

現実的には、**手動データ入力機能の追加**が最も確実で法的にも安全です。

自動化が必要な場合は：
1. 公式APIの使用を優先
2. robots.txtを確認
3. Seleniumを慎重に使用（適切な間隔を空ける）
4. 企業に許可を得る
