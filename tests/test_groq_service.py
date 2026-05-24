import unittest

from app.backend.services.groq_service import GroqServiceError, extract_json_object


class GroqServiceTest(unittest.TestCase):
    def test_extract_plain_json(self):
        self.assertEqual(extract_json_object('{"intent":"CREATE_RESERVATION"}')["intent"], "CREATE_RESERVATION")

    def test_extract_fenced_json(self):
        parsed = extract_json_object('```json\n{"intent":"OUT_OF_SCOPE"}\n```')
        self.assertEqual(parsed["intent"], "OUT_OF_SCOPE")

    def test_invalid_json_raises_controlled_error(self):
        with self.assertRaises(GroqServiceError) as context:
            extract_json_object("isso nao e json")
        self.assertEqual(context.exception.code, "invalid_json")

    def test_empty_response_raises_controlled_error(self):
        with self.assertRaises(GroqServiceError) as context:
            extract_json_object("")
        self.assertEqual(context.exception.code, "empty_response")


if __name__ == "__main__":
    unittest.main()

