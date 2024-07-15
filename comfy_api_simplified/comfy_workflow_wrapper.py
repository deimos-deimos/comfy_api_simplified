import json
import logging
from typing import Any, List

_log = logging.getLogger(__name__)

class ComfyWorkflowWrapper(dict):
    def __init__(self, path: str):
        """
        Initialize the ComfyWorkflowWrapper object.

        Args:
            path (str): The path to the workflow file.
        """
        with open(path) as f:
            workflow_str = f.read()
        super().__init__(json.loads(workflow_str))

    def list_nodes(self) -> List[str]:
        """
        Get a list of node titles in the workflow.

        Returns:
            List[str]: A list of node titles.
        """
        return [node["_meta"]["title"] for node in super().values()]

    def set_node_param(self, title: str, param: str, value):
        """
        Set the value of a parameter for a specific node.
        Mind that this method will change parameters for ALL nodes with the same title.

        Args:
            title (str): The title of the node.
            param (str): The name of the parameter.
            value: The value to set.

        Raises:
            ValueError: If the node is not found.
        """
        smth_changed = False
        for node in super().values():
            if node["_meta"]["title"] == title:
                _log.info(f"Setting parameter '{param}' of node '{title}' to '{value}'")
                node["inputs"][param] = value
                smth_changed = True
        if not smth_changed:
            raise ValueError(f"Node '{title}' not found.")

    def get_node_param(self, title: str, param: str) -> Any:
        """
        Get the value of a parameter for a specific node.
        Mind that this method will return the value of the first node with this title.

        Args:
            title (str): The title of the node.
            param (str): The name of the parameter.

        Returns:
            The value of the parameter.

        Raises:
            ValueError: If the node is not found.
        """
        for node in super().values():
            if node["_meta"]["title"] == title:
                return node["inputs"][param]
        raise ValueError(f"Node '{title}' not found.")

    def get_node_id(self, title: str) -> str:
            """
            Get the ID of a specific node.

            Args:
                title (str): The title of the node.

            Returns:
                str: The ID of the node.

            Raises:
                ValueError: If the node is not found.
            """
            for id, node in super().items():
                if node["_meta"]["title"] == title:
                    return id
            raise ValueError(f"Node '{title}' not found.")

    def save_to_file(self, path: str):
        """
        Save the workflow to a file.

        Args:
            path (str): The path to save the workflow file.
        """
        workflow_str = json.dumps(self, indent=4)
        with open(path, "w+") as f:
            f.write(workflow_str)
