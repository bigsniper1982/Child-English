# 英语冒险岛（私人自用MVP）

面向小学生的KET/A2导向词汇与口语练习网站。当前主题为 **School Life**，包含30个词、听音选词、词块拼句、固定间隔复习、受控口语场景、小狐狸成长和家长进度页。

## 功能

- 家庭密码登录、CSRF与登录限速
- 每日5个新词；1/3/7/14天复习
- 浏览器英文朗读（Speech Synthesis）
- 浏览器语音识别，始终提供文字输入兜底
- 服务器不接收或保存原始录音
- SQLite保存词汇、游戏和口语结果
- PWA与移动端布局

## 本地运行

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('CHANGE-ME'))"
export SECRET_KEY='replace-with-a-random-secret'
export FAMILY_PASSWORD_HASH='paste-generated-scrypt-hash'
export SESSION_COOKIE_SECURE=0
venv/bin/flask --app 'app:create_app()' run --debug
```

访问 `http://127.0.0.1:5000`。

## 环境变量

| 变量 | 必需 | 说明 |
|---|---|---|
| `SECRET_KEY` | 是 | Flask随机密钥 |
| `FAMILY_PASSWORD_HASH` | 是 | Werkzeug scrypt密码哈希 |
| `DATABASE` | 否 | SQLite路径，默认`instance/app.db` |
| `SESSION_COOKIE_SECURE` | 生产必需 | HTTPS时设为`1` |
| `MAX_LOGIN_ATTEMPTS` | 否 | 默认5 |
| `LOGIN_LOCKOUT_SECONDS` | 否 | 默认300秒 |

## 测试

```bash
venv/bin/pytest -q
python3 -m compileall -q app
```

## 生产部署

示例文件：

- `deploy/kids-english-ai.service`
- `deploy/nginx.conf`

生产目录为 `/opt/kids-english-ai`，应用仅监听 `127.0.0.1:8010`，由Nginx负责TLS。SQLite目录应归`www-data`所有；代码应归`root`所有且不可被应用用户修改。

## 隐私

网站本身只接收浏览器识别后的文字和学习结果，不接收原始音频。浏览器的SpeechRecognition实现可能把语音交给浏览器供应商处理，具体取决于浏览器；不希望使用时可以只用文字输入。

## 内容边界

课程为原创A2/KET导向练习，并非Cambridge官方产品，也不提供官方考试评分。
