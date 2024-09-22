import logging
import threading
import time
import json
import os
from urllib.parse import urlparse
import requests

from bitcoinutils.keys import PublicKey
from web3 import Web3

from zbtc_utils import (
    get_simple_withdraw_tx,
    get_burned,
    get_deposit,
    get_withdraw_tx,
)
from pyfrost.network.abstract import Validators, DataManager, NodesInfo as BaseNodeInfo
from config import VALIDATED_IPS, CONTRACT_ADDRESS, MPC_ADDRESS,\
     NODES_PUBLIC_KEYS_FILE, DepositType, generate_node_id
from typing import Dict


class NodeDataManager(DataManager):
    def __init__(
        self,
        dkg_keys_file=f"./dkg_keys.json",
        nonces_file=f"./nonces.json",
    ) -> None:
        super().__init__()
        self.dkg_keys_file = dkg_keys_file
        self.nonces_file = nonces_file

        # Load data from files if they exist
        self.__dkg_keys = self._load_data(self.dkg_keys_file)
        self.__nonces = self._load_data(self.nonces_file)

    def _load_data(self, file_path):
        if os.path.exists(file_path):
            with open(file_path, "r") as file:
                return json.load(file)
        return {}

    def _save_data(self, file_path, data):
        with open(file_path, "w") as file:
            json.dump(data, file, indent=4)

    def set_nonce(self, nonce_public: str, nonce_private: str) -> None:
        self.__nonces[nonce_public] = nonce_private
        self._save_data(self.nonces_file, self.__nonces)

    def get_nonce(self, nonce_public: str):
        data = self._load_data(self.nonces_file)
        return data.get(nonce_public)

    def remove_nonce(self, nonce_public: str) -> None:
        self.__nonces = self._load_data(self.nonces_file)
        if nonce_public in self.__nonces:
            del self.__nonces[nonce_public]
            self._save_data(self.nonces_file, self.__nonces)

    def set_key(self, key, value) -> None:
        for dkg_id, dkg_data in list(self.__dkg_keys.items()):
            if dkg_data["key_type"] == value["key_type"]:
                del self.__dkg_keys[dkg_id]
                break
        self.__dkg_keys[key] = value
        self._save_data(self.dkg_keys_file, self.__dkg_keys)

    def get_key(self, key):
        data = self._load_data(self.dkg_keys_file)
        return data.get(key, {})

    def remove_key(self, key):
        self.__dkg_keys = self._load_data(self.dkg_keys_file)
        if key in self.__dkg_keys:
            del self.__dkg_keys[key]
            self._save_data(self.dkg_keys_file, self.__dkg_keys)


class NodeValidators(Validators):
    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def caller_validator(sender_ip: str, method: str):
        if method in VALIDATED_IPS.get(str(sender_ip), []):
            return True
        return False

    @staticmethod
    def data_validator(input_data: Dict):
        method = input_data["method"]
        data = input_data["data"]
        if method == "get_simple_withdraw_tx":
            from_address = data["from"]
            to_address = data["to"]
            fee = data["fee"]
            utxos = data["utxos"]
            tx_digest = bytes.fromhex(data["hash"])
            send_amount = data["send_amount"]
            tx, tx_digests = get_simple_withdraw_tx(
                from_address, utxos, to_address, send_amount, fee
            )
            if tx_digest in tx_digests:
                result = {
                    "input": input_data,
                    "sign_params": {"tx_digest": tx_digest.hex()},
                    "hash": tx_digest.hex(),
                }
                return result
            else:
                raise ValueError(f"Invalid Data: {input_data}")

        elif method == "get_withdraw_tx":
            rpc_url = "https://ethereum-holesky-rpc.publicnode.com"
            web3 = Web3(Web3.HTTPProvider(rpc_url))

            burn_tx_hash = data["burn_tx_hash"]
            tx_digest = bytes.fromhex(data["hash"])
            fee = data["fee"]
            utxos = data["utxos"]

            burned = get_burned(burn_tx_hash, web3, CONTRACT_ADDRESS)
            logging.debug(f"Burn Info: {burned}")
            send_amount = burned["amount"]
            single_spend_txid = burned["singleSpendTx"]
            single_spend_vout = 0
            to_address = burned["bitcoinAddress"]
            to_address = PublicKey(to_address)
            to_address = to_address.get_segwit_address().to_string()
            burner_address = burned["burner"]

            tx, tx_digests = get_withdraw_tx(
                MPC_ADDRESS,
                utxos,
                to_address,
                send_amount,
                fee,
                single_spend_txid,
                single_spend_vout,
                burner_address,
            )
            if tx_digest in tx_digests:
                result = {
                    "input": input_data,
                    "sign_params": {"tx_digest": tx_digest.hex()},
                    "hash": tx_digest.hex(),
                }
                return result
            else:
                raise ValueError(f"Invalid Data: {input_data}")

        elif method == "mint":
            tx_hash = data["tx"]
            bitcoin_address = data["bitcoin_address"]
            amount = data["amount"]
            to = data["to"]
            message_hash = data["hash"]

            deposit = get_deposit(
                tx_hash, bitcoin_address, MPC_ADDRESS, DepositType.BRIDGE
            )
            msg = Web3.solidity_keccak(
                ["uint256", "uint256", "address"],
                [
                    int(deposit["tx"], 16),
                    deposit["amount"],
                    Web3.to_checksum_address(deposit["eth_address"]),
                ],
            ).hex().replace("0x", "")
            if (
                msg == message_hash
                and int(tx_hash, 16) == int(deposit["tx"], 16)
                and deposit["amount"] == amount
                and to == Web3.to_checksum_address(deposit["eth_address"])
            ):
                result = {
                    "input": input_data,
                    "sign_params": {
                        "tx": int(deposit["tx"], 16),
                        "amount": deposit["amount"],
                        "to": Web3.to_checksum_address(deposit["eth_address"]),
                    },
                    "hash": msg,
                }
                return result
            else:
                raise ValueError(f"Invalid Data: {input_data}")

        else:
            raise NotImplementedError()


class NodesInfo(BaseNodeInfo):
    prefix = "/pyfrost"
    subgraph_url = (
        os.getenv("ZBTC_SUBGRAPH_URL")
    )

    def __init__(self):
        self.nodes = {}
        self._stop_event = threading.Event()
        self.sync_with_subgraph()
        self.start_sync_thread()

    def sync_with_subgraph(self):
        query = """
        query MyQuery {
          operators(where: {registered: true}) {
            id
            operatorId
            pubkeyG1_X
            pubkeyG1_Y
            pubkeyG2_X
            pubkeyG2_Y
            socket
            stake
          }
        }
        """
        try:
            response = requests.post(self.subgraph_url, json={'query': query})
            if response.status_code == 200:
                data = response.json()
                operators = data.get('data', {}).get('operators', [])
                self.nodes = self._convert_operators_to_nodes(operators)
                print("Synced with subgraph successfully.")
            else:
                print(f"Failed to fetch data from subgraph. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")

    def _convert_operators_to_nodes(self, operators):
        nodes_public_keys = self.get_file_content(NODES_PUBLIC_KEYS_FILE)
        nodes = {}
        for operator in operators:
            node_info = {
                "public_key": nodes_public_keys(operator["id"]),
                "pubkeyG1_X": operator["pubkeyG1_X"],
                "pubkeyG1_Y": operator["pubkeyG1_Y"],
                "pubkeyG2_X": operator["pubkeyG2_X"],
                "pubkeyG2_Y": operator["pubkeyG2_Y"],
                "socket": operator["socket"],
                "stake": operator["stake"],
            }
            nodes[str(generate_node_id(operator["id"]))] = node_info
        return nodes

    def _sync_periodically(self, interval):
        while not self._stop_event.is_set():
            time.sleep(interval)
            self.sync_with_subgraph()

    def get_file_content(self, source: str):
        """Get the json contents of a file"""
        if source.startswith('http://') or source.startswith('https://'):
            response = requests.get(source)
            response.raise_for_status()
            return response.json()
        elif os.path.isfile(source):
            with open(source, 'r', encoding='utf-8') as file:
                content = json.loads(file.read())
            return content
        else:
            raise ValueError("The source provided is neither a valid URL nor a valid file path.")        

    def start_sync_thread(self):
        sync_interval = 60  # 1 minute
        self._sync_thread = threading.Thread(
            target=self._sync_periodically, args=(sync_interval,)
        )
        self._sync_thread.daemon = True
        self._sync_thread.start()

    def stop_sync_thread(self):
        self._stop_event.set()
        self._sync_thread.join()

    def lookup_node(self, node_id: str = None):
        return self.nodes.get(node_id, {})

    def get_all_nodes(self, n: int = None):
        if n is None:
            n = len(self.nodes)
        return list(self.nodes.keys())[:n]
