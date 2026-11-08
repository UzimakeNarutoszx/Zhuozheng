import base64
import io
import json
import time
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from PIL import Image, ImageOps
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import settings
from .db import Comment, Favorite, Like, Post, Report, User, Work, get_db
from .deps import admin_user, current_user, is_admin, optional_user
from .schemas import CommentRequest, ReportRequest, ResolveRequest, ReviewRequest
from .security import limiter
from .moderation import comment_is_safe

router = APIRouter()
METHODS = {'frame', 'borrow', 'opposition', 'leak', 'screen'}
MEDIA_SIZES = {'thumb': 480, 'full': 1600}


# ---------- media ----------

def media_path(kind, key):
    return settings.media_dir / kind / f'{key}.webp'


def media_url(kind, key):
    return f'/api/v1/media/{kind}/{key}.webp' if key else ''


def remove_media(key):
    for kind in MEDIA_SIZES:
        if key:
            media_path(kind, key).unlink(missing_ok=True)


def write_media(data_url):
    try:
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(base64.b64decode(data_url.partition(',')[2]))))
        image = image.convert('RGBA' if 'A' in image.getbands() else 'RGB')
    except Exception:
        raise HTTPException(400, '作品图片无法读取，请重新保存后再发布') from None
    key = uuid.uuid4().hex
    for kind, size in MEDIA_SIZES.items():
        copy = image.copy()
        copy.thumbnail((size, size) if kind == 'full' else (size, size * 4))
        path = media_path(kind, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        copy.save(path, 'WEBP', quality=82 if kind == 'full' else 76, method=4)
    return key


@router.get('/api/v1/media/{kind}/{name}')
def media(kind: str, name: str, viewer: User | None = Depends(optional_user), db: Session = Depends(get_db)):
    key = name.removesuffix('.webp')
    if kind not in MEDIA_SIZES or not name.endswith('.webp') or len(key) != 32 or not key.isalnum():
        raise HTTPException(404, '图片不存在')
    # Keys are unguessable; only works submitted to the community have them.
    post = db.scalar(select(Post).where(Post.media_key == key, Post.status != 'private'))
    # Unreviewed or rejected media stays with the author and admins only.
    preview = post and post.status != 'approved' and viewer and (viewer.id == post.user_id or is_admin(viewer))
    if not post or (post.status != 'approved' and not preview) or not media_path(kind, key).exists():
        raise HTTPException(404, '图片不存在')
    cache = 'public, max-age=86400' if post.status == 'approved' else 'private, no-store'
    return FileResponse(media_path(kind, key), media_type='image/webp', headers={'Cache-Control': cache})


# ---------- shared helpers ----------

def work_payload(db, user_id, work_id):
    row = db.scalar(select(Work).where(Work.user_id == user_id, Work.work_id == work_id))
    return json.loads(row.payload) if row else None


def author_json(user):
    return {'id': user.id, 'nickname': user.nickname} if user else {'id': 0, 'nickname': '园林访客'}


def iso_ms(value):
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat().replace('+00:00', 'Z') if value else None


def post_summary(post, author, liked, favorite=False):
    return {'id': post.public_id, 'title': post.title or '未命名取景', 'methodId': post.method_id, 'thumbUrl': media_url('thumb', post.media_key), 'author': author_json(author), 'likeCount': post.like_count, 'commentCount': post.comment_count, 'likedByMe': liked, 'favoritedByMe': favorite, 'publishedAt': iso_ms(post.published_ts)}


def post_detail(post, author, liked, favorite=False):
    return {**post_summary(post, author, liked, favorite), 'imageUrl': media_url('full', post.media_key), 'note': post.note, 'frameId': post.frame_id, 'reviewStatus': post.status, 'rejectReason': post.reject_reason if post.status == 'rejected' else ''}


def liked_ids(db, viewer, post_ids):
    if not viewer or not post_ids:
        return set()
    return set(db.scalars(select(Like.post_id).where(Like.user_id == viewer.id, Like.post_id.in_(post_ids))))


def favorite_ids(db, viewer, post_ids):
    if not viewer or not post_ids:
        return set()
    return set(db.scalars(select(Favorite.post_id).where(Favorite.user_id == viewer.id, Favorite.post_id.in_(post_ids))))


def authors(db, user_ids):
    return {user.id: user for user in db.scalars(select(User).where(User.id.in_(set(user_ids))))} if user_ids else {}


def parse_cursor(cursor):
    try:
        first, second = cursor.split('.')
        return int(first), int(second)
    except (ValueError, AttributeError):
        raise HTTPException(400, '分页参数无效') from None


def visible_post(db, public_id, viewer, *, interact=False):
    post = db.scalar(select(Post).where(Post.public_id == public_id))
    can_preview = post and post.status in {'pending', 'rejected'} and viewer and (viewer.id == post.user_id or is_admin(viewer))
    if not post or (post.status != 'approved' and (interact or not can_preview)):
        raise HTTPException(404, '作品不存在或尚未公开')
    return post


def community_state(db, user_id):
    # Attached to the private work list so “我的” can show publish status.
    return {post.work_id: post for post in db.scalars(select(Post).where(Post.user_id == user_id))}


def state_fields(post):
    status = post.status if post else 'private'
    return {'visibility': 'private' if status == 'private' else 'public', 'reviewStatus': status, 'rejectReason': post.reject_reason if post and status == 'rejected' else '', 'communityId': post.public_id if post and status != 'private' else ''}


def snapshot(post, payload):
    # Feed queries read this snapshot instead of decoding multi-megabyte work payloads.
    post.title = (payload.get('title') or '未命名取景')[:120]
    post.method_id = payload.get('methodId') if payload.get('methodId') in METHODS else 'frame'
    post.frame_id = payload.get('frameId') or 'round'
    post.note = (payload.get('note') or '')[:2000]
    old, post.media_key = post.media_key, write_media(payload['imageDataUrl'])
    post.status, post.reject_reason, post.updated_at = 'pending', '', datetime.utcnow()
    return old


def on_work_saved(db, user_id, work_id, payload):
    # Editing a public work sends the new version back to review.
    post = db.scalar(select(Post).where(Post.user_id == user_id, Post.work_id == work_id))
    if post and post.status in {'pending', 'approved'}:
        old = snapshot(post, payload)
        db.commit()
        remove_media(old)


def on_work_deleted(db, user_id, work_id):
    post = db.scalar(select(Post).where(Post.user_id == user_id, Post.work_id == work_id))
    if not post:
        return
    comment_ids = [str(cid) for cid in db.scalars(select(Comment.id).where(Comment.post_id == post.id))]
    db.execute(delete(Report).where(or_((Report.target_type == 'work') & (Report.target_id == post.public_id), (Report.target_type == 'comment') & Report.target_id.in_(comment_ids))))
    db.execute(delete(Comment).where(Comment.post_id == post.id))
    db.execute(delete(Like).where(Like.post_id == post.id))
    db.execute(delete(Favorite).where(Favorite.post_id == post.id))
    key = post.media_key
    db.delete(post)
    db.commit()
    remove_media(key)


# ---------- author: publish ----------

@router.post('/api/v1/profile/works/{work_id}/publish')
def publish(work_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    payload = work_payload(db, user.id, work_id)
    if not payload:
        raise HTTPException(404, '作品不存在，请先保存到账号')
    limiter.consume(f'publish:{user.id}', 20, 86400)
    post = db.scalar(select(Post).where(Post.user_id == user.id, Post.work_id == work_id))
    if not post:
        post = Post(public_id=uuid.uuid4().hex, user_id=user.id, work_id=work_id)
        db.add(post)
    old = snapshot(post, payload)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        remove_media(post.media_key)
        raise HTTPException(409, '作品正在提交，请稍后刷新') from None
    remove_media(old)
    return {'status': 'pending', 'communityId': post.public_id}


@router.post('/api/v1/profile/works/{work_id}/unpublish')
def unpublish(work_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    post = db.scalar(select(Post).where(Post.user_id == user.id, Post.work_id == work_id))
    if post and post.status != 'private':
        # Likes and comments stay so a later re-publish keeps its history; images are removed now.
        old, post.media_key, post.status, post.reject_reason = post.media_key, '', 'private', ''
        db.commit()
        remove_media(old)
    return {'status': 'private'}


# ---------- public feed ----------

@router.get('/api/v1/community/works')
def feed(cursor: str = '', method: str = '', sort: str = Query('latest', pattern='^(latest|popular)$'), limit: int = Query(20, ge=1, le=50), viewer: User | None = Depends(optional_user), db: Session = Depends(get_db)):
    query = select(Post).where(Post.status == 'approved')
    if method:
        if method not in METHODS:
            raise HTTPException(400, '造景手法无效')
        query = query.where(Post.method_id == method)
    primary = Post.like_count if sort == 'popular' else Post.published_ts
    if cursor:
        value, last_id = parse_cursor(cursor)
        query = query.where(or_(primary < value, (primary == value) & (Post.id < last_id)))
    rows = list(db.scalars(query.order_by(primary.desc(), Post.id.desc()).limit(limit + 1)))
    page, more = rows[:limit], len(rows) > limit
    people, liked = authors(db, [p.user_id for p in page]), liked_ids(db, viewer, [p.id for p in page])
    favorites = favorite_ids(db, viewer, [p.id for p in page])
    last = page[-1] if page else None
    next_cursor = f'{last.like_count if sort == "popular" else last.published_ts}.{last.id}' if more and last else None
    return {'items': [post_summary(p, people.get(p.user_id), p.id in liked, p.id in favorites) for p in page], 'nextCursor': next_cursor}


@router.get('/api/v1/community/works/{public_id}')
def detail(public_id: str, viewer: User | None = Depends(optional_user), db: Session = Depends(get_db)):
    post = visible_post(db, public_id, viewer)
    return post_detail(post, db.get(User, post.user_id), post.id in liked_ids(db, viewer, [post.id]), post.id in favorite_ids(db, viewer, [post.id]))


@router.get('/api/v1/profile/favorites')
def favorites(cursor: int | None = Query(None, ge=1), user: User = Depends(current_user), db: Session = Depends(get_db)):
    query = select(Post, Favorite.id).join(Favorite, Favorite.post_id == Post.id).where(Favorite.user_id == user.id, Post.status == 'approved')
    if cursor:
        query = query.where(Favorite.id < cursor)
    rows = db.execute(query.order_by(Favorite.id.desc()).limit(21)).all()
    page = rows[:20]
    people = authors(db, [p.user_id for p, _ in page])
    liked = liked_ids(db, user, [p.id for p, _ in page])
    return {'items': [post_summary(p, people.get(p.user_id), p.id in liked, True) for p, _ in page], 'nextCursor': page[-1][1] if len(rows) > 20 else None}


@router.post('/api/v1/community/works/{public_id}/favorite')
def favorite(public_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    post = visible_post(db, public_id, user, interact=True)
    if not db.scalar(select(Favorite.id).where(Favorite.post_id == post.id, Favorite.user_id == user.id)):
        db.add(Favorite(post_id=post.id, user_id=user.id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    return {'favorited': True}


@router.delete('/api/v1/community/works/{public_id}/favorite')
def unfavorite(public_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    post = visible_post(db, public_id, user, interact=True)
    db.execute(delete(Favorite).where(Favorite.post_id == post.id, Favorite.user_id == user.id))
    db.commit()
    return {'favorited': False}


def like_state(db, post, liked):
    # Recount in one UPDATE so concurrent likes cannot write a stale number back.
    db.execute(update(Post).where(Post.id == post.id).values(like_count=select(func.count()).select_from(Like).where(Like.post_id == Post.id).scalar_subquery()))
    db.commit()
    db.refresh(post)
    return {'liked': liked, 'likeCount': post.like_count}


@router.post('/api/v1/community/works/{public_id}/like')
def like(public_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    limiter.consume(f'like:{user.id}', 60, 60)
    post = visible_post(db, public_id, user, interact=True)
    if not db.scalar(select(Like.id).where(Like.post_id == post.id, Like.user_id == user.id)):
        db.add(Like(post_id=post.id, user_id=user.id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    return like_state(db, post, True)


@router.delete('/api/v1/community/works/{public_id}/like')
def unlike(public_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    limiter.consume(f'like:{user.id}', 60, 60)
    post = visible_post(db, public_id, user, interact=True)
    db.execute(delete(Like).where(Like.post_id == post.id, Like.user_id == user.id))
    return like_state(db, post, False)


# ---------- comments ----------

def comment_json(comment, author):
    return {'id': comment.id, 'content': comment.content, 'author': author_json(author), 'createdAt': comment.created_at.isoformat() + 'Z', 'status': comment.status}


def recount_comments(db, post_id):
    count = db.scalar(select(func.count()).select_from(Comment).where(Comment.post_id == post_id, Comment.status == 'visible'))
    db.execute(update(Post).where(Post.id == post_id).values(comment_count=count))


@router.get('/api/v1/community/works/{public_id}/comments')
def comments(public_id: str, cursor: int | None = Query(None, ge=1), viewer: User | None = Depends(optional_user), db: Session = Depends(get_db)):
    post = visible_post(db, public_id, viewer)
    # Pending comments are visible only to their own author.
    visible = Comment.status == 'visible'
    query = select(Comment).where(Comment.post_id == post.id, or_(visible, (Comment.status == 'pending') & (Comment.user_id == viewer.id)) if viewer else visible)
    if cursor:
        query = query.where(Comment.id < cursor)
    rows = list(db.scalars(query.order_by(Comment.id.desc()).limit(21)))
    page = rows[:20]
    people = authors(db, [c.user_id for c in page])
    return {'items': [comment_json(c, people.get(c.user_id)) for c in page], 'nextCursor': page[-1].id if len(rows) > 20 else None}


@router.post('/api/v1/community/works/{public_id}/comments', status_code=201)
def add_comment(public_id: str, payload: CommentRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    limiter.consume(f'comment:{user.id}', 10, 60)
    post = visible_post(db, public_id, user, interact=True)
    status = 'visible' if comment_is_safe(payload.content) else 'pending'
    comment = Comment(post_id=post.id, user_id=user.id, content=payload.content, status=status)
    db.add(comment)
    db.flush()
    recount_comments(db, post.id)
    db.commit()
    return comment_json(comment, user)


@router.delete('/api/v1/community/comments/{comment_id}')
def remove_comment(comment_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    comment = db.get(Comment, comment_id)
    post = db.get(Post, comment.post_id) if comment else None
    if not comment or not post:
        raise HTTPException(404, '评论不存在')
    if user.id not in {comment.user_id, post.user_id} and not is_admin(user):
        raise HTTPException(403, '只能删除自己的评论或自己作品下的评论')
    db.execute(delete(Report).where(Report.target_type == 'comment', Report.target_id == str(comment.id)))
    db.delete(comment)
    db.flush()
    recount_comments(db, post.id)
    db.commit()
    return {'message': '评论已删除'}


# ---------- reports ----------

@router.post('/api/v1/community/reports', status_code=201)
def report(payload: ReportRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if payload.targetType == 'work':
        exists = db.scalar(select(Post.id).where(Post.public_id == payload.targetId, Post.status == 'approved'))
    else:
        exists = payload.targetId.isdigit() and db.scalar(select(Comment.id).where(Comment.id == int(payload.targetId), Comment.status == 'visible'))
    if not exists:
        raise HTTPException(404, '举报对象不存在')
    duplicate = db.scalar(select(Report.id).where(Report.reporter_id == user.id, Report.target_type == payload.targetType, Report.target_id == payload.targetId, Report.status == 'open'))
    if duplicate:
        return {'id': duplicate, 'message': '已收到你的举报，我们会尽快处理'}
    limiter.consume(f'report:{user.id}', 20, 86400)
    row = Report(reporter_id=user.id, target_type=payload.targetType, target_id=payload.targetId, reason=payload.reason.strip() or '未填写原因')
    db.add(row)
    db.commit()
    return {'id': row.id, 'message': '已收到你的举报，我们会尽快处理'}


# ---------- admin ----------

@router.get('/api/v1/admin/queue')
def queue(type: str = Query('work', pattern='^(work|comment|report)$'), _: User = Depends(admin_user), db: Session = Depends(get_db)):
    if type == 'work':
        rows = list(db.scalars(select(Post).where(Post.status == 'pending').order_by(Post.updated_at).limit(50)))
        people = authors(db, [p.user_id for p in rows])
        return {'items': [post_detail(p, people.get(p.user_id), False) for p in rows]}
    if type == 'comment':
        rows = list(db.scalars(select(Comment).where(Comment.status == 'pending').order_by(Comment.id).limit(50)))
        people, posts = authors(db, [c.user_id for c in rows]), {p.id: p for p in db.scalars(select(Post).where(Post.id.in_({c.post_id for c in rows})))} if rows else {}
        return {'items': [{**comment_json(c, people.get(c.user_id)), 'workId': posts[c.post_id].public_id, 'workTitle': posts[c.post_id].title} for c in rows if c.post_id in posts]}
    rows = list(db.scalars(select(Report).where(Report.status == 'open').order_by(Report.id).limit(50)))
    items = []
    for r in rows:
        if r.target_type == 'work':
            post = db.scalar(select(Post).where(Post.public_id == r.target_id))
            preview = post.title if post else '（作品已删除）'
        else:
            comment = db.get(Comment, int(r.target_id)) if r.target_id.isdigit() else None
            preview = comment.content if comment else '（评论已删除）'
        items.append({'id': r.id, 'targetType': r.target_type, 'targetId': r.target_id, 'reason': r.reason, 'preview': preview, 'createdAt': r.created_at.isoformat() + 'Z'})
    return {'items': items}


@router.post('/api/v1/admin/works/{public_id}/review')
def review_work(public_id: str, payload: ReviewRequest, _: User = Depends(admin_user), db: Session = Depends(get_db)):
    post = db.scalar(select(Post).where(Post.public_id == public_id))
    if not post or post.status == 'private':
        raise HTTPException(404, '作品不存在或已撤回')
    if payload.action == 'approve':
        # Keep the first publish time, so re-approved edits do not jump the feed.
        post.status, post.reject_reason = 'approved', ''
        post.published_ts = post.published_ts or int(time.time() * 1000)
    else:
        post.status, post.reject_reason = 'rejected', payload.reason.strip() or '内容不符合社区规范'
    db.commit()
    return {'status': post.status}


@router.post('/api/v1/admin/comments/{comment_id}/review')
def review_comment(comment_id: int, payload: ReviewRequest, _: User = Depends(admin_user), db: Session = Depends(get_db)):
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(404, '评论不存在')
    comment.status = 'visible' if payload.action == 'approve' else 'hidden'
    db.flush()
    recount_comments(db, comment.post_id)
    db.commit()
    return {'status': comment.status}


@router.post('/api/v1/admin/reports/{report_id}/resolve')
def resolve_report(report_id: int, payload: ResolveRequest = ResolveRequest(), _: User = Depends(admin_user), db: Session = Depends(get_db)):
    row = db.get(Report, report_id)
    if not row:
        raise HTTPException(404, '举报不存在')
    if payload.action == 'remove':
        if row.target_type == 'work':
            post = db.scalar(select(Post).where(Post.public_id == row.target_id))
            # A pending edit (re-submitted, not yet reviewed) is taken down too.
            if post and post.status in {'approved', 'pending'}:
                post.status, post.reject_reason = 'rejected', '因举报下架，修改后可重新发布'
        elif row.target_id.isdigit() and (comment := db.get(Comment, int(row.target_id))):
            comment.status = 'hidden'
            db.flush()
            recount_comments(db, comment.post_id)
    # One decision closes every open report on the same target.
    db.execute(update(Report).where(Report.target_type == row.target_type, Report.target_id == row.target_id, Report.status == 'open').values(status='resolved'))
    db.commit()
    return {'status': 'resolved'}
