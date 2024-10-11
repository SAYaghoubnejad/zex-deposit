import time

from web3 import Web3
import json

from config import INFURA_KEY

# Connect to Infura or another Ethereum node
infura_url = f"https://sepolia.infura.io/v3/{INFURA_KEY}"
web3 = Web3(Web3.HTTPProvider(infura_url))

# Check connection
if not web3.is_connected():
    raise ConnectionError("Failed to connect to Ethereum node")

# ERC20 Transfer event signature (hashed)
transfer_event_signature = web3.keccak(text="Transfer(address,address,uint256)").hex()

# List of addresses to filter for
address_list = [
    "0x094248eb440b6ebb9e54FcbD8B8ad18B037E6885",
]

# Function to monitor and filter transfer events
def handle_transfer_event(event):
    receipt = web3.eth.get_transaction_receipt(event['transactionHash'])
    for log in receipt['logs']:

        if len(log['topics']) == 0:
            continue  # Skip this event if data is invalid

        # Check if the log matches the transfer event signature
        if log['topics'][0].hex() == transfer_event_signature:
            # Decode the log and extract relevant data
            token_address = web3.to_checksum_address(log['address'])
            from_address = web3.to_checksum_address(log['topics'][1].hex()[26:])
            to_address = web3.to_checksum_address(log['topics'][2].hex()[26:])
            # Ensure that the data field is not empty or just '0x'
            if log['data'] == '0x' or len(log['data']) == 0:
                continue  # Skip this event if data is invalid

            value = int(log['data'].hex().replace("0x", ""))

            # Filter based on destination address
            if to_address in address_list:
                print(f"Transfer detected to address in list: {to_address}")
                print(f"From: {from_address}, To: {to_address}, Value: {value} of {token_address}")

# Subscribe to Transfer events
def log_loop(event_filter, poll_interval):
    while True:
        for event in event_filter.get_new_entries():
            handle_transfer_event(event)
        time.sleep(poll_interval)

def main():
    # Create a filter for ERC20 Transfer events across the whole blockchain
    transfer_filter = web3.eth.filter({
        "fromBlock": "latest",
        "topics": [transfer_event_signature]
    })

    # Start monitoring the transfer events
    log_loop(transfer_filter, 2)

if __name__ == "__main__":
    main()
