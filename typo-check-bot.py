# -*- coding: utf-8 -*-
import os
import json
import logging
import random
import urllib.request

# ログ設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handle_slack_event(slack_event: dict, context) -> str:
    """
    Slackからのイベントを受け取り、
    イベントに応じた処理を行います
    :param slack_event: Slackからのイベント情報
    :param context: Lambdaのランタイム情報を取得できるオブジェクト
    :return: Slackへの返答
    """

    # 受け取ったイベント情報をCloud Watchログに出力
    logging.info(json.dumps(slack_event))

    # SlackのEvent APIの呼び出し先にエンドポイントを登録する際、
    # 正しいエンドポイントかどうかの認証のため、
    # Slackからchallengeという項目にトークンが送られてくる
    # その場合、正しいエンドポイントであることを知らせるために
    # challengeの値を返却する必要がある
    if "challenge" in slack_event:
        return slack_event.get("challenge")

    # Slack以外からの不正な呼び出しでないかを
    # イベント情報に含まれるSlackアプリの認証トークンで確認する
    # （本来はLambdaが呼ばれる前にAPI Gatewayで設定するべきだと思う）
    if not is_valid_access(slack_event):
        return "AUTH_ERROR"

    # ボットによるイベントまたはメッセージ投稿イベント以外の場合反応させない
    # Slackには何かしらのレスポンスを返す必要があるのでOKと返す
    # （返さない場合、失敗とみなされて同じリクエストが何度か送られてくる）
    slack_event_detail: dict = slack_event.get("event")
    if is_bot(slack_event_detail) or not is_message_event(slack_event_detail):
        return "OK"

    # 誤字・脱字発見APIを呼び出す
    check_api_response: dict = call_check_sentence_api(slack_event_detail.get("text"))
    logger.info(json.dumps(check_api_response))

    # 誤字・脱字発見APIのレスポンスから
    # ボットに発言させる内容を決める
    message: str = create_message(check_api_response)
    logger.info(message)

    # Slackにメッセージを投稿する
    post_message_to_slack_channel(message, slack_event_detail.get("channel"))

    # メッセージの投稿とは別に、Event APIによるリクエストの結果として
    # Slackに何かしらのレスポンスを返す必要があるのでOKと返す
    # （返さない場合、失敗とみなされて同じリクエストが何度か送られてくる）
    return "OK"


def is_valid_access(slack_event: dict) -> bool:
    """
    イベント情報に含まれる認証トークンにより、
    Slack以外からのリクエストでないかを確認します
    :param slack_event: イベント情報
    :return: 認証成功でTrue
    """
    return slack_event.get("token") == os.environ["SLACK_APP_AUTH_TOKEN"]


def is_bot(slack_event_detail: dict) -> bool:
    """
    イベント詳細情報を受け取り、ボットによるイベントかどうか調べます
    :param slack_event_detail: Slackからのイベント情報
    :return: ボットならばTrue
    """
    return slack_event_detail.get("subtype") == "bot_message"


def is_message_event(slack_event_detail: dict) -> bool:
    """
    イベント詳細情報を受け取り、
    メッセージ投稿イベントであるかどうか調べます
    :param slack_event_detail: Slackからのイベント情報
    :return: メッセージ投稿イベントならばTrue
    """
    return slack_event_detail.get("type") == "message"


def call_check_sentence_api(sentence: str) -> dict:
    """
    リクルートのProofreading APIを利用してメッセージを校閲します
    :param sentence: 校閲対象メッセージ
    :return: 校閲結果
    """

    # リクエストURLを生成する
    # メッセージには日本語が含まれるためURLエンコードする
    params: dict = {
        "apikey": os.environ.get("PROOF_READING_API_KEY"),
        "sentence": sentence
    }
    encoded_params: str = urllib.parse.urlencode(params)
    url: str = "https://api.a3rt.recruit-tech.co.jp/proofreading/v1/typo?{0}".format(encoded_params)

    # APIをコールし、結果を返却する
    # 受け取った結果はUTF-8にデコードしたのち辞書化する
    res: str = urllib.request.urlopen(url).read().decode('utf-8')
    return json.loads(res)


def create_message(check_api_response: dict) -> str:
    """
    リクルートのProofreading APIのレスポンスから
    ボットが投稿するメッセージを生成します
    メッセージを投稿しない場合Noneを返します
    :param check_api_response: Proofreading APIのレスポンス
    :return: メッセージ or None
    """

    # ステータスが「正常応答（指摘あり）」以外の場合は返答なし
    if check_api_response.get("status") != 1:
        return None

    # あまりに細かい指摘を省くため、指摘内容から「a little unnatural(alertCode=0)」を排除
    # 排除した結果他に指摘がなければ返答なし
    except_little_natural: dict = [x for x in check_api_response.get("alerts") if x.get("alertCode") != 0]
    if except_little_natural.__len__() == 0:
        return None

    # 最も間違っている可能性が高い箇所への指摘を取り出す
    sorted_alert: dict = sorted(except_little_natural, key=lambda alert: alert.get("rankingScore"), reverse=True)
    high_score_alert: dict = sorted_alert[0]

    # メッセージを返却
    random_message_head: list[str] = [
        "怪しい日本語がありますね",
        "この日本語はおかしいかもしれませんね",
        "えっ、この日本語大丈夫ですか？",
    ]
    return "{0}\n{1}".format(random_message_head[random.randint(0, random_message_head.__len__()-1)], high_score_alert.get("checkedSentence"))


def post_message_to_slack_channel(message: str, channel: str):
    """
    Slackのチャンネルにメッセージを投稿します
    :param message: 投稿するメッセージ
    :param channel: 投稿先チャンネル名 or チャンネルID
    :return: なし
    """

    # Slackのchat.postMessage APIを利用して投稿する
    # ヘッダーにはコンテンツタイプとボット認証トークンを付与する
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Authorization ": "Bearer {0}".format(os.environ["SLACK_BOT_USER_ACCESS_TOKEN"])
    }
    data = {
        "token": os.environ["SLACK_APP_AUTH_TOKEN"],
        "channel": channel,
        "text": message,
        "username": "CC-Bot"
    }
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), method="POST", headers=headers)
    urllib.request.urlopen(req)
    return
