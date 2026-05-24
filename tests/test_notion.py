from unittest.mock import patch, MagicMock
import httpx
from notion_client import APIResponseError
from notion_client.errors import APIErrorCode
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
            response=httpx.Response(401, headers={}),
            message="Unauthorized",
            code=APIErrorCode.Unauthorized,
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


def test_get_property_names_by_type_filters_properties():
    with patch("common.notion.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.databases.retrieve.return_value = {
            "properties": {
                "名目": {"type": "title"},
                "備註": {"type": "rich_text"},
                "Paul": {"type": "number"},
            }
        }

        api = NotionApi(token="t")
        result = api.get_property_names_by_type("db-id", ["title", "rich_text"])

        assert result == {"title": "名目", "rich_text": "備註"}


def test_check_record_exists_returns_true_when_results_nonempty():
    with patch("common.notion.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.databases.query.return_value = {
            "results": [{"id": "found"}]
        }

        api = NotionApi(token="t")
        exists = api.check_record_exists("db-id", "名目", "202504")

        assert exists is True
        mock_client.databases.query.assert_called_once_with(
            database_id="db-id",
            filter={"property": "名目", "title": {"equals": "202504"}},
        )


def test_check_record_exists_returns_false_when_results_empty():
    with patch("common.notion.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.databases.query.return_value = {"results": []}

        api = NotionApi(token="t")
        assert api.check_record_exists("db-id", "名目", "notfound") is False


def test_update_database_schema_calls_databases_update():
    with patch("common.notion.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.databases.update.return_value = {"id": "db-id"}

        api = NotionApi(token="t")
        properties = {"娛樂": {"number": {"format": "number"}}}
        resp = api.update_database_schema("db-id", properties)

        assert resp.status_code == 200
        mock_client.databases.update.assert_called_once_with(
            database_id="db-id", properties=properties
        )


def test_update_database_schema_returns_error_response_when_api_fails():
    with patch("common.notion.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        err = APIResponseError(
            response=httpx.Response(400, headers={}),
            message="Invalid schema",
            code=APIErrorCode.ValidationError,
        )
        mock_client.databases.update.side_effect = err

        api = NotionApi(token="bad")
        resp = api.update_database_schema("db-id", {})

        assert resp.status_code == 400
        assert "Invalid schema" in resp.json()["error"]


def test_fake_resp_text_returns_json_string():
    from common.notion import _FakeResp
    resp = _FakeResp(200, {"hello": "世界"})
    assert resp.text == '{"hello": "世界"}'
