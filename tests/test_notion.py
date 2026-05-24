from unittest.mock import patch, MagicMock
import httpx
from notion_client import APIResponseError
from common.notion import NotionApi


def test_query_database_returns_response_with_json_method():
    with patch("common.notion.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.databases.query.return_value = {"results": [{"id": "page1"}]}

        api = NotionApi(token="fake-token")
        resp = api.query_database("db-id", {"filter": {"property": "x"}})

        assert resp.status_code == 200
        assert resp.json() == {"results": [{"id": "page1"}]}
        mock_client.databases.query.assert_called_once_with(
            database_id="db-id", filter={"property": "x"}
        )


def test_query_database_returns_error_response_when_api_fails():
    with patch("common.notion.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        err = APIResponseError(
            code="unauthorized",
            status=401,
            message="Unauthorized",
            headers=httpx.Headers(),
            raw_body_text="",
        )
        mock_client.databases.query.side_effect = err

        api = NotionApi(token="bad")
        resp = api.query_database("db-id", {})

        assert resp.status_code == 401
        assert "Unauthorized" in resp.json()["error"]
