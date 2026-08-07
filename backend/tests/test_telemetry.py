import unittest

from app.telemetry import _headers, configure_telemetry


class TelemetryTests(unittest.TestCase):
    def test_otlp_headers_are_parsed_and_url_decoded(self):
        self.assertEqual(
            _headers("Authorization=Bearer%20secret,X-Tenant=learneros"),
            {"Authorization": "Bearer secret", "X-Tenant": "learneros"},
        )

    def test_blank_otlp_headers_are_ignored(self):
        self.assertIsNone(_headers("  "))

    def test_disabled_telemetry_is_a_noop(self):
        configure_telemetry()


if __name__ == "__main__":
    unittest.main()
