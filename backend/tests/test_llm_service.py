from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.services.llm import LLMService, ModelTarget, parse_json_response, strip_code_fence


class LLMServiceTests(unittest.TestCase):
    def test_fenced_json_is_parsed(self) -> None:
        self.assertEqual(parse_json_response('```json\n{"ok": true}\n```'), {"ok": True})

    def test_non_object_json_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_json_response('["not", "an", "object"]')

    def test_multimodal_messages_use_openai_image_format(self) -> None:
        messages = LLMService._messages(
            prompt="Read this",
            system="Return JSON",
            messages=None,
            images=["data:image/png;base64,YQ=="],
        )
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["content"][1]["type"], "image_url")

    def test_invalid_image_url_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            LLMService._messages(prompt="Read", system=None, messages=None, images=["https://example.com/a.png"])

    def test_code_fence_stripping(self) -> None:
        self.assertEqual(strip_code_fence("```json\n{}\n```"), "{}")

    def test_generation_falls_back_after_provider_payment_error(self) -> None:
        class PaymentRequired(Exception):
            status_code = 402

        cerebras_create = Mock(side_effect=PaymentRequired("payment required"))
        fireworks_create = Mock(
            return_value=SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))],
                usage=None,
            )
        )
        clients = {
            "cerebras": SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=cerebras_create))),
            "fireworks": SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fireworks_create))),
        }
        service = LLMService()

        with patch.object(service, "client", side_effect=lambda provider: clients[provider]):
            output = service.generate_json(
                provider="cerebras",
                model="gemma-4-31b",
                prompt="Return JSON",
                fallbacks=[ModelTarget("fireworks", "accounts/fireworks/models/minimax-m3")],
                retries=1,
            )

        self.assertEqual(output, {"ok": True})
        cerebras_create.assert_called_once()
        fireworks_create.assert_called_once()


if __name__ == "__main__":
    unittest.main()
