
# Zellular BTC

Zellular BTC is a decentralized bridge from Bitcoin network to EVM-compatible chains hosted on eigenlayer and secured via resktaing. It uses [FROST](https://eprint.iacr.org/2020/852.pdf) protocol to enable EigenLayer nodes own an MPC wallet in a decentralized way using Schnorr Threshold Signatures.

This [tutorial](https://github.com/zellular-xyz/zbtc/wiki/How-to-Use-ZBTC) will guide you through using the PoC version of ZBTC on the EigenLayer Holesky testnet to bridge BTC from Bitcoin testnet3 to the Ethereum Holesky test network and back.

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
# File path of the encrypted ECDSA key used for the ZBTC node private key.
ZBTC_ECDSA_KEY_FILE=[home-or-path-to-keys]/.eigenlayer/operator_keys/zbtc.ecdsa.key.json

# Password used to decrypt the ECDSA key file.
ZBTC_ECDSA_KEY_PASSWORD=
```

## Run

To run nodes, execute the following command:

```bash
$ python node.py
```

Next, to initiate a Distributed Key Generation (DKG) for the MPC wallet, run:

```bash
$ python dkg.py [threshold] [n] BTC mpc_wallet 
```

To set up a DKG for generating signatures for the EVM-side contract, use:

```bash
$ python dkg.py [threshold] [n] ETH ethereum 
```

To run the signature aggregator, which acts as a client for the user, run:

```bash
$ python sa.py
```
