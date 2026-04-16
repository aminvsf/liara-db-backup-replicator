from json import JSONDecodeError

import requests
from requests import RequestException

from src.config import config
from src.liara.exceptions import LiaraAPIError


class LiaraAPI:

    def __init__(self, token, team_id=None, api_url=None):
        self.token = token
        self.team_id = team_id
        self.api_url = api_url or "https://api.liara.ir/v1"

    def fetch(self, *, path, key, method="GET"):
        try:
            response = getattr(requests, method.lower())(
                "%s/%s" % (self.api_url.rstrip("/"), path.lstrip("/")),
                params=(
                    {
                        "teamID": self.team_id,
                    }
                    if self.team_id
                    else None
                ),
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return key(data) if callable(key) else data[key]

        except RequestException as exc:
            raise LiaraAPIError(
                (
                    "Failed to communicate with the Liara API: %s"
                    "\n"
                    "Please check your network connection or contact Liara support."
                )
                % exc
            )
        except (JSONDecodeError, KeyError):
            raise LiaraAPIError(
                "Received an invalid response from the Liara API. Try again in "
                "a few minutes or contact Liara support."
            )


liara_api = LiaraAPI(
    token=config.liara.api_token,
    team_id=config.liara.team_id,
    api_url=config.liara.api_url,
)
