import json
import requests
import websocket
import uuid
from requests.auth import HTTPBasicAuth
from requests.compat import urljoin, urlencode
from comfy_api_simplified.comfy_workflow_wrapper import ComfyWorkflowWrapper


class ComfyApiWrapper:
    def __init__(
        self, url: str = "http://127.0.0.1:8188", user: str = "", password: str = ""
    ):
        self.url = url
        self.auth = None
        url_without_protocol = url.split("//")[-1]

        if user:
            self.auth = HTTPBasicAuth(user, password)
            ws_url_base = f"ws://{user}:{password}@{url_without_protocol}"
        else:
            ws_url_base = f"ws://{url_without_protocol}"
        self.ws_url = urljoin(ws_url_base, "/ws?clientId={}")

    def queue_prompt(self, prompt: dict, client_id: str = None):
        p = {"prompt": prompt}
        if client_id:
            p["client_id"] = client_id
        data = json.dumps(p).encode("utf-8")
        resp = requests.post(urljoin(self.url, "/prompt"), data=data, auth=self.auth)
        print(f"{resp.status_code}: {resp.reason}")
        if resp.status_code == 200:
            return resp.json()

    def queue_prompt_and_wait(self, prompt: dict):
        client_id = str(uuid.uuid4())
        prompt_id = self.queue_prompt(prompt, client_id)["prompt_id"]
        ws = websocket.WebSocket()
        ws.connect(self.ws_url.format(client_id))
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message["type"] == "crystools.monitor":
                    continue
                print(message)
                if message["type"] == "execution_error":
                    data = message["data"]
                    if data["prompt_id"] == prompt_id:
                        print(data[:200])
                        return None
                if message["type"] == "executing":
                    data = message["data"]
                    if data["node"] is None and data["prompt_id"] == prompt_id:
                        return prompt_id

    def queue_and_wait_images(
        self, prompt: ComfyWorkflowWrapper, output_node_title: str
    ):
        prompt_id = self.queue_prompt_and_wait(prompt)
        history = self.get_history(prompt_id)
        image_node_id = prompt.get_node_id(output_node_title)
        images = history[prompt_id]["outputs"][image_node_id]["images"]
        return {
            image["filename"]: self.get_image(
                image["filename"], image["subfolder"], image["type"]
            )
            for image in images
        }

    def get_history(self, prompt_id):
        url = urljoin(self.url, f"/history/{prompt_id}")
        resp = requests.get(url, auth=self.auth)
        if resp.status_code == 200:
            return resp.json()

    def get_image(self, filename, subfolder, folder_type):
        params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url = urljoin(self.url, f"/view?{urlencode(params)}")
        print(url)
        resp = requests.get(url, auth=self.auth)
        print(f"{resp.status_code}: {resp.reason}")
        if resp.status_code == 200:
            return resp.content

    def upload_image(self, filename: str, subfolder: str = "default_unload_folder"):
        url = urljoin(self.url, "/upload/image")
        serv_file = filename.split("/")[-1]
        data = {"subfolder": subfolder}
        print(url)
        print(serv_file)
        files = {"image": (serv_file, open(filename, "rb"))}
        resp = requests.post(url, files=files, data=data, auth=self.auth)
        print(f"{resp.status_code}: {resp.reason}, {resp.text}")
        if resp.status_code == 200:
            return resp.json()
