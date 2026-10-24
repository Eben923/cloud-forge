import os
from unittest.mock import patch


def test_api_key_auth_enforced_when_configured(client):
    with patch.dict(os.environ, {"API_KEY": "supersecretkey"}):
        import main
        main.REQUIRED_API_KEY = "supersecretkey"

        # 1. /health should always remain public without auth
        health_res = client.get("/health")
        assert health_res.status_code == 200

        # 2. Protected endpoint without key should return 401
        res_no_key = client.get("/projects")
        assert res_no_key.status_code == 401

        # 3. Protected endpoint with invalid key should return 401
        res_wrong_key = client.get("/projects", headers={"X-API-Key": "wrong"})
        assert res_wrong_key.status_code == 401

        # 4. Protected endpoint with correct key should succeed
        res_valid_key = client.get("/projects", headers={"X-API-Key": "supersecretkey"})
        assert res_valid_key.status_code == 200

        # Reset state
        main.REQUIRED_API_KEY = None
