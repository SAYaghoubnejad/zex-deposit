
# Zellular BTC

Zellular BTC is a decentralized bridge from Bitcoin network to EVM-compatible chains hosted on eigenlayer and secured via resktaing. It uses [FROST](https://eprint.iacr.org/2020/852.pdf) protocol to enable EigenLayer nodes own an MPC wallet in a decentralized way using Schnorr Threshold Signatures.

[This tutorial](/wiki/How-to-Use-ZBTC) will guide you through using the PoC version of ZBTC on the EigenLayer Holesky testnet to bridge BTC from Bitcoin testnet3 to the Ethereum Holesky test network and back.

## Setup

- Activate the Python virtual environment and install required packages:

```bash
$ git clone https://github.com/zellulr-xyz/zbtc.git
$ cd zbtc
$ virtualenv -p python3.10 venv
$ source venv/bin/activate
(venv) $ pip install -r requirements.txt
```

> [!TIP]
> Python version `3.10` or above is required.

- Set up the `.env` file using the provided `.env.example` as a reference:

```bash
$ cp .env.example .env
```

Then modify the `.env` file with the appropriate parameters:

```
# Path to the file containing validated IP addresses to request dkg and signature:
ZBTC_VALIDATED_IPS=./validated_ips.json

# Private key for the ZBTC node (in integer format)
ZBTC_PRIVATE_KEY=94337664340063690438010829915800780946232589158282044690319564900000952004167

# ZBTC smart contract address
ZBTC_CONTRACT_ADDRESS=0x0323C15f879C8c8F024154BF5179c75e2eb9cAaD

# Bitcoin MPC (Multi-Party Computation) address
ZBTC_MPC_ADDRESS=tb1p0wm4lp4enjz47y7qzne288gj9keffed58mmjz7exr0wlw02duq3ssw7y20
```

## Run

To run nodes, execute the following command:

```bash
$ python node.py [node_id]
```

Next, to initiate a Distributed Key Generation (DKG) for the MPC wallet, run:

```bash
$ python dkg.py [number of nodes] [threshold] [n] BTC mpc_wallet 
```

To set up a DKG for generating signatures for the EVM-side contract, use:

```bash
$ python dkg.py [number of nodes] [threshold] [n] ETH ethereum 
```

To run the signature aggregator, which acts as a client for the user, run:

```bash
$ python sa.py [number of nodes]
```
