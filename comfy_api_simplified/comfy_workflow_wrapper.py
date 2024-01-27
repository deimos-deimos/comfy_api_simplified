import json


class ComfyWorkflowWrapper(dict):
    def __init__(self, path: str):
        with open(path) as f:
            workflow_str = f.read()
        super().__init__(json.loads(workflow_str))

    def list_nodes(self):
        return [node["_meta"]["title"] for node in super().values()]

    def set_node_param(self, title: str, param: str, value):
        for node in super().values():
            if node["_meta"]["title"] == title:
                node["inputs"][param] = value

    def get_node_param(self, title: str, param: str):
        for node in super().values():
            if node["_meta"]["title"] == title:
                return node["inputs"][param]

    def save_to_file(self, path: str):
        workflow_str = json.dumps(self, indent=4)
        with open(path, "w+") as f:
            f.write(workflow_str)
