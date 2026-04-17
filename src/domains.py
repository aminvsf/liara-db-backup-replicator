from dataclasses import dataclass

from liara.api import liara_api


@dataclass(frozen=True)
class Database:
    id: str
    name: str

    def get_backups(self):
        return liara_api.fetch(
            path=f"/databases/{self.id}/backups",
            key=lambda data: [
                Backup(database=self, name=b["name"]) for b in data["backups"]
            ],
        )


@dataclass(frozen=True)
class Backup:
    database: Database
    name: str

    @classmethod
    def from_s3_obj(cls, database, prefix, obj):
        return cls(database=database, name=obj["Key"][len(prefix):].rstrip(".enc"))

    def get_download_url(self):
        return liara_api.fetch(
            path=f"/databases/{self.database.id}/backups/{self.name}/download",
            key="link",
            method="POST",
        )
