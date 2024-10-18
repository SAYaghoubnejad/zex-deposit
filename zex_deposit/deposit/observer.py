import asyncio

from web3 import AsyncWeb3
from eth_typing import BlockNumber, ChecksumAddress, ChainId


from utils.transfer_decoder import (
    decode_transfer_tx,
    NotRecognizedSolidityFuncError,
)
from .utils import async_web3_factory, filter_blocks
from .db.models import Transfer, TransferStatus
from .db.transfer import (
    get_latest_block_observed,
    insert_many_transfers,
)
from .db.address import insert_new_adderss_to_db, get_active_address
from .config import (
    BATCH_BLOCK_NUMBER_SIZE,
    MAX_DELAY_PER_BLOCK_BATCH,
    CHAINS_CONFIG,
    ChainConfig,
)


async def get_block_batches(
    from_block: BlockNumber | int, latest_block: BlockNumber | int
) -> list[tuple[BlockNumber, ...]]:
    block_batches = [
        tuple(
            BlockNumber(j)
            for j in range(i, min(latest_block + 1, i + BATCH_BLOCK_NUMBER_SIZE + 1))
        )
        for i in range(from_block, latest_block + 1, BATCH_BLOCK_NUMBER_SIZE)
    ]
    return block_batches


async def extract_transfer_from_block(
    w3: AsyncWeb3, block_number: BlockNumber, chain_id: ChainId, **kwargs
) -> list[Transfer]:
    print(f"Observing block number {block_number} start")
    block = await w3.eth.get_block(block_number, full_transactions=True)
    result = []
    for tx in block.transactions:  # type: ignore
        try:
            decoded_input = decode_transfer_tx(tx.input.hex())
            result.append(
                Transfer(
                    tx_hash=tx.hash.hex(),
                    block_number=block_number,
                    chain_id=chain_id,
                    to=decoded_input._to,
                    value=decoded_input._value,
                    status=TransferStatus.PENDING,
                    token=tx.to,
                )
            )
        except NotRecognizedSolidityFuncError as _:
            ...
    print(f"Observing block number {block_number} end")
    return result


async def filter_transfers(
    transfers: list[Transfer], valid_addresses: set[ChecksumAddress]
) -> tuple[Transfer, ...]:
    return tuple(filter(lambda transfer: transfer.to in valid_addresses, transfers))


async def observe_deposit(chain: ChainConfig):
    last_block_observed = await get_latest_block_observed(chain.chain_id)
    while True:
        await insert_new_adderss_to_db()
        w3 = await async_web3_factory(chain)
        latest_block = await w3.eth.get_block_number()
        if last_block_observed is not None and last_block_observed == latest_block:
            print("block already observed continue")
            await asyncio.sleep(MAX_DELAY_PER_BLOCK_BATCH)
            continue
        elif last_block_observed is None:
            last_block_observed = latest_block
        block_batches = await get_block_batches(last_block_observed, latest_block)
        for blocks_number in block_batches:
            transfers = await filter_blocks(
                w3, blocks_number, extract_transfer_from_block, chain_id=chain.chain_id
            )
            valid_addresses = await get_active_address()
            valid_transfers = await filter_transfers(transfers, valid_addresses)
            print(list(valid_transfers))
            if len(valid_transfers) != 0:
                await insert_many_transfers(valid_transfers)
        last_block_observed = latest_block + 1


if __name__ == "__main__":
    asyncio.run(observe_deposit(CHAINS_CONFIG["11155111"]))
