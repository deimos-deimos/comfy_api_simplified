import json
import logging
import warnings
from pathlib import Path
from typing import Any, List, Union

from comfy_api_simplified.exceptions import NodeNotFoundError

_log = logging.getLogger(__name__)

class ComfyWorkflowWrapper(dict):
    def __init__(self, path_or_obj: Union[str, Path, dict]) -> None:
        """
        Initialize the ComfyWorkflowWrapper object.

        Args:
            path_or_obj (str | Path | dict): The path to the workflow file, or dict object.
        """
        if isinstance(path_or_obj, (str, Path)):
            with Path(path_or_obj).open('r', encoding='utf-8') as f:
                obj = json.load(f)
        else:
            obj = path_or_obj
        super().__init__(obj)

    def list_nodes(self) -> List[str]:
        """
        Get a list of node titles in the workflow.

        Returns:
            List[str]: A list of node titles.
        """
        return [node["_meta"]["title"] for node in super().values()]

    def set_node_param(self, title: str, param: str, value: Any) -> None:
        """
        Set the value of a parameter for a specific node.
        Mind that this method will change parameters for ALL nodes with the same title.
        If more than one node shares the title, a UserWarning is emitted.

        Args:
            title (str): The title of the node.
            param (str): The name of the parameter.
            value: The value to set.

        Raises:
            NodeNotFoundError: If the node is not found.
        """
        nodes_changed = 0
        for node in super().values():
            if node["_meta"]["title"] == title:
                _log.info(f"Setting parameter '{param}' of node '{title}' to '{value}'")
                node["inputs"][param] = value
                nodes_changed += 1
        if nodes_changed == 0:
            raise NodeNotFoundError(f"Node '{title}' not found.")
        if nodes_changed > 1:
            warnings.warn(
                f"set_node_param: {nodes_changed} nodes share the title '{title}'; "
                "all were updated. Use unique node titles to avoid ambiguity.",
                stacklevel=2,
            )

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
            NodeNotFoundError: If the node is not found.
        """
        for node in super().values():
            if node["_meta"]["title"] == title:
                return node["inputs"][param]
        raise NodeNotFoundError(f"Node '{title}' not found.")

    def get_node_id(self, title: str) -> str:
        """
        Get the ID of a specific node.

        Args:
            title (str): The title of the node.

        Returns:
            str: The ID of the node.

        Raises:
            NodeNotFoundError: If the node is not found.
        """
        for id, node in super().items():
            if node["_meta"]["title"] == title:
                return id
        raise NodeNotFoundError(f"Node '{title}' not found.")

    def save_to_file(self, path: Union[str, Path]) -> None:
        """
        Save the workflow to a file.

        Args:
            path (str | Path): The path to save the workflow file.
        """
        workflow_str = json.dumps(self, indent=4)
        with Path(path).open("w+", encoding="utf-8") as f:
            f.write(workflow_str)
