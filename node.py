import os
import logging
import sys

from flask import Flask
from urllib.parse import urlparse
from pyfrost.network.node import Node
from abstracts import NodesInfo, NodeDataManager, NodeValidators
from config import PRIVATE_KEY, NODE_ID


def run_node(node_id: int) -> None:
    data_manager = NodeDataManager(
        f"dkg_keys.json",
        f"nonces.json",
    )
    nodes_info = NodesInfo()
    node = Node(
        data_manager,
        str(node_id),
        PRIVATE_KEY,
        nodes_info,
        NodeValidators.caller_validator,
        NodeValidators.data_validator,
    )
    node_info = nodes_info.lookup_node(str(node_id))
    app = Flask(__name__)
    app.register_blueprint(node.blueprint, url_prefix="/pyfrost")
    parsed_url = urlparse(node_info["socket"])
    app.run(
        host="0.0.0.0",
        port=int(parsed_url.port),
        debug=False,
        threaded=True,
        use_reloader=False,
    )


if __name__ == "__main__":
    file_path = "logs"
    file_name = f"node{NODE_ID}.log"
    log_formatter = logging.Formatter(
        "%(asctime)s - %(message)s",
    )
    root_logger = logging.getLogger()
    if not os.path.exists(file_path):
        os.mkdir(file_path)
    with open(f"{file_path}/{file_name}", "w"):
        pass
    file_handler = logging.FileHandler(f"{file_path}/{file_name}")
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.DEBUG)
    sys.set_int_max_str_digits(0)

    try:
        run_node(NODE_ID)
    except KeyboardInterrupt:
        pass
