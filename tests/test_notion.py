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


def test_create_page_calls_pages_create():
    with patch("common.notion.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.pages.create.return_value = {"id": "new-page-id"}

        api = NotionApi(token="t")
        properties = {"Name": {"title": [{"text": {"content": "test"}}]}}
        resp = api.create_page("db-id", properties)

        assert resp.status_code == 200
        assert resp.json()["id"] == "new-page-id"
        mock_client.pages.create.assert_called_once_with(
            parent={"database_id": "db-id"}, properties=properties
        )


def test_append_block_children_calls_blocks_children_append():
    with patch("common.notion.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.blocks.children.append.return_value = {"results": []}

        api = NotionApi(token="t")
        blocks = [{"type": "paragraph"}]
        resp = api.append_block_children("page-id", blocks)

        assert resp.status_code == 200
        mock_client.blocks.children.append.assert_called_once_with(
            block_id="page-id", children=blocks
        )
