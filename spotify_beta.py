from mastodon import Mastodon
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import datetime
import sqlite3

# apidata.txtにapiデータをテキストファイルとして保存している前提です
f = open('apidata.txt', 'r')

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

# spotifyのapi認証
my_id = api_datalist[3] #client ID
my_secret = api_datalist[4] #client secret
ccm = SpotifyClientCredentials(client_id = my_id, client_secret = my_secret)
spotify = spotipy.Spotify(client_credentials_manager = ccm, language='ja')

user = api_datalist[5] #Spotifyのusername
playlist_id = api_datalist[6] #対象とするSpotifyプレイリストのid

#日付
today = datetime.date.today()
month = str(today.month)
day = str(today.day)

# db接続
# dbは以下の文で定義されたテーブル1つで構成されています
# CREATE TABLE music(id integer, track_name text, artist text, date text);
dbname = 'mastodon.db'
conn = sqlite3.connect(dbname)
cur = conn.cursor()

#プレイリストからデータを収集
playlist_data = spotify.user_playlist(user, playlist_id)

#プレイリストの中で、DBに無い、先頭の曲を取ってくる
list = playlist_data['tracks']['items']

# dbから最新の曲のidを取得
cur.execute("select count(*) from music")
db_count = cur.fetchone()[0] - 1

# 新しい曲が追加されたとき
if len(list) > db_count:
    # dbから最新の曲のidを取得
    cur.execute("select id, track_name from music order by id desc limit 1")
    db_latest_song = cur.fetchone()

    # 現在投稿されているリストの最も下の曲を取得
    for i in reversed(range(len(list))):
      if(list[i]['track']['name'] == db_latest_song[1]):
        latest_track = list[i+1]['track']
        break
      
    #投稿する曲のデータ
    track_name = latest_track['name']
    track_url = latest_track['external_urls']['spotify']
    
    artists_name = ''
    bool_first = True
    for item in latest_track['artists']:
      if bool_first:
        artists_name += item['name']
        bool_first = False
      else:
        artists_name += ',' + item['name']
    
    # トゥート文
    toot_text = month + '/' + day + '\n' + track_name + ' - ' + artists_name + '\n' + track_url

    # リプライの形式で追加
    latest_data = api.status(db_latest_song[0])
    api.status_reply(latest_data, toot_text, visibility='unlisted')
     
    # 最新のトゥートを取得
    user_dict = api.account_verify_credentials()
    user_toots = api.account_statuses(user_dict['id'], limit=1)

    # リプライの形式で追加するためにDBに保存
    insert_text = "INSERT INTO music VALUES(" + str(user_toots[0]['id']) + ", '" + track_name + "', '" + artist_name + "', '" + str(today) + "')"
    cur.execute(insert_text)
    conn.commit()
    print('successfully tooted')
else:
    print('Playlist is not updated')

conn.close()