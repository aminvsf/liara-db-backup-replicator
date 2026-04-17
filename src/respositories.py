from domains import Database
from liara.api import liara_api as default_liara_api


class DatabaseRepository:

    def __init__(self, liara_api=None):
        self.liara_api = liara_api or default_liara_api

    def list(self):
        return self.liara_api.fetch(
            path="/databases",
            key=lambda data: [
                Database(id=d["_id"], name=d["hostname"]) for d in data["databases"]
            ],
        )
