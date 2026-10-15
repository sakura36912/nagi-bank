# 凪Bot 残高・武器 API 契約案

## 状態

この文書は凪Bot側に実装してもらうためのAPI案です。まだ凪Botへの接続はありません。凪BotがAPIを実装した後、武器BotにAPIクライアントを追加します。

## 接続条件

- 凪Botと武器Botは別々のReplitで稼働できます。SQLiteファイルをReplit間で直接共有しません。
- 凪BotのAPIだけが、凪Bot自身のSQLiteデータベースへアクセスします。
- APIはHTTPSで公開し、武器Botのサーバーからだけ利用できるBearer認証を設定します。
- Bearer tokenは両BotのSecretsに保存し、Discordメッセージやログに出しません。
- リクエストの `guildId` / `userId` はDiscordのSnowflake IDを文字列で渡します。
- APIは `userId` を凪Botの `users` テーブルのDiscord ID列へ対応付けます。実際の列名は凪Bot側のスキーマに合わせます。

## 共通仕様

- Base URLは凪Botの管理者が決めます。以下では `https://nagi.example` を例として使います。
- 認証が必要な全リクエストに `Authorization: Bearer <service-token>` を付けます。
- JSONを送受信し、レスポンスには `Content-Type: application/json` を付けます。
- 更新系リクエストには `Idempotency-Key` を必須とします。武器BotはDiscord interaction IDを使用します。
- 同じキー・同じ内容の再送は、最初の処理結果を返し、残高やレベルを再度変更しません。同じキーを異なる内容で使った場合は `409 idempotency_conflict` を返します。
- 認証失敗は `401 unauthorized`、入力不正は `400 invalid_request` とします。

## 武器の所持状態を読む

`GET /api/v1/guilds/{guildId}/users/{userId}/weapon`

所持武器がある場合:

```json
{
  "weaponId": "greatsword",
  "level": 1
}
```

所持武器がない場合は `404 weapon_not_found` を返します。

## 初回の武器選択を保存する

`POST /api/v1/weapons/select`

Headers:

```text
Authorization: Bearer <service-token>
Idempotency-Key: <discord-interaction-id>
Content-Type: application/json
```

Request:

```json
{
  "guildId": "123456789012345678",
  "userId": "234567890123456789",
  "weaponId": "greatsword"
}
```

選択可能な `weaponId` は次の6種です。

| ID | 表示名 |
| --- | --- |
| `greatsword` | 大剣 |
| `sword` | 片手剣 |
| `spear` | 槍 |
| `bow` | 弓 |
| `dual-blades` | 双剣 |
| `staff` | 杖 |

作成成功時は `201 Created`:

```json
{
  "weaponId": "greatsword",
  "level": 1
}
```

選択状態は凪BotのSQLiteにある独立した `weapons` テーブルで管理します。少なくとも `guild_id`, `user_id`, `weapon_id`, `level` を保持し、`(guild_id, user_id)` に一意制約を付けます。重複選択は `409 weapon_already_owned` とし、既存行を変更しません。

武器BotはDiscord上で「本船員」ロールを確認してからAPIを呼びます。APIは信頼済みの武器Botサービスからの認証済み要求だけを受け付けてください。

## 武器を強化し、凪を減算する

`POST /api/v1/weapons/upgrade`

Request:

```json
{
  "guildId": "123456789012345678",
  "userId": "234567890123456789"
}
```

価格はAPI側で現在の武器レベルから決定します。Discordクライアントや武器Botから金額を受け取ってはいけません。価格ルールが未設定の場合は `422 upgrade_price_not_configured` を返し、残高・武器レベルのどちらも変更しません。

強化成功時は `200 OK`:

```json
{
  "weaponId": "greatsword",
  "previousLevel": 1,
  "level": 2,
  "cost": 100,
  "money": 900
}
```

凪Botは**同じSQLiteトランザクション内**で、所持武器の確認、`users.money` の残高確認と減算、`weapons.level` の加算を実施してください。いずれかが失敗したらすべてロールバックします。武器が未所持の場合は `404 weapon_not_found`、残高不足は `409 insufficient_funds` とし、どちらもデータを変更しません。

## 実装前に凪Bot側で確認する項目

- `users` テーブルでDiscordユーザーIDを特定する列名
- `users.money` の型と通貨が整数単位かどうか
- `weapons` テーブルの既存定義、または上記列と一意制約を追加できるか
- レベルごとの強化価格。価格が決まるまで強化エンドポイントは無効のままにします。
- 凪BotがHTTPS APIを提供できる公開URLと、武器Bot用のサービス認証方式

## 安全要件

- SQLはパラメータ化し、`guildId`、`userId`、`weaponId` をSQL文に文字列連結しません。
- 残高とレベルの更新は必ずSQLiteトランザクションで行います。
- `money` が不足していないことを条件付き更新で検査し、マイナス残高を許可しません。
- APIの認証情報、Authorization header、残高を含むrequest/response bodyをログに記録しません。
