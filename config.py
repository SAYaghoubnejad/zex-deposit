import os
import json
import hashlib

from enum import Enum
from dotenv import load_dotenv

from web3 import Account
from pyfrost.crypto_utils import code_to_pub
from bitcoinutils.keys import PublicKey
from eigensdk.crypto.bls import attestation

load_dotenv()

def get_taproot_address(public_key):
    public_key = code_to_pub(public_key)
    x_hex = hex(public_key.x)[2:].zfill(64)
    y_hex = hex(public_key.y)[2:].zfill(64)
    prefix = "02" if int(y_hex, 16) % 2 == 0 else "03"
    compressed_pubkey = prefix + x_hex
    public_key = PublicKey(compressed_pubkey)
    taproot_address = public_key.get_taproot_address()
    return taproot_address

def generate_node_id(eth_address: str) -> str:
    eth_address = eth_address.replace("0x","")
    node_id_bytes = bytes.fromhex(eth_address)
    sha256_hash = hashlib.sha256(node_id_bytes).digest()
    sha256_hex = sha256_hash.hex()
    node_id = '0x' + sha256_hex
    return int(node_id, 16)

valid_ips = json.loads(os.getenv("ZBTC_VALIDATED_IPS"))
VALIDATED_IPS = {}
for ip in valid_ips:
    VALIDATED_IPS[ip]= [
    "/pyfrost/v1/dkg/round1",
    "/pyfrost/v1/dkg/round2",
    "/pyfrost/v1/dkg/round3",
    "/pyfrost/v1/sign",
    "/pyfrost/v1/generate-nonces"
    ]


ecdsa_key_store_path: str = os.getenv("ZBTC_ECDSA_KEY_FILE")
ecdsa_key_password: str = os.getenv("ZBTC_ECDSA_KEY_PASSWORD")
with open(ecdsa_key_store_path, 'r') as f:
    encrypted_json: str = json.loads(f.read())

bls_key_store_path = os.getenv("ZBTC_BLS_KEY_FILE")
bls_key_password = os.getenv("ZBTC_BLS_KEY_PASSWORD")
bls_key_pair: attestation.KeyPair = attestation.KeyPair.read_from_file(bls_key_store_path, bls_key_password)

ecdsa_private_key: str = Account.decrypt(encrypted_json, ecdsa_key_password)
PRIVATE_KEY = int(ecdsa_private_key.hex(),16)
NODE_ID = generate_node_id(Account.from_key(ecdsa_private_key).address.lower())

CONTRACT_ADDRESS = os.getenv("ZBTC_CONTRACT_ADDRESS")
FEE_AMOUNT = os.getenv("ZBTC_FEE_AMOUNT")
BTC_NETWORK = os.getenv("ZBTC_BTC_NETWORK")
BASE_URL = os.getenv("ZBTC_RPC_URL")
PORT = os.getenv("ZBTC_PORT")

DATA_PATH = os.getenv("ZBTC_DATA_PATH")
if not os.path.exists(DATA_PATH):
    os.makedirs(DATA_PATH)

dkg_data = {}
if os.path.exists("dkg_keys.json"):
    with open("dkg_keys.json", "r") as file:
        dkg_data = json.load(file)

MPC_ADDRESS = ""
for dkg in dkg_data.values():
    if dkg["key_type"] == "BTC":
        MPC_ADDRESS = get_taproot_address(dkg["dkg_public_key"]).to_string()



class DepositType(Enum):
    BRIDGE = 1
    WITHDRAW = 2
