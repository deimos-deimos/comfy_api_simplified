class ComfyApiError(Exception):
    """Raised when a ComfyUI HTTP request fails (non-200 response)."""


class NodeNotFoundError(ValueError):
    """Raised when no workflow node with the requested title exists.

    Subclasses ValueError for backward compatibility with code that
    catches ValueError from set_node_param / get_node_param / get_node_id.
    """
