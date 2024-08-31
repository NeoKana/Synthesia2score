import sqlite3
import os

def get_counts(site_name, date):
    # データベースに接続
    conn = sqlite3.connect('site_data.db')
    cursor = conn.cursor()

    # データを取得
    cursor.execute('''
    SELECT access, convert, download
    FROM site_data
    WHERE date = ? AND site_name = ?
    ''', (date, site_name))
    
    row = cursor.fetchone()
    conn.close()
    return row

# 使用例
counts = get_counts('MIDI_converter', '2024-08-25')
print(counts)