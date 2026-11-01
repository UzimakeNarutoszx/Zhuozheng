import base64
import io
import os
import tempfile
import unittest
from pathlib import Path

_temp = tempfile.TemporaryDirectory()
# Same isolated test environment as test_api.py when this module runs alone.
os.environ.setdefault('DATABASE_URL', 'sqlite:///' + _temp.name + '/community.db')
os.environ['ENVIRONMENT'] = 'test'
os.environ['SMS_PROVIDER'] = 'local'
os.environ['SMS_DEV_CODE'] = '123456'
os.environ.setdefault('SECRET_KEY', 'garden-test-secret-not-for-production')

from fastapi.testclient import TestClient
from PIL import Image
from app.main import app
from app.config import settings
from app.db import Base, engine
from app.security import limiter

ADMIN = '13900000009'


def png(color='green', size=(40, 30)):
    output = io.BytesIO()
    Image.new('RGB', size, color).save(output, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode()


class CommunityTests(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        limiter.entries.clear()
        self.media = tempfile.TemporaryDirectory()
        self.saved = settings.admin_phones, settings.media_dir
        settings.admin_phones, settings.media_dir = {ADMIN}, Path(self.media.name)
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        settings.admin_phones, settings.media_dir = self.saved
        self.media.cleanup()

    def register(self, phone, nickname='园中访客'):
        limiter.clear('sms-minute:' + phone)
        self.client.post('/api/v1/auth/send-sms', json={'phone': phone, 'scene': 'register'})
        response = self.client.post('/api/v1/auth/register', json={'phone': phone, 'nickname': nickname, 'password': 'testpass123', 'sms_code': '123456'})
        self.assertEqual(response.status_code, 201, response.text)
        return {'Authorization': 'Bearer ' + response.json()['access_token']}

    def publish(self, headers, work_id='w1', title='窗里的园', method='frame'):
        work = {'id': work_id, 'title': title, 'note': '从圆窗看竹', 'methodId': method, 'imageDataUrl': png()}
        self.assertEqual(self.client.post('/api/v1/profile/works', json=work, headers=headers).status_code, 200)
        result = self.client.post(f'/api/v1/profile/works/{work_id}/publish', headers=headers)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['status'], 'pending')
        return result.json()['communityId'], work

    def approve(self, admin, public_id):
        result = self.client.post(f'/api/v1/admin/works/{public_id}/review', json={'action': 'approve'}, headers=admin)
        self.assertEqual(result.status_code, 200, result.text)

    def test_publish_review_feed_and_privacy(self):
        alice, bob, admin = self.register('13800000011', '小园'), self.register('13800000012'), self.register(ADMIN)
        self.assertEqual(self.client.get('/api/v1/profile/me', headers=admin).json()['role'], 'admin')
        self.assertEqual(self.client.get('/api/v1/profile/me', headers=alice).json()['role'], 'user')
        pid, _ = self.publish(alice)
        mine = self.client.get('/api/v1/profile/works', headers=alice).json()[0]
        self.assertEqual((mine['visibility'], mine['reviewStatus'], mine['communityId']), ('public', 'pending', pid))
        # Pending: not in feed, hidden from others, visible to author and admin.
        self.assertEqual(self.client.get('/api/v1/community/works').json()['items'], [])
        self.assertEqual(self.client.get(f'/api/v1/community/works/{pid}', headers=bob).status_code, 404)
        self.assertEqual(self.client.get(f'/api/v1/community/works/{pid}', headers=alice).json()['reviewStatus'], 'pending')
        self.assertEqual(self.client.get('/api/v1/admin/queue?type=work', headers=bob).status_code, 403)
        self.assertEqual([item['id'] for item in self.client.get('/api/v1/admin/queue?type=work', headers=admin).json()['items']], [pid])
        self.approve(admin, pid)
        feed = self.client.get('/api/v1/community/works').json()
        self.assertEqual(len(feed['items']), 1)
        item = feed['items'][0]
        self.assertEqual(item['author'], {'id': item['author']['id'], 'nickname': '小园'})
        self.assertNotIn('13800000011', str(feed))
        detail = self.client.get(f'/api/v1/community/works/{pid}').json()
        self.assertEqual((detail['note'], detail['methodId']), ('从圆窗看竹', 'frame'))
        thumb = self.client.get(detail['thumbUrl'])
        self.assertEqual(thumb.status_code, 200)
        self.assertEqual(thumb.headers['content-type'], 'image/webp')
        self.assertIn('immutable', thumb.headers['cache-control'])
        self.assertEqual(self.client.get('/api/v1/profile/me', headers=alice).headers['cache-control'], 'no-store')
        # Editing re-enters review with a new image; unpublishing removes media.
        _, work = self.publish(alice, 'w2', '第二幅', 'borrow')
        self.assertEqual(len(self.client.get('/api/v1/community/works?method=borrow').json()['items']), 0)
        work = {'id': 'w1', 'title': '改过的园', 'imageDataUrl': png('red')}
        self.client.put('/api/v1/profile/works/w1', json=work, headers=alice)
        self.assertEqual(self.client.get(detail['thumbUrl']).status_code, 404)
        self.assertEqual(self.client.get('/api/v1/community/works').json()['items'], [])
        self.approve(admin, pid)
        self.assertEqual(self.client.get('/api/v1/community/works').json()['items'][0]['title'], '改过的园')
        self.client.post('/api/v1/profile/works/w1/unpublish', headers=alice)
        self.assertEqual(self.client.get(f'/api/v1/community/works/{pid}').status_code, 404)
        # Only the still-pending w2 keeps its thumb + full image.
        self.assertEqual(len(list(Path(self.media.name).rglob('*.webp'))), 2)

    def test_reject_with_reason(self):
        alice, admin = self.register('13800000013'), self.register(ADMIN)
        pid, _ = self.publish(alice)
        self.client.post(f'/api/v1/admin/works/{pid}/review', json={'action': 'reject', 'reason': '图片不清晰'}, headers=admin)
        mine = self.client.get('/api/v1/profile/works', headers=alice).json()[0]
        self.assertEqual((mine['reviewStatus'], mine['rejectReason']), ('rejected', '图片不清晰'))
        self.assertEqual(self.client.post(f'/api/v1/community/works/{pid}/like', headers=alice).status_code, 404)

    def test_likes_idempotent_and_popular_pagination(self):
        alice, bob, admin = self.register('13800000014'), self.register('13800000015'), self.register(ADMIN)
        ids = []
        for index in range(3):
            pid, _ = self.publish(alice, f'w{index}', f'作品{index}')
            self.approve(admin, pid)
            ids.append(pid)
        for _ in range(2):
            self.assertEqual(self.client.post(f'/api/v1/community/works/{ids[0]}/like', headers=bob).json(), {'liked': True, 'likeCount': 1})
        self.assertEqual(self.client.post(f'/api/v1/community/works/{ids[0]}/like').status_code, 401)
        self.assertTrue(self.client.get('/api/v1/community/works', headers=bob).json()['items'][-1]['likedByMe'])
        self.assertFalse(self.client.get('/api/v1/community/works').json()['items'][-1]['likedByMe'])
        first = self.client.get('/api/v1/community/works?sort=popular&limit=2').json()
        self.assertEqual(first['items'][0]['id'], ids[0])
        rest = self.client.get(f'/api/v1/community/works?sort=popular&limit=2&cursor={first["nextCursor"]}').json()
        self.assertEqual(len({i['id'] for i in first['items'] + rest['items']}), 3)
        self.assertIsNone(rest['nextCursor'])
        latest = self.client.get('/api/v1/community/works').json()['items']
        self.assertEqual([i['id'] for i in latest], ids[::-1])
        for _ in range(2):
            self.assertEqual(self.client.delete(f'/api/v1/community/works/{ids[0]}/like', headers=bob).json(), {'liked': False, 'likeCount': 0})

    def test_comments_moderation_reports_and_delete_cascade(self):
        alice, bob, carol, admin = self.register('13800000016'), self.register('13800000017', '路人'), self.register('13800000018'), self.register(ADMIN)
        pid, _ = self.publish(alice)
        self.approve(admin, pid)
        ok = self.client.post(f'/api/v1/community/works/{pid}/comments', json={'content': '  好看的窗  '}, headers=bob)
        self.assertEqual((ok.status_code, ok.json()['content'], ok.json()['status']), (201, '好看的窗', 'visible'))
        flagged = self.client.post(f'/api/v1/community/works/{pid}/comments', json={'content': '加微信看更多'}, headers=bob).json()
        self.assertEqual(flagged['status'], 'pending')
        self.assertEqual(len(self.client.get(f'/api/v1/community/works/{pid}/comments', headers=bob).json()['items']), 2)
        self.assertEqual(len(self.client.get(f'/api/v1/community/works/{pid}/comments').json()['items']), 1)
        self.assertEqual(self.client.get(f'/api/v1/community/works/{pid}').json()['commentCount'], 1)
        self.assertEqual(self.client.post(f'/api/v1/community/works/{pid}/comments', json={'content': 'x' * 501}, headers=bob).status_code, 422)
        self.assertEqual([c['id'] for c in self.client.get('/api/v1/admin/queue?type=comment', headers=admin).json()['items']], [flagged['id']])
        self.client.post(f'/api/v1/admin/comments/{flagged["id"]}/review', json={'action': 'reject'}, headers=admin)
        self.assertEqual(len(self.client.get(f'/api/v1/community/works/{pid}/comments', headers=bob).json()['items']), 1)
        # Only comment author, work author or admin may delete.
        self.assertEqual(self.client.delete(f'/api/v1/community/comments/{ok.json()["id"]}', headers=carol).status_code, 403)
        report = self.client.post('/api/v1/community/reports', json={'targetType': 'work', 'targetId': pid, 'reason': '疑似搬运'}, headers=carol)
        self.assertEqual(report.status_code, 201)
        again = self.client.post('/api/v1/community/reports', json={'targetType': 'work', 'targetId': pid, 'reason': '重复'}, headers=carol)
        self.assertEqual(again.json()['id'], report.json()['id'])
        queue = self.client.get('/api/v1/admin/queue?type=report', headers=admin).json()['items']
        self.assertEqual((len(queue), queue[0]['preview']), (1, '窗里的园'))
        self.client.post(f'/api/v1/admin/reports/{queue[0]["id"]}/resolve', json={'action': 'remove'}, headers=admin)
        self.assertEqual(self.client.get('/api/v1/community/works').json()['items'], [])
        self.assertEqual(self.client.get('/api/v1/admin/queue?type=report', headers=admin).json()['items'], [])
        self.assertEqual(self.client.delete(f'/api/v1/community/comments/{ok.json()["id"]}', headers=alice).status_code, 200)
        self.assertEqual(self.client.delete('/api/v1/profile/works/w1', headers=alice).status_code, 200)
        self.assertEqual(self.client.get(f'/api/v1/community/works/{pid}', headers=admin).status_code, 404)
        self.assertEqual(list(Path(self.media.name).rglob('*.webp')), [])

    def test_rate_limits_and_invalid_input(self):
        alice, admin = self.register('13800000019'), self.register(ADMIN)
        pid, _ = self.publish(alice)
        self.approve(admin, pid)
        for _ in range(10):
            self.assertEqual(self.client.post(f'/api/v1/community/works/{pid}/comments', json={'content': '好'}, headers=alice).status_code, 201)
        self.assertEqual(self.client.post(f'/api/v1/community/works/{pid}/comments', json={'content': '好'}, headers=alice).status_code, 429)
        self.assertEqual(self.client.get('/api/v1/community/works?cursor=bad').status_code, 400)
        self.assertEqual(self.client.get('/api/v1/community/works?method=nope').status_code, 400)
        self.assertEqual(self.client.get('/api/v1/media/thumb/../../.secret').status_code, 404)
        self.assertEqual(self.client.post('/api/v1/profile/works/missing/publish', headers=alice).status_code, 404)


if __name__ == '__main__':
    unittest.main()
