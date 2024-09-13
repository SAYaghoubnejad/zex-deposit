import os
import json

from enum import Enum
from bitcoinutils.utils import to_satoshis
from dotenv import load_dotenv

load_dotenv()

with open(os.getenv("ZBTC_VALIDATED_IPS"),"r") as reader:
    valid_ips = json.loads(reader.read())
    VALIDATED_IPS = {}
    for ip in valid_ips:
        VALIDATED_IPS[ip]= [
        "/pyfrost/v1/dkg/round1",
        "/pyfrost/v1/dkg/round2",
        "/pyfrost/v1/dkg/round3",
        "/pyfrost/v1/sign",
        "/pyfrost/v1/generate-nonces"
        ]


PRIVATE_KEY = int(os.getenv("ZBTC_PRIVATE_KEY"))

ZBTC_CONTRACT_ADDRESS = os.getenv("ZBTC_CONTRACT_ADDRESS")
FEE_AMOUNT = to_satoshis(0.00003000)

BTC_NETWORK = "testnet"
BASE_URL = "https://mempool.space/testnet/api"

MPC_ADDRESS = os.getenv("ZBTC_MPC_ADDRESS")


# Define an enum class
class DepositType(Enum):
    BRIDGE = 1
    WITHDRAW = 2
