from flask import Flask, request, redirect, send_file, render_template, abort, jsonify
import os
from threading import Thread
from Synthesia2midi import mp42midi
from apscheduler.schedulers.background import BackgroundScheduler
import time
from datetime import datetime, timedelta 
import sqlite3

# --------------------------------------------------------------------------------
# ログ用ファイル作成
# データベースに接続
conn = sqlite3.connect('site_data.db')
cursor = conn.cursor()

# テーブル作成（存在しない場合）
cursor.execute('''
CREATE TABLE IF NOT EXISTS site_data (
    date TEXT,
    site_name TEXT,
    access INTEGER,
    convert INTEGER,
    download INTEGER,
    PRIMARY KEY (date, site_name)
)
''')

# コミットして接続を閉じる
conn.commit()
conn.close()

# --------------------------------------------------------------------------------


def update_counts(site_name, access_type):
    if access_type not in ['access', 'convert', 'download']:
        raise ValueError("Invalid access_type. Must be 'access', 'convert', or 'download'.")

    # 現在の日付を取得
    today_date = datetime.now().strftime('%Y-%m-%d')

    # データベースに接続
    conn = sqlite3.connect('site_data.db')
    cursor = conn.cursor()

    # 既存のカウントを取得
    cursor.execute('''
    SELECT access, convert, download
    FROM site_data
    WHERE date = ? AND site_name = ?
    ''', (today_date, site_name))
    
    row = cursor.fetchone()

    # カウントを更新
    if row:
        access, convert, download = row
    else:
        access, convert, download = 0, 0, 0

    if access_type == 'access':
        access += 1
    elif access_type == 'convert':
        convert += 1
    elif access_type == 'download':
        download += 1

    # データを挿入または更新
    cursor.execute('''
    INSERT OR REPLACE INTO site_data (date, site_name, access, convert, download)
    VALUES (?, ?, ?, ?, ?)
    ''', (today_date, site_name, access, convert, download))

    # コミットして接続を閉じる
    conn.commit()
    conn.close()


app = Flask(__name__)

# アップロードされたファイルを保存するディレクトリ
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
PROCESSED_FOLDER = "processed"
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
PROGRESS_FILE = "progress.txt"

# --------------------------------------------------------------------------------
# スケジューラのセットアップ
scheduler = BackgroundScheduler()

# 定期的に実行するタスク
def delete_old_files():
    now = datetime.now()
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(file_path):
            creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
            if now - creation_time > timedelta(hours=24):
                os.remove(file_path)
                
    for filename in os.listdir(PROCESSED_FOLDER):
        file_path = os.path.join(PROCESSED_FOLDER, filename)
        if os.path.isfile(file_path):
            creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
            if now - creation_time > timedelta(hours=24):
                os.remove(file_path)
                
# スケジューラでタスクを毎時間実行
scheduler.add_job(delete_old_files, 'interval', hours=1)
scheduler.start()
# --------------------------------------------------------------------------------

@app.route('/')
def upload_form():
    update_counts("MIDI_converter", "access")
    return render_template('synthesia2midi.html')

@app.route('/synthesia2midi')
def upload_form_synthesia2score():
    update_counts("MIDI_converter", "access")
    return render_template('synthesia2midi.html')

@app.route('/synthesia2midi/upload', methods=['POST'])
def upload_file():
    update_counts("MIDI_converter", "convert")
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    
    filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filename)
            
    abs_upload_folder = os.path.join(app.root_path,app.config['UPLOAD_FOLDER'])
    abs_processed_folder = os.path.join(app.root_path,app.config['PROCESSED_FOLDER'])
    
    thread = Thread(target=mp42midi, args=(abs_upload_folder, file.filename, abs_processed_folder))
    thread.start()
            
    return jsonify({"file_name": file.filename}), 200

    
@app.route('/synthesia2midi/progress', methods=['GET'])
def get_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            progress = f.read()
        return jsonify({'progress': progress}), 200
    else:
        return jsonify({'progress': '0'}), 200
    

@app.route('/synthesia2midi/download', methods=['POST'])
def download():
    update_counts("MIDI_converter", "download")
    data = request.json  # JSON データを取得
    filename = data.get('filename') # /processed/....midi
    try:
        return send_file(filename, as_attachment=True)
    except FileNotFoundError:
        # ファイルが見つからない場合の処理
        return jsonify({"error": "File not found"}), 404

    except Exception as e:
        # その他の例外が発生した場合の処理
        return jsonify({"error": str(e)}), 500

@app.route('/synthesia2midi/list-files', methods=['GET'])
def list_files():
    directory = app.root_path
    files = os.listdir(directory)
    return jsonify({"files": files})

if __name__ == '__main__':
    # ディレクトリが存在しない場合は作成する
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(PROCESSED_FOLDER, exist_ok=True)
    try:
        app.run(debug=True)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()