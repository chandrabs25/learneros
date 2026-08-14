from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.config import settings
from app.services.llm import (
    LLMService,
    ModelTarget,
    default_generation_targets,
    parse_json_response,
    strip_code_fence,
)


class LLMServiceTests(unittest.TestCase):
    @patch("app.services.llm.settings.FIREWORKS_API_KEY", "fireworks-key")
    def test_default_generation_uses_only_fireworks(self) -> None:
        self.assertEqual(
            default_generation_targets(),
            [ModelTarget("fireworks", settings.FIREWORKS_MODEL)],
        )

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

    def test_generation_falls_back_to_another_fireworks_model_after_error(self) -> None:
        class PaymentRequired(Exception):
            status_code = 402

        fireworks_create = Mock(
            side_effect=[
                PaymentRequired("payment required"),
                SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content='{"ok": true}')
                        )
                    ],
                    usage=None,
                ),
            ]
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=fireworks_create))
        )
        service = LLMService()

        with patch.object(service, "client", return_value=client):
            output = service.generate_json(
                provider="fireworks",
                model="accounts/fireworks/models/primary",
                prompt="Return JSON",
                fallbacks=[ModelTarget("fireworks", "accounts/fireworks/models/fallback")],
                retries=1,
            )

        self.assertEqual(output, {"ok": True})
        self.assertEqual(fireworks_create.call_count, 2)


if __name__ == "__main__":
    unittest.main()
