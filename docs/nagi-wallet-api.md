# 凪Bot 残高・武器 API 契約案

## 状態と配置

この文書は凪Bot側に実装してもらうためのAPI案です。凪Botと武器Botは別々のReplitで動くため、ローカルの `pirate.db` ファイル自体は共有しません。凪Botだけが自分のSQLiteを開き、武器BotはHTTPS API経由で武器・所持金を参照／更新します。

APIが実装されるまでは、武器Botは現在のPostgreSQLを使い続けます。`pirate.db` への直接接続に切り替えると、凪Botとは別の空ファイルを作る危険があるためです。

## SQLiteデータモデル（凪Bot側）

日時はISO 8601 UTC文字列で保存します。`users` は凪Botの既存テーブルを利用し、武器Bot用に重複作成しません。

```sql
CREATE TABLE users (
  user_id TEXT PRIMARY KEY,
  money INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE weapons (
  user_id TEXT PRIMARY KEY REFERENCES users(user_id),
  weapon TEXT NOT NULL,
  level INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1),
  attack INTEGER NOT NULL CHECK (attack >= 0),
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

初期選択の例は、大剣を `level=1`, `attack=10` とします。他の5種の初期攻撃力、およびレベルごとの強化費用・攻撃力上昇ルールは未指定のため、凪Bot側の設定前に確定が必要です。

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
  "money": 35000,
  "nextUpgradeCost": null
}
```

価格ルール未設定時は `nextUpgradeCost: null` を返します。武器未所持は `404 weapon_not_found`、凪Bot未登録ユーザーは `404 user_not_found` です。

武器Botの `/武器確認` は武器・Lv・攻撃力・固有スキルを表示し、`/鍛冶屋` はさらに所持金と次の強化費用を表示します。スキル名・説明は武器Bot側の6種の定義に対応させます。

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

作成成功時は `201 Created` として `weaponId`, `weapon`, `level=1`, `attack` を返します。APIは凪BotのSQLiteで対象ユーザーが `users` に存在することを確認し、`weapons` に一度だけ登録します。重複選択は `409 weapon_already_owned` とし、既存行を変更しません。

武器BotはDiscord上で「本船員」ロールを確認してからAPIを呼びます。APIは認証済みの武器Botサービスからの要求のみ受け付けてください。

## 武器を強化し、凪を減算する

`POST /api/v1/users/{userId}/weapon/upgrade`

Request bodyは不要です。武器Botから費用や攻撃力を受け取らず、凪Botが現在の `level` と価格設定から計算します。

強化成功時は `200 OK`。以下の攻撃力・費用・残高はレスポンス形式の説明用の仮値で、ゲーム内の価格や成長率を確定するものではありません。

```json
{
  "weaponId": "greatsword",
  "previousLevel": 1,
  "level": 2,
  "attack": 12,
  "cost": 100,
  "money": 34900
}
```

レベルごとの価格ルールが未設定の場合は `422 upgrade_price_not_configured` を返し、残高も武器データも変更しません。

凪Botは**同じSQLiteトランザクション内**で、`users.money` の確認・減算、`weapons.level` と `weapons.attack` の更新、`updated_at` の更新を行います。いずれかが失敗したらすべてロールバックしてください。残高不足は `409 insufficient_funds` とし、マイナス残高を許可しません。

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
- お金と武器レベル／攻撃力は同じSQLiteトランザクションで更新します。
- `money` が費用以上である条件を更新時にも確認し、同時実行でも二重使用や負の残高を許しません。
- Authorization header、認証情報、残高を含むrequest/response bodyをログに記録しません。
- 凪Bot側のAPI URL、`users.user_id` がDiscord IDであること、他5種の初期攻撃力、強化費用と攻撃力上昇式は未確定です。
