import unittest
from unittest.mock import Mock, patch

import httpx

from app.moderation import comment_is_safe


class ModerationTests(unittest.TestCase):
    @patch('app.moderation.settings')
    @patch('app.moderation.httpx.post')
    def test_only_explicit_allow_is_public(self, post, settings):
        settings.sensitive_words = {'博彩'}
        settings.ai_api_key = 'test'
        settings.ai_api_base_url = 'https://example.invalid'
        settings.ai_model = 'test'
        response = Mock()
        post.return_value = response
        for result, expected in [('{"decision":"allow"}', True), ('{"decision":"review"}', False), ('invalid', False), ('{}', False)]:
            response.json.return_value = {'choices': [{'message': {'content': result}}]}
            with self.subTest(result=result):
                self.assertEqual(comment_is_safe('这扇窗很好看'), expected)
        post.side_effect = httpx.ConnectTimeout('timeout')
        self.assertFalse(comment_is_safe('这扇窗很好看'))
        post.reset_mock()
        self.assertFalse(comment_is_safe('博彩'))
        post.assert_not_called()

    @patch('app.moderation.settings')
    @patch('app.moderation.httpx.post')
    def test_fenced_and_wrapped_answers_are_still_parsed(self, post, settings):
        settings.sensitive_words = set()
        settings.ai_api_key = 'test'
        settings.ai_api_base_url = 'https://example.invalid'
        settings.ai_model = 'test'
        response = Mock()
        post.return_value = response
        cases = [('```json\n{"decision":"allow"}\n```', True), ('```\n{"decision":"review"}\n```', False), ('结论如下：{"decision":"allow"} 以上。', True), ('{"decision":"allow","reason":"窗"}', True), ('{"decision":"review"}', False), ('```json\nnot json\n```', False)]
        for result, expected in cases:
            response.json.return_value = {'choices': [{'message': {'content': result}}]}
            with self.subTest(result=result):
                self.assertEqual(comment_is_safe('这扇窗很好看'), expected)
        # The request asks for a JSON object so fences are less likely in the first place.
        self.assertEqual(post.call_args.kwargs['json']['response_format'], {'type': 'json_object'})

    @patch('app.moderation.settings')
    @patch('app.moderation.httpx.post')
    def test_failure_log_names_status_and_error_without_key(self, post, settings):
        settings.sensitive_words = set()
        settings.ai_api_key = 'sk-secret-should-not-leak'
        settings.ai_api_base_url = 'https://example.invalid'
        settings.ai_model = 'test'
        response = Mock(status_code=502)
        response.raise_for_status.side_effect = httpx.HTTPStatusError('bad gateway', request=Mock(), response=Mock(status_code=502))
        post.return_value = response
        with self.assertLogs('app.moderation', level='WARNING') as logs:
            self.assertFalse(comment_is_safe('这扇窗很好看'))
        output = ' '.join(logs.output)
        self.assertIn('502', output)
        self.assertIn('HTTPStatusError', output)
        self.assertNotIn('sk-secret-should-not-leak', output)


if __name__ == '__main__':
    unittest.main()
