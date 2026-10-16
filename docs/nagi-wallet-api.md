# 凪Bot 残高・武器 API 契約

## 状態と配置

凪Botと武器Botは別々のReplitで動くため、ローカルの `pirate.db` ファイル自体は共有しません。凪Botだけが正本のSQLiteを開き、武器BotはHTTPS API経由で武器・所持金を参照／更新します。

Python版武器Botは再起動後も保持するため `data/pirate.db` にローカルミラーを保存します。これは表示・将来の機能向けのキャッシュであり、残高確認・強化可否・武器状態の正本ではありません。API応答が失敗したときにミラーから強化を許可したり、古い内容で正本を上書きしたりしてはいけません。

## SQLiteデータモデル（凪Bot側）

日時はISO 8601 UTC文字列で保存します。`users` は凪Botの既存テーブルを利用し、武器Bot用に重複作成しません。

```sql
CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  money INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS weapons (
  user_id TEXT PRIMARY KEY REFERENCES users(user_id),
  weapon TEXT NOT NULL,
  level INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1),
  attack INTEGER NOT NULL CHECK (attack >= 0),
  defense INTEGER NOT NULL CHECK (defense >= 0),
  accuracy INTEGER NOT NULL CHECK (accuracy BETWEEN 0 AND 100),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  exp INTEGER NOT NULL DEFAULT 0,
  boss_win INTEGER NOT NULL DEFAULT 0,
  pvp_win INTEGER NOT NULL DEFAULT 0,
  pvp_lose INTEGER NOT NULL DEFAULT 0,
  skill_count INTEGER NOT NULL DEFAULT 0
);
```

`weapons.user_id` が主キーなので、武器はDiscordユーザーごとに1つです。複数サーバーで別々の武器を持たせる仕様にする場合は `guild_id` を加え、主キーを `(guild_id, user_id)` に変更する必要があります。

武器BOTの `weapon_bot/config.py` に各武器の初期ステータスとレベルごとの上昇値を定義しています。大剣はLv1で攻撃10です。凪API側にも同じ武器ID・初期値・成長値を設定してください。APIが更新したステータスは、強化に失敗した場合は一切変えません。

### 強化費用・成功率

強化前のレベルを `L` とします。価格・成功率はAPI側で計算し、BOTから価格や成功率を受け取ってはいけません。

| 強化 | 費用 | 成功率 |
| --- | ---: | ---: |
| Lv1 → 2 | $1,000 | 100% |
| Lv2 → 3 | $2,500 | 95% |
| Lv3 → 4 | $5,000 | 90% |
| Lv4 → 5 | $8,000 | 85% |
| Lv5 → 6 | $12,000 | 80% |
| Lv6 → 7 | $16,000 | 75% |
| Lv7 → 8 | $20,000 | 70% |
| Lv8 → 9 | $24,000 | 65% |
| Lv9 → 10 | $28,000 | 60% |
| Lv10 → 11 | $32,000 | 55% |

- Lv5→6以降の費用: `12,000 + 4,000 × (L - 5)`
- 成功率: `max(30, 100 - 5 × (L - 1))` パーセント
- これらは武器BOTの `config.py` にも設定されています。凪APIの設定を変更する際は必ず同期してください。

## 共通API仕様

- Base URLは凪Botの管理者が決めます。以下では `https://nagi.example` を例として使います。
- 全リクエストをHTTPSにし、武器Botからのリクエストに `Authorization: Bearer <service-token>` を必須とします。
- Bearer tokenは両BotのSecretsに保存し、Discordの返信やログには出しません。
- JSONを送受信し、レスポンスには `Content-Type: application/json` を付けます。
- 更新系リクエストには `Idempotency-Key` を必須とします。武器BotはDiscord interaction IDを使用します。
- 同じキー・同じ内容の再送は最初の結果を返し、二重登録・二重課金を防ぎます。同じキーを異なる内容に使った場合は `409 idempotency_conflict` を返します。
- Idempotency-Keyの保存には、必要に応じて凪Bot側に専用テーブルを追加します。

## 鍛冶屋の情報を読む

`GET /api/v1/users/{userId}/forge`

成功時:

```json
{
  "weaponId": "greatsword",
  "weapon": "大剣",
  "level": 1,
  "attack": 10,
  "defense": 3,
  "accuracy": 75,
  "money": 35000,
  "nextUpgradeCost": 1000,
  "nextSuccessRate": 100,
  "createdAt": "2026-10-16T00:00:00Z",
  "updatedAt": "2026-10-16T00:00:00Z"
}
```

武器BOTは取得した攻撃力・防御力・命中率・所持金を一般ユーザー向けコマンドに表示しません。武器未所持は `404 weapon_not_found`、凪Bot未登録ユーザーは `404 user_not_found` です。

## 初回の武器選択を保存する

`POST /api/v1/users/{userId}/weapon`

Headers:

```text
Authorization: Bearer <service-token>
Idempotency-Key: <discord-interaction-id>
Content-Type: application/json
```

Request:

```json
{
  "weaponId": "greatsword"
}
```

選択可能な `weaponId`:

| ID | 表示名 |
| --- | --- |
| `greatsword` | 大剣 |
| `sword` | 片手剣 |
| `spear` | 槍 |
| `bow` | 弓 |
| `dual-blades` | 双剣 |
| `staff` | 杖 |

作成成功時は `201 Created` として `weaponId`, `weapon`, `level=1`, `attack`, `defense`, `accuracy`, `money`, `createdAt`, `updatedAt` を返します。APIは凪BotのSQLiteで対象ユーザーが `users` に存在することを確認し、`weapons` に一度だけ登録します。重複選択は `409 weapon_already_owned` とし、既存行を変更しません。初回選択はお金を消費しません。

武器BotはDiscord上で「本船員」ロールを確認してからAPIを呼びます。APIは認証済みの武器Botサービスからの要求のみ受け付けてください。

## 武器を強化し、凪を減算する

`POST /api/v1/users/{userId}/weapon/upgrade`

Request bodyは不要です。武器Botから費用・成功率・成功判定・ステータスを受け取らず、凪Botが現在の `level` と価格設定から費用と成功率を計算し、暗号学的に安全な乱数で成功判定します。

強化処理結果は成功・失敗のどちらでも `200 OK`。失敗でも費用は消費しますが、レベル・内部ステータスは一切変わりません。成功例:

```json
{
  "weaponId": "greatsword",
  "weapon": "大剣",
  "previousLevel": 1,
  "level": 2,
  "attack": 13,
  "defense": 4,
  "accuracy": 76,
  "cost": 1000,
  "successRate": 100,
  "success": true,
  "money": 34000,
  "nextUpgradeCost": 2500,
  "nextSuccessRate": 95,
  "createdAt": "2026-10-16T00:00:00Z",
  "updatedAt": "2026-10-16T00:01:00Z"
}
```

失敗例では `success: false`, `level: previousLevel` とし、`attack`, `defense`, `accuracy` も強化前と同じ値を返します。`money` は費用分減った残高です。`nextUpgradeCost` と `nextSuccessRate` は変わらない強化前レベルに対する次回値です。

凪Botは**同じSQLiteトランザクション内**で、`users.money` の確認・減算、成功時のみ `weapons.level` と内部ステータスの更新、`updated_at` の更新を行います。失敗時は残高だけ減算します。いずれかのDB処理が失敗したらすべてロールバックしてください。残高不足は `409 insufficient_funds` とし、マイナス残高を許可しません。

## 管理者用データ操作

BOT側ではDiscord Administrator権限を確認した後、以下を呼び出します。全更新系APIで認証と `Idempotency-Key` を必須にします。

- `PUT /api/v1/users/{userId}/weapon` — `{ "weaponId": "bow" }` で武器を管理者変更する。現在のレベル・内部ステータスはLv1に戻す。残高は変更しない。
- `DELETE /api/v1/users/{userId}/weapon` — 武器データを削除し、残高は保持する。成功時は空の武器状態と残高を返す。
- `PATCH /api/v1/users/{userId}/weapon/admin` — `level`, `attack`, `defense`, `accuracy`, `money` の指定フィールドのみ編集する。整数範囲をサーバー側でも検証する。

成功レスポンスは、`GET /forge` と同じ形式で最新状態を返します。武器リセットでもユーザーの凪残高は削除しません。

## エラー形式

```json
{
  "error": {
    "code": "insufficient_funds",
    "message": "残高が不足しています"
  }
}
```

主なHTTP status:

- `400 invalid_request` — 不正な入力
- `401 unauthorized` — サービス認証失敗
- `404 user_not_found` / `404 weapon_not_found` — 対象データなし
- `409 weapon_already_owned` / `409 insufficient_funds` / `409 idempotency_conflict` — 状態競合
- `422 upgrade_price_not_configured` — 強化価格未設定

## 安全要件と未確定事項

- SQLはパラメータ化し、ユーザーID・武器IDをSQL文へ文字列連結しません。
- お金と武器レベル／内部ステータスは同じSQLiteトランザクションで更新します。
- `money` が費用以上である条件を更新時にも確認し、同時実行でも二重使用や負の残高を許しません。
- Authorization header、認証情報、残高を含むrequest/response bodyをログに記録しません。
- `users.user_id` はDiscord IDです。武器はDiscordユーザーごとに1つで、ギルドごとには分けません。
- API URLとサービス認証トークンは運用時に設定します。API実装と稼働確認はこの契約を凪Bot側へ実装した後に行います。
