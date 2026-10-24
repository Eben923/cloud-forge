from unittest.mock import MagicMock, patch
import pytest


def test_reject_invalid_image_tag_name(client):
    project_res = client.post("/projects", json={"name": "Deploy Test"})
    project_id = project_res.json()["id"]

    # Invalid image tag should fail fast with 400
    response = client.post(
        f"/projects/{project_id}/deployments",
        params={"image_name": "malicious/image:latest"},
    )
    assert response.status_code == 400
    assert "Invalid image name" in response.json()["detail"]


@patch("docker.from_env")
def test_successful_sandboxed_deployment_execution(mock_docker, client):
    project_res = client.post("/projects", json={"name": "Execution Test"})
    project_id = project_res.json()["id"]
    valid_tag = f"cloudforge-project-{project_id}:1234567890ab"

    # Configure Docker client mock
    mock_client = MagicMock()
    mock_docker.return_value = mock_client
    mock_container = MagicMock()
    mock_container.status = "exited"
    mock_container.attrs = {"State": {"ExitCode": 0}}
    mock_container.logs.return_value = b"Hello from Cloud Forge!\n"
    mock_client.containers.run.return_value = mock_container

    response = client.post(
        f"/projects/{project_id}/deployments",
        params={"image_name": valid_tag},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert "Hello from Cloud Forge!" in data["logs"]

    # Verify that strict security isolation parameters were passed to docker.run
    mock_client.containers.run.assert_called_once()
    _, kwargs = mock_client.containers.run.call_args
    assert kwargs["network_disabled"] is True
    assert kwargs["mem_limit"] == "128m"
    assert kwargs["nano_cpus"] == 500_000_000
    assert kwargs["pids_limit"] == 64
    assert kwargs["read_only"] is True
    assert kwargs["cap_drop"] == ["ALL"]
    assert kwargs["user"] == "nobody"
