import os
import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException

import security


class SecurityTests(unittest.TestCase):
    def setUp(self):
        security._cache.clear()
        os.environ["GOOGLE_CLIENT_ID"] = "expected-client"

    def tearDown(self):
        os.environ.pop("GOOGLE_CLIENT_ID", None)
        security._cache.clear()

    @patch("security.requests.get")
    def test_verified_corporate_token_is_accepted(self, get):
        token_info = Mock(status_code=200)
        token_info.json.return_value = {
            "audience": "expected-client",
            "email": "worker@e-voltage.cl",
            "verified_email": True,
            "expires_in": "120",
        }
        profile = Mock(status_code=200)
        profile.json.return_value = {"email": "worker@e-voltage.cl", "name": "Worker"}
        get.side_effect = [token_info, profile]

        user = security._verify_google_access_token("valid-token")
        self.assertEqual(user.email, "worker@e-voltage.cl")
        self.assertEqual(user.name, "Worker")

    @patch("security.requests.get")
    def test_wrong_audience_is_rejected(self, get):
        response = Mock(status_code=200)
        response.json.return_value = {
            "audience": "attacker-client",
            "email": "worker@e-voltage.cl",
            "verified_email": True,
        }
        get.return_value = response
        with self.assertRaises(HTTPException) as context:
            security._verify_google_access_token("wrong-audience")
        self.assertEqual(context.exception.status_code, 401)

    @patch("security.requests.get")
    def test_non_corporate_account_is_rejected(self, get):
        response = Mock(status_code=200)
        response.json.return_value = {
            "audience": "expected-client",
            "email": "attacker@gmail.com",
            "verified_email": True,
        }
        get.return_value = response
        with self.assertRaises(HTTPException) as context:
            security._verify_google_access_token("external-user")
        self.assertEqual(context.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
