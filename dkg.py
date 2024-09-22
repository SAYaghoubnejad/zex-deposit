import json

from pyfrost.crypto_utils import is_y_even, code_to_pub, Half_N
from pyfrost.network.dkg import Dkg
from pyfrost.network.sa import SA
from abstracts import NodesInfo
import logging
import time
import timeit
import sys
import os
import random
import asyncio


async def initiate_dkg(
    threshold: int, dkg_type: str, dkg_name: any
) -> None:
    nodes_info = NodesInfo()
    all_nodes = nodes_info.get_all_nodes()
    dkg = Dkg(nodes_info, default_timeout=50)

    # Just added for requesting nonce to get the node state whether a node is live or not.
    sa = SA(nodes_info, default_timeout=5)
    
    party = []
    node_state_responses = await sa.request_nonces(all_nodes,1)
    for node_id, data in node_state_responses.items():
        if data["status"] == "SUCCESSFUL":
            party.append(node_id)
    # Requesting DKG:
    now = timeit.default_timer()
    dkg_key = await dkg.request_dkg(threshold, party, dkg_type)
    if dkg_type == "BTC":
        is_even = is_y_even(code_to_pub(dkg_key["public_key"]))
        while not is_even:
            dkg_key = await dkg.request_dkg(threshold, party, dkg_type)
            is_even = is_y_even(code_to_pub(dkg_key["public_key"]))
    elif dkg_type == "ETH":
        is_gt_halfq = code_to_pub(dkg_key["public_key"]).x < Half_N
        while not is_gt_halfq:
            dkg_key = await dkg.request_dkg(threshold, party, dkg_type)
            is_gt_halfq = code_to_pub(dkg_key["public_key"]).x < Half_N
    then = timeit.default_timer()

    logging.info(f"Requesting DKG takes: {then - now} seconds.")
    logging.info(f'The DKG result is {dkg_key["result"]}')

    logging.info(f"DKG key: {dkg_key}")
    dkg_key["threshold"] = threshold
    dkg_key["number_of_nodes"] = len(party)
    dkg_file_path = "."
    dkg_file_name = "dkgs.json"
    if not os.path.exists(f"{dkg_file_path}/{dkg_file_name}"):
        os.mkdir(dkg_file_path) if not os.path.exists(dkg_file_path) else None
        data = {}
    else:
        with open(f"{dkg_file_path}/{dkg_file_name}", "r") as file:
            data = json.load(file)

    data[dkg_name] = dkg_key
    
    with open(f"{dkg_file_path}/{dkg_file_name}", "w") as file:
        json.dump(data, file, indent=4)


if __name__ == "__main__":
    file_path = "logs"
    file_name = "test.log"
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

    dkg_threshold = int(sys.argv[1])
    dkg_type = sys.argv[2]
    dkg_name = sys.argv[3]

    try:
        asyncio.run(
            initiate_dkg(
                dkg_threshold, dkg_type, dkg_name
            )
        )
    except KeyboardInterrupt:
        pass
