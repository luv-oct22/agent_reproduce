import unittest
from unittest.mock import patch

from src.harness.openai import OpenAIHarness


class HarnessTimeoutTests(unittest.TestCase):
    def test_explicit_timeout_defaults_and_environment_overrides_reach_sdk(self):
        for environment, expected_connect, expected_read in [
            ({}, 60, 600),
            ({'OPENAI_TIMEOUT': '900', 'OPENAI_CONNECT_TIMEOUT': '120'}, 120, 900),
        ]:
            with patch.dict('os.environ', environment, clear=True), patch('src.harness.openai.OpenAI') as client:
                OpenAIHarness('test-model', api_key='test-key')
                timeout = client.call_args.kwargs['timeout']
                self.assertEqual(timeout.connect, expected_connect)
                self.assertEqual(timeout.read, expected_read)
                self.assertEqual(timeout.write, expected_read)
                self.assertEqual(timeout.pool, expected_read)

    def test_invalid_timeouts_fail_before_constructing_client(self):
        for variable in ('OPENAI_TIMEOUT', 'OPENAI_CONNECT_TIMEOUT'):
            for value in ('0', '-5', 'nan', 'inf', 'invalid'):
                with patch.dict('os.environ', {variable: value}, clear=True), patch('src.harness.openai.OpenAI') as client:
                    with self.assertRaisesRegex(ValueError, variable):
                        OpenAIHarness(api_key='test-key')
                    client.assert_not_called()


if __name__ == '__main__':
    unittest.main()
