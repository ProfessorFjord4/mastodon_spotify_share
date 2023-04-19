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

user = api_datalist[5]
playlist_id = api_datalist[6]

#日付
today = datetime.date.today()
month = str(today.month)
day = str(today.day)

# db接続
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

if len(list) > db_count:
    # dbから最新の曲のidを取得
    cur.execute("select id, track_name from music order by id desc limit 1")
    db_latest_song = cur.fetchone()

    for i in reversed(range(len(list))):
      if(list[i]['track']['name'] == db_latest_song[1]):
        latest_track = list[i+1]['track']
        break
      
    #曲のデータ
    track_name = latest_track['name']
    artist_name = latest_track['album']['artists'][0]['name']
    track_url = latest_track['external_urls']['spotify']
    
    toot_text = month + '/' + day + '\n' + track_name + ' - ' + artist_name + '\n' + track_url

    # リプライの形式で追加
    latest_data = api.status(db_latest_song[0])
    api.status_reply(latest_data, toot_text, visibility='unlisted')
     
    # 最新のトゥートを取得
    user_dict = api.account_verify_credentials()
    user_toots = api.account_statuses(user_dict['id'], limit=1)

    insert_text = "INSERT INTO music VALUES(" + str(user_toots[0]['id']) + ", '" + track_name + "', '" + artist_name + "', '" + str(today) + "')"
    cur.execute(insert_text)
    conn.commit()
    print('successfully tooted')
else:
    print('Playlist is not updated')

conn.close()