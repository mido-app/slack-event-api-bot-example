# 何をするボット？
Slackのチャンネルに投稿された日本語メッセージに  
不自然な日本語がないかチェックし、指摘するボットです。  
Event APIを用いたSlackボットのサンプルとして作成しました。  

# 使用方法
本ボットはAWS Lamda上で動作させる想定で作成しています。  
AWS Lamda上にzip化してアップロードするか、  
AWSのコンソール上でtypo-check-ot.pyの内容を  
そのままコピー&ペーストして利用することができます。  

一部のパラメータ（認証情報）は環境変数として設定します。  
以下の内容をAWS Lamdaの環境変数として設定してください。  

| 環境変数名 | 値 |
| --- | --- |
| SLACK_APP_AUTH_TOKEN | Slack API（https://api.slack.com）の認証トークンを指定します |
| SLACK_BOT_USER_ACCESS_TOKEN | Slack APIの「OAuth & 権限」のページに表示されるボットユーザの認証トークンを指定します |
| PROOF_READING_API_KEY | リクルートのProofreading API（https://a3rt.recruit-tech.co.jp/product/proofreadingAPI/）のAPIキーを指定します |

# その他
細かな使い方、ソースコードの解説はのちに記事にしますのでそちらをご覧ください。
