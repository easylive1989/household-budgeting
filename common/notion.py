from notion_client import Client, APIResponseError


class _FakeResp:
    """讓 SDK 結果具備 ledger_analysis.py 期望的 .status_code 與 .json() 介面。"""

    def __init__(self, status, data):
        self.status_code = status
        self._data = data

    def json(self):
        return self._data


class NotionApi:
    def __init__(self, token):
        self.client = Client(auth=token)

    def query_database(self, db_id, filter_body):
        try:
            data = self.client.databases.query(database_id=db_id, **filter_body)
            return _FakeResp(200, data)
        except APIResponseError as e:
            return _FakeResp(getattr(e, "status", 500), {"error": str(e)})

    def create_page(self, db_id, properties):
        try:
            data = self.client.pages.create(
                parent={"database_id": db_id}, properties=properties
            )
            return _FakeResp(200, data)
        except APIResponseError as e:
            return _FakeResp(getattr(e, "status", 500), {"error": str(e)})

    def append_block_children(self, page_id, blocks):
        try:
            data = self.client.blocks.children.append(
                block_id=page_id, children=blocks
            )
            return _FakeResp(200, data)
        except APIResponseError as e:
            return _FakeResp(getattr(e, "status", 500), {"error": str(e)})
