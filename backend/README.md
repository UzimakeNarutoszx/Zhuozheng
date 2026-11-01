# 拙政观景后端

独立 FastAPI + SQLAlchemy 服务，默认使用项目私有 SQLite 数据库 `data/garden.db`，不会连接或修改见闻的用户数据。SQLite 适用于本机和单实例部署；生产可通过 `DATABASE_URL` 使用独立数据库。

## 启动

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8011
```

健康检查：`GET /health`。交互接口文档：`/docs`。开发前端通过 Vite 的 `/api` 代理连接；生产反向代理将同源 `/api` 指向本服务。

默认 `SMS_PROVIDER=aliyun`，使用阿里云号码认证服务 DYPNS。配置 `ALIYUN_DYPNS_ACCESS_KEY_ID`、`ALIYUN_DYPNS_ACCESS_KEY_SECRET` 与 `ALIYUN_DYPNS_SIGN_NAME`；签名和账号权限需在阿里云控制台确认，注册/重置模板分别为 `100001` / `100003`。阿里云生成并核验六位随机验证码，五分钟有效，接口不返回验证码。发送失败不会记为已签发；上游异常只返回通用错误，避免泄露密钥或运营商信息。

仅本地测试时显式设置 `SMS_PROVIDER=local`，先请求发送验证码，再使用界面显示的 `SMS_DEV_CODE`（默认 `123456`）注册或找回密码。验证码按用途绑定、一次有效、五次输错失效。生产环境拒绝本地验证码，必须配置真实短信与 `SECRET_KEY`。没有配置 AI key 时问答返回 503 且不扣额度。

仅将已授权的 AI 和短信配置项按需填入本地 `.env`，不要复制整个配置文件或用户数据库；`.env` 权限应为 `0600`。`.env`、数据库、日志和私有自动生成 secret 都被 Git 忽略。手机号+密码登录、PBKDF2 密码哈希、HMAC Bearer token、7 天有效期与重置密码失效机制沿用见闻的行为。短信与登录频率限制保存在单进程内存中；多个实例需要共用限流存储后再部署。

## 接口

- `POST /api/v1/auth/send-sms`：`{phone,scene:"register"|"reset_password"}`。
- `POST /api/v1/auth/register`：`{phone,nickname,password,sms_code}`。
- `POST /api/v1/auth/login`：`{phone,password}`。
- `POST /api/v1/auth/forgot-password`：`{phone,new_password,sms_code}`。
- `GET /api/v1/profile/me`：资料及北京时间每日 AI 额度。
- `GET/POST /api/v1/profile/works`：作品列表/保存。
- `GET/PUT/DELETE /api/v1/profile/works/{id}`：单件作品。
- `POST /api/v1/profile/works/import`：`{works:[...]}`，相同 ID 保留云端版本，返回 `{imported,skipped,works}`。
- `GET /api/v1/content/ask/bootstrap`：公开欢迎语和推荐问题。
- `POST /api/v1/content/ask`：`{question,history?,method_id?}`，返回 `{answer,sources}`。
- `POST /api/v1/content/ask/stream`：同样的请求，返回 UTF-8 `text/plain` 流；首字节前故障返回非 2xx 并退额，之后断流由客户端显示中断，部分回答仍保存。
- `GET /api/v1/profile/ai-records?limit=20&before=<id>`：按时间倒序读取个人问答记录；limit 为 1–100（默认 100），before 用于继续读取更早记录。
- `DELETE /api/v1/profile/ai-records`：清空个人问答记录，不返还额度。

### 社区（作品先审后发，评论先发后审）

公开响应不含手机号，作者仅为 `{id,nickname}`。`profile/me` 返回 `role`（`user`/`admin`，由 `.env` 的 `ADMIN_PHONES` 逗号列表决定）。

- `POST /api/v1/profile/works/{id}/publish` → `{status:"pending",communityId}`，作品需已保存到账号；被驳回后可再次 publish。`POST .../unpublish` → `{status:"private"}`，删除公开图片，保留点赞和评论。编辑 pending/approved 作品会生成新图片并重新进入 pending；再次通过时保留首次公开时间。删除作品会一并删除其帖子、点赞、评论、举报和图片。
- `GET /api/v1/profile/works` 每项附加 `visibility`、`reviewStatus`（`private|pending|approved|rejected`）、`rejectReason`、`communityId`。
- `GET /api/v1/community/works?cursor=&method=&sort=latest|popular&limit=20` → `{items:[{id,title,methodId,thumbUrl,author,likeCount,commentCount,likedByMe,publishedAt}],nextCursor}`；无需登录，带 token 时返回 `likedByMe`。
- `GET /api/v1/community/works/{id}`：上述字段加 `imageUrl,note,frameId,reviewStatus`；仅 approved 公开，作者本人和管理员可看 pending。
- `POST|DELETE /api/v1/community/works/{id}/like` → `{liked,likeCount}`，幂等。
- `GET /api/v1/community/works/{id}/comments?cursor=` → `{items:[{id,content,author,createdAt,status}],nextCursor}`；`POST {content≤500}`；`DELETE /api/v1/community/comments/{cid}`（评论作者、作品作者、管理员）。命中敏感词的评论为 pending，只有作者本人可见。
- `POST /api/v1/community/reports {targetType:"work"|"comment",targetId,reason≤200}`。
- 管理员：`GET /api/v1/admin/queue?type=work|comment|report`；`POST /api/v1/admin/works/{id}/review {action:"approve"|"reject",reason?}`；`POST /api/v1/admin/comments/{cid}/review {action}`；`POST /api/v1/admin/reports/{rid}/resolve {action:"dismiss"|"remove"}`（remove：作品转为 rejected，评论转为 hidden；同一对象的未处理举报一并关闭）。同一用户对同一对象的重复举报不重复记录。
- `GET /api/v1/media/{thumb|full}/{key}.webp`：发布时生成的 WebP（最长边 480 / 1600），保存在 `MEDIA_DIR`（默认 `data/media`）。approved 为 `public, max-age=31536000, immutable`，审核中为 `private, max-age=60`；撤回后返回 404。其他接口仍为 `no-store`。
- 敏感词：`config.py` 内置一小组，可用 `SENSITIVE_WORDS` 逗号列表追加。
- 限流：点赞 60/分钟，评论 10/分钟，发布 20/天，举报 20/天。

问答页仅保留最近 7 组问答；“我的 → 问答记录”可分页查看全部历史。每个账号每天默认最多 20 次提问，按北京时间零点恢复；两种提问接口共用额度，并发请求也不能超额。未生成回答的失败请求退还额度，已生成部分内容的中断回答保留并计入额度。

除 bootstrap 和认证外均需 `Authorization: Bearer <access_token>`。所有响应设为 `Cache-Control: no-store`。问题最多 2000 字；历史最多 20 条，只接受 user/assistant，每条最多 4000 字。单张作品图最多 4 MB base64，接受 JPEG/PNG/WebP 并验证解码；可选 `sourceImageDataUrl` 用于保存压缩的可编辑原图。数据库仅保存该用户自己的作品与问答；客户端不能指定用户 ID。

## 验证

```bash
python -m unittest discover -s tests -v
```

测试使用临时数据库，覆盖验证码、登录、重置 token、作品隔离/去重、AI 退款、流式 UTF-8 与独立日额度。测试不调用真实短信或外部 AI。
