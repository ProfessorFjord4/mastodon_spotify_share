from mastodon import Mastodon
import datetime
import sqlite3
from apiclient.discovery import build

# apidata.txtにapiデータをテキストファイルとして保存している前提です
f = open('yt_apidata.txt', 'r')

api_datalist = f.readlines()

# 改行コードの処理
for i in range(len(api_datalist)):
    api_datalist[i] = api_datalist[i].rstrip('\n')
    
f.close()

# mastodonのapi認証
api = Mastodon(
    api_base_url  = 'https://mstdn.jp',
    client_id     = api_datalist[0], #Webでアプリ登録時に発行されたクライアントキー
    client_secret = api_datalist[1],  #Webでアプリ登録時に発行されたクライアントシークレット
    access_token  = api_datalist[2]  #Webでアプリ登録時に発行されたアクセストークン
)

# youtubeのapi認証
API_KEY = api_datalist[3]
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
youtube = build(
    YOUTUBE_API_SERVICE_NAME,
    YOUTUBE_API_VERSION,
    developerKey=API_KEY
)
playlist_id = api_datalist[4]

#日付
today = datetime.date.today()
month = str(today.month)
day = str(today.day)

# 再生リストの中の動画のidを全て取得
def getVideoIds(playlist_id, page_token):
  items_info = youtube.playlistItems().list(part='contentDetails', playlistId=playlist_id, maxResults=50, pageToken=page_token).execute()
  video_ids = list(map(lambda item: item['contentDetails']['videoId'], items_info['items']))
  if 'nextPageToken' in items_info:
    video_ids.extend(getVideoIds(playlist_id, items_info['nextPageToken']))
  return video_ids

# 特定のidの動画の情報を取得
def getVideoData(video_id):
  video_info = youtube.videos().list(part='snippet,statistics', id=video_id).execute()
  return video_info

yt_video_ids = getVideoIds(playlist_id, None)


# db接続
# dbは以下の文で定義されたテーブル1つで構成されています
# CREATE TABLE youtube(id integer, video_id text, video_title text, channel_title text, date text);
dbname = 'mastodon.db'
conn = sqlite3.connect(dbname)
cur = conn.cursor()

# dbから最新の曲のidを取得
cur.execute("select count(*) from youtube")
db_count = cur.fetchone()[0] - 1

# 新しい曲が追加されたとき
if len(yt_video_ids) > db_count:
    # dbから最新の曲のidを取得
    cur.execute("select * from youtube order by id desc limit 1")
    db_latest_video = cur.fetchone()

    # 現在投稿されているリストの最も下の動画を取得
    for i in reversed(range(len(yt_video_ids))):
      if(yt_video_ids[i] == db_latest_video[i]):
        latest_video_id = yt_video_ids[i+1]
        break
    
    latest_video_data = getVideoData(latest_video_id)['items'][0]
    #投稿する動画のデータ
    video_title = latest_video_data['snippet']['title']
    channel_title = latest_video_data['snippet']['channelTitle']
    video_id = latest_video_data['id']
    video_url = 'https://youtube.com/watch?v=' + video_id
    
    # トゥート文
    toot_text = month + '/' + day + '\n' + video_title + '\n' + channel_title + '\n' + video_url

    # リプライの形式で追加
    latest_data = api.status(db_latest_video[0])
    api.status_reply(latest_data, toot_text, visibility='unlisted')
    
    # 最新のトゥートを取得
    user_dict = api.account_verify_credentials()
    user_toots = api.account_statuses(user_dict['id'], limit=1)

    # リプライの形式で追加するためにDBに保存
    insert_text = "INSERT INTO youtube VALUES(" + str(user_toots[0]['id']) + ", '" + video_id + "', '" + video_title + "', '" + channel_title + "', '" + str(today) + "')"
    cur.execute(insert_text)
    conn.commit()
    print('successfully tooted')
else:
    print('Playlist is not updated')

conn.close()