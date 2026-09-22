import unittest
from unittest.mock import Mock, patch

from jev import JevUnavailable, decide, decide_or_fallback


QUESTION = {
    "status": {
        "type": "choice",
        "instructions": "Classify the supplied audit summary.",
        "criteria": {"ok": "No issue", "review": "Needs review"},
    }
}


class JevClientTests(unittest.TestCase):
    @patch.dict("os.environ", {"JEV_API_KEY": "test-key"})
    @patch("jev.requests.post")
    def test_decide_posts_typed_payload(self, post):
        response = Mock()
        response.json.return_value = {"answers": {"status": {"choice": "ok"}}}
        post.return_value = response

        result = decide(state={"total": 1}, questions=QUESTION)

        self.assertEqual("ok", result["answers"]["status"]["choice"])
        self.assertEqual("Bearer test-key", post.call_args.kwargs["headers"]["Authorization"])

    def test_choice_requires_criteria(self):
        with self.assertRaises(ValueError):
            decide(state="audit", questions={"x": {"type": "choice", "instructions": "x"}})

    @patch.dict("os.environ", {}, clear=True)
    def test_fallback_when_key_is_missing(self):
        result, used_fallback = decide_or_fallback(
            state="audit", questions=QUESTION, fallback=lambda: {"answers": {"status": {"choice": "review"}}}
        )
        self.assertTrue(used_fallback)
        self.assertEqual("review", result["answers"]["status"]["choice"])

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_key_raises_safe_error(self):
        with self.assertRaises(JevUnavailable):
            decide(state="audit", questions=QUESTION)
