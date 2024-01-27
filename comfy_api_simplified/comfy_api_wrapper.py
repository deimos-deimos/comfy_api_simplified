import json
import requests
from requests.auth import HTTPBasicAuth
from requests.compat import urljoin


class ComfyApiWrapper:
    def __init__(
        self, url: str = "http://127.0.0.1:8188", user: str = "", password: str = ""
    ):
        self.url = url
        self.auth = None
        if user:
            self.auth = HTTPBasicAuth(user, password)

    def queue_prompt(self, prompt: dict):
        p = {"prompt": prompt}
        data = json.dumps(p).encode("utf-8")
        resp = requests.post(urljoin(self.url, "/prompt"), data=data, auth=self.auth)
        print(f"{resp.status_code}: {resp.reason}")
        if resp.status_code == 200:
            return resp.json()
