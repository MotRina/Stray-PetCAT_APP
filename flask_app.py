from flask import Flask, render_template, request, redirect, url_for, session
import csv
import os
import random

app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')



# usersディクショナリをメモリからCSVへ移行
def load_users():
    users = {}
    with open("/home/ojus/mysite/users.csv", "r") as file:
        reader = csv.reader(file)
        for row in reader:
            username, password, position, expertise = row
            users[username] = {
                "password": password,
                "position": position,
                "expertise": expertise
            }
    return users

users = load_users()

@app.route('/')
def index():
    # ログインしていない場合は新規ログインページへリダイレクト
    if 'username' not in session:
        return redirect(url_for('register'))

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    IMAGES_PATH = os.path.join(BASE_DIR, 'static', 'images')

    # staticフォルダ内の全写真を取得し、まだ表示されていない写真を選択
    photos = [f for f in os.listdir(IMAGES_PATH) if f not in session.get('seen_photos', []) and f != ".DS_Store"]

    # 全ての写真を見終わった場合は終了メッセージを表示
    if not photos:
        return render_template('all_photos_viewed.html')

    if 'current_photo' in session and session['current_photo'] not in session['seen_photos']:
        photo = session['current_photo']
    else:
        photo = random.choice(photos)
        session['current_photo'] = photo

        if 'seen_photos' not in session:
            session['seen_photos'] = [photo]
        else:
            seen_photos = session['seen_photos']
            seen_photos.append(photo)
            session['seen_photos'] = seen_photos


    total_photos = [f for f in os.listdir(IMAGES_PATH) if f != ".DS_Store"]
    total_photos_count = len(total_photos)

    # 残りの写真の割合を計算
    if 'seen_photos_count' in session:
        percentage = 100 * (session.get('seen_photos_count', 0) / total_photos_count)
    else:
        remaining_photos_count = len(photos)
        percentage = 100 - ((remaining_photos_count / total_photos_count) * 100)

    if percentage >= 100:
        return render_template('all_photos_viewed.html')

    return render_template('index.html', photo=photo, username=session['username'], percentage=percentage)



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        position = request.form['position']
        expertise = request.form['expertise']

        # ユーザーが既に存在する場合のチェック
        if username in users:
            error_message = "ユーザー名は既に存在します。"
            return render_template('register.html', error_message=error_message)

        # ユーザデータの保存（注意: 実際にはハッシュ化などの処理が必要）
        users[username] = {
            "password": password,
            "position": position,
            "expertise": expertise
        }

        # 保存したユーザデータをCSVファイルへ書き込み
        with open("/home/ojus/mysite/users.csv", "a") as file:
            writer = csv.writer(file)
            writer.writerow([username, password, position, expertise])

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if users.get(username) and users[username]['password'] == password:
            session['username'] = username

            # 進捗をロード
            with open("/home/ojus/mysite/progress.csv", "r") as file:
                reader = csv.reader(file)
                for row in reader:
                    if row[0] == session['username']:
                        session['seen_photos_count'] = int(row[1])
                        session['seen_photos'] = row[2].split(",") if len(row) > 2 else []
                        break
                    else:
                        session['seen_photos_count'] = 0
                        session['seen_photos'] = []

            # ユーザがログインした際に、そのユーザの「見た写真のリスト」をリセット
            session['seen_photos'] = []
            return redirect(url_for('index'))
        else:
            error = "ユーザ名またはパスワードが正しくありません。"

    return render_template('login.html', error=error)


@app.route('/classify/<photo>/<label>')
def classify(photo, label):
    session['seen_photos_count'] = session.get('seen_photos_count', 0) + 1

    photo_without_extension = photo.replace('.png', '')
    # 分類結果をCSVに保存
    with open("/home/ojus/mysite/db.csv", "a") as file:
        writer = csv.writer(file)
        writer.writerow([session['username'], photo_without_extension, label])

    # ユーザーの進捗を更新
    seen_photos_str = ",".join(session['seen_photos'])  # Seen photos are joined into a string
    with open("/home/ojus/mysite/progress.csv", "r") as file:
        reader = csv.reader(file)
        data = list(reader)
    for row in data:
        if row[0] == session['username']:
            row[1] = str(session['seen_photos_count'])
            row[2] = ",".join(session['seen_photos'])
            break
    else:
        data.append([session['username'], "1", photo])

    with open("/home/ojus/mysite/progress.csv", "w") as file:
        writer = csv.writer(file)
        writer.writerows(data)

    if 'current_photo' in session:
        del session['current_photo']

    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    with open("/home/ojus/mysite/progress.csv", "r") as file:
        reader = csv.reader(file)
        data = list(reader)
    for row in data:
        if row[0] == session['username']:
            row[1] = str(session.get('seen_photos_count', 0))
            row[2] = ",".join(session.get('seen_photos', []))
            break

    with open("/home/ojus/mysite/progress.csv", "w") as file:
        writer = csv.writer(file)
        writer.writerows(data)

    session.clear()
    return redirect(url_for('login'))



if __name__ == '__main__':
    app.run()

