from notion_client import Client, APIResponseError


class _FakeResp:
    """讓 SDK 結果具備 ledger_analysis.py 期望的 .status_code 與 .json() 介面。"""

    def __init__(self, status, data):
        self.status_code = status
        self._data = data

    def json(self):
        return self._data

    @property
    def text(self):
        import json
        return json.dumps(self._data, ensure_ascii=False)


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

    def update_database_schema(self, db_id, properties):
        try:
            data = self.client.databases.update(
                database_id=db_id, properties=properties
            )
            return _FakeResp(200, data)
        except APIResponseError as e:
            return _FakeResp(getattr(e, "status", 500), {"error": str(e)})

    def get_property_names_by_type(self, db_id, types):
        db = self.client.databases.retrieve(database_id=db_id)
        out = {}
        for name, prop in db["properties"].items():
            if prop["type"] in types and prop["type"] not in out:
                out[prop["type"]] = name
        return out

    def check_record_exists(self, db_id, title_prop_name, value):
        resp = self.client.databases.query(
            database_id=db_id,
            filter={"property": title_prop_name, "title": {"equals": value}},
        )
        return len(resp["results"]) > 0
