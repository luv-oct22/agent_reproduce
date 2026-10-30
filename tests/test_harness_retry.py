from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx
from openai import APIStatusError, APITimeoutError, BadRequestError

from src.harness.openai import OpenAIHarness
from src.harness.types import Message


def status_error(code, message):
    response = httpx.Response(code, request=httpx.Request('POST', 'https://example.invalid/v1/chat/completions'))
    cls = BadRequestError if code == 400 else APIStatusError
    return cls(message, response=response, body={'error': {'message': message}})


def success():
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='B', tool_calls=None))], usage=None)


class HarnessRetryTests(unittest.TestCase):
    def test_transient_400_and_connection_timeout_share_budget_and_same_request(self):
        with patch.dict('os.environ', {}, clear=True), patch('src.harness.openai.OpenAI') as client, patch('src.harness.openai.time.sleep') as sleep:
            harness = OpenAIHarness('vision', api_key='test')
            self.assertEqual(client.call_args.kwargs['max_retries'], 0)
            create = client.return_value.chat.completions.create
            create.side_effect = [status_error(400, 'Download multimodal file timed out'),
                                  APITimeoutError(request=httpx.Request('POST', 'https://example.invalid')), success()]
            self.assertEqual(harness.generate([Message(role='user', content='Question')]).content, 'B')
            self.assertEqual([call.args[0] for call in sleep.call_args_list], [5, 10])
            self.assertEqual(create.call_count, 3)
            self.assertEqual(create.call_args_list[0], create.call_args_list[2])

    def test_exhausted_budget_raises_original_error_and_caps_backoff(self):
        error = status_error(400, 'Download multimodal file timed out')
        with patch.dict('os.environ', {'OPENAI_MAX_RETRIES': '5'}, clear=True), patch('src.harness.openai.OpenAI') as client, patch('src.harness.openai.time.sleep') as sleep:
            client.return_value.chat.completions.create.side_effect = error
            with self.assertRaises(BadRequestError) as caught:
                OpenAIHarness(api_key='test').generate([])
            self.assertIs(caught.exception, error)
            self.assertEqual(client.return_value.chat.completions.create.call_count, 6)
            self.assertEqual([call.args[0] for call in sleep.call_args_list], [5, 10, 20, 30, 30])

    def test_permanent_errors_fail_immediately_and_zero_disables_retries(self):
        for code, message, retries in [(400, 'Unsupported image format', '3'),
                                        (401, 'Invalid API key', '3'),
                                        (400, 'Download multimodal file timed out', '0')]:
            with patch.dict('os.environ', {'OPENAI_MAX_RETRIES': retries}, clear=True), patch('src.harness.openai.OpenAI') as client, patch('src.harness.openai.time.sleep') as sleep:
                client.return_value.chat.completions.create.side_effect = status_error(code, message)
                with self.assertRaises(APIStatusError):
                    OpenAIHarness(api_key='test').generate([])
                self.assertEqual(client.return_value.chat.completions.create.call_count, 1)
                sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
