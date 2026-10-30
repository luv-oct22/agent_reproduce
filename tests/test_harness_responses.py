import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.harness.openai import OpenAIHarness, api_mode_for
from src.harness.types import Message, ToolCall, ToolDef


def fake_response():
    call = SimpleNamespace(type='function_call', call_id='call_1', name='measure_mass', arguments='{"object_id": "ball_1"}')
    text = SimpleNamespace(type='message', content=[SimpleNamespace(type='output_text', text='Measuring.')])
    reasoning = SimpleNamespace(type='reasoning')
    return SimpleNamespace(output=[reasoning, text, call], usage=SimpleNamespace(input_tokens=10, output_tokens=5))


class ResponsesApiTests(unittest.TestCase):
    def test_mode_selection(self):
        with patch.dict('os.environ', {}, clear=True):
            self.assertEqual(api_mode_for('gpt-6.1-sol'), 'responses')
            self.assertEqual(api_mode_for('qwen3.8-max'), 'chat')
        with patch.dict('os.environ', {'OPENAI_API_MODE': 'responses'}, clear=True):
            self.assertEqual(api_mode_for('qwen3.8-max'), 'responses')
        with patch.dict('os.environ', {'OPENAI_API_MODE': 'chat'}, clear=True):
            self.assertEqual(api_mode_for('gpt-6.1-sol'), 'chat')

    def test_request_translation_and_output_parsing(self):
        with patch.dict('os.environ', {}, clear=True), patch('src.harness.openai.OpenAI') as client:
            harness = OpenAIHarness('gpt-6.1-sol', api_key='test')
            create = client.return_value.responses.create
            create.return_value = fake_response()
            messages = [
                Message(role='system', content='sys'),
                Message(role='user', content='go'),
                Message(role='assistant', content='', tool_calls=[ToolCall(id='c0', function_name='inspect', arguments='{}')]),
                Message(role='tool', content='{"ok": true}', tool_call_id='c0'),
            ]
            tools = [ToolDef(name='measure_mass', description='d', parameters={'type': 'object', 'properties': {}})]
            resp = harness.generate(messages, tools=tools, temperature=0.7, seed=42, max_completion_tokens=100)

            kwargs = create.call_args.kwargs
            self.assertEqual(kwargs['model'], 'gpt-6.1-sol')
            self.assertNotIn('temperature', kwargs)
            self.assertNotIn('seed', kwargs)
            self.assertNotIn('max_completion_tokens', kwargs)
            self.assertEqual(kwargs['max_output_tokens'], 100)
            self.assertEqual(kwargs['tools'], [{'type': 'function', 'name': 'measure_mass', 'description': 'd',
                                               'parameters': {'type': 'object', 'properties': {}}}])
            self.assertEqual(kwargs['input'], [
                {'role': 'system', 'content': 'sys'},
                {'role': 'user', 'content': 'go'},
                {'type': 'function_call', 'call_id': 'c0', 'name': 'inspect', 'arguments': '{}'},
                {'type': 'function_call_output', 'call_id': 'c0', 'output': '{"ok": true}'},
            ])
            client.return_value.chat.completions.create.assert_not_called()

            self.assertEqual(resp.content, 'Measuring.')
            self.assertEqual([(t.id, t.function_name, json.loads(t.arguments)) for t in resp.tool_calls],
                             [('call_1', 'measure_mass', {'object_id': 'ball_1'})])
            self.assertEqual((resp.usage.prompt_tokens, resp.usage.completion_tokens), (10, 5))

    def test_chat_models_still_use_chat_completions(self):
        with patch.dict('os.environ', {}, clear=True), patch('src.harness.openai.OpenAI') as client:
            harness = OpenAIHarness('qwen3.8-max', api_key='test')
            client.return_value.chat.completions.create.return_value = SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='hi', tool_calls=None))], usage=None)
            self.assertEqual(harness.generate([Message(role='user', content='x')], temperature=0.7).content, 'hi')
            self.assertEqual(client.return_value.chat.completions.create.call_args.kwargs['temperature'], 0.7)
            client.return_value.responses.create.assert_not_called()


if __name__ == '__main__':
    unittest.main()
