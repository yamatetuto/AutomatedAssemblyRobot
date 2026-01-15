import configparser
import io

# 1. 設定の読み込み
config = configparser.ConfigParser()
config.optionxform = str # 大文字小文字を区別
file_path = 'SPLEBO-N.pos'
config.read(file_path)

# 2. データの編集（例：Item5を変更）
if 'Point' in config:
    # 変更したい値をセット
    # 例: Item1の値を変更
    config['Point']['Item1'] = '1,0,10,10,10,,,,,,0,change pos'

# 3. スペースを除去して保存する処理
output_path = 'SPLEBO-N.pos'

# 一時的なメモリバッファを作成
with io.StringIO() as buffer:
    # バッファに書き込み（この時点では "Key = Value" となっている）
    config.write(buffer)
    
    # バッファの中身を文字列として取得
    buffer_content = buffer.getvalue()

# 行ごとに処理して、最初の " = " だけを "=" に置換する
final_lines = []
for line in buffer_content.splitlines():
    # セクション名（[Position]など）以外の行で、" = " が含まれていれば置換
    if ' = ' in line and not line.startswith('['):
        # 最初の1回だけ置換することで、データの中身（コメント等）に含まれる "=" を守る
        clean_line = line.replace(' = ', '=', 1)
        final_lines.append(clean_line)
    else:
        final_lines.append(line)

# 4. 最終的なファイル書き出し
with open(output_path, 'w', encoding='utf-8') as f:
    # 改行コードで結合して書き込み
    f.write('\n'.join(final_lines))
    # 末尾に改行がないと一部の機器でエラーになる場合があるため念のため追加
    f.write('\n')

print(f"'{output_path}' にスペースなし形式で保存しました。")