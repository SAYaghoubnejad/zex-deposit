import os
import logging
import sys
import time

from urllib.parse import urlparse
from random import randbytes

from flask import Flask
from pyfrost.network.node import Node
from abstracts import NodesInfo, NodeDataManager, NodeValidators
from eigensdk.chainio.clients.builder import BuildAllConfig, build_all
from config import PRIVATE_KEY, NODE_ID, PORT, ecdsa_private_key, bls_key_pair

def register_operator(ecdsa_private_key, bls_key_pair) -> None:
    rpc_node = os.getenv("ZBTC_RPC_NODE")
    registry_coordinator = os.getenv("ZBTC_REGISTRY_COORDINATOR")
    operator_state_retriever = os.getenv("ZBTC_OPERATOR_STATE_RETRIEVER")

    config = BuildAllConfig(
        eth_http_url=rpc_node,
        registry_coordinator_addr=registry_coordinator,
        operator_state_retriever_addr=operator_state_retriever,
    )

    clients = build_all(config, ecdsa_private_key)
    clients.avs_registry_writer.register_operator_in_quorum_with_avs_registry_coordinator(
        operator_ecdsa_private_key=ecdsa_private_key,
        operator_to_avs_registration_sig_salt=randbytes(32),
        operator_to_avs_registration_sig_expiry=int(time.time()) + 60,
        bls_key_pair=bls_key_pair,
        quorum_numbers=[0],
        socket=os.getenv("ZBTC_REGISTER_SOCKET"),
    )


def run_node(node_id: int) -> None:
    data_manager = NodeDataManager(
        f"dkg_keys.json",
        f"nonces.json",
    )
    nodes_info = NodesInfo()
    
    if NODE_ID not in nodes_info.get_all_nodes():
        if os.getenv("ZBTC_REGISTER_OPERATOR") == 'true':
            register_operator(ecdsa_private_key, bls_key_pair)
            print("Operator registration transaction sent.")
        print("Operator not found in the nodes' list")
        sys.exit()
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
    assert (
        int(PORT) == int(parsed_url.port)
    ), f"The zbtc port in the .env file does not match the node port registered to Eigenlayer network."
    app.run(
        host="0.0.0.0",
        port=PORT,
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
