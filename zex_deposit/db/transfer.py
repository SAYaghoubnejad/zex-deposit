from typing import Iterable

from pymongo import ASCENDING, DESCENDING
from eth_typing import ChainId

from .models import BlockNumber, TransferStatus, Transfer
from .database import transaction_collection


async def insert_transfer(transfer: Transfer):
    await transaction_collection.insert_one(transfer.model_dump())


async def insert_many_transfers(transfers: Iterable[Transfer]):
    await transaction_collection.insert_many(
        transfer.model_dump() for transfer in transfers
    )


async def find_transactions_by_status(
    status: TransferStatus,
) -> list[Transfer]:
    res = []
    async for transaction in transaction_collection.find({"status": status.value}):
        res.append(Transfer(**transaction))
    return res


async def update_transaction_status(tx_hash, new_status):
    await transaction_collection.update_one(
        {"tx_hash": tx_hash}, {"$set": {"status": new_status}}
    )


async def delete_transaction(tx_hash):
    await transaction_collection.delete_one({"tx_hash": tx_hash})


async def to_finalized(
    finalized_block_number: BlockNumber,
    tx_hashes: list[str],
):
    query = {
        "block_number": {"$lte": finalized_block_number},
        "status": TransferStatus.PENDING.value,
        "tx_hash": {"$in": tx_hashes},
    }

    update = {"$set": {"status": TransferStatus.FINALIZED.value}}

    _ = await transaction_collection.update_many(query, update)


async def to_reorg(
    from_block: BlockNumber, to_block: BlockNumber, finalized_tx_hashes: list[str]
):
    query = {
        "block_number": {"$lte": to_block, "$gte": from_block},
        "status": TransferStatus.PENDING.value,
        "tx_hash": {"$nin": finalized_tx_hashes},
    }
    update = {"$set": {"status": TransferStatus.REORG.value}}
    _ = await transaction_collection.update_many(query, update)


async def get_pending_transfers_block_number(
    chain_id: ChainId, finalized_block_number: BlockNumber
) -> list[BlockNumber]:
    query = {
        "chain_id": chain_id.value,
        "status": TransferStatus.PENDING.value,
        "block_number": {"$lte": finalized_block_number},
    }
    block_numbers = set()
    async for record in transaction_collection.find(
        query,
        sort=[("block_number", ASCENDING)],
    ):
        block_numbers.add(BlockNumber(record["block_number"]))
    return list(block_numbers)


async def get_latest_block_observed(chain_id: ChainId) -> BlockNumber | None:
    query = {"chain_id": chain_id.value}
    result = await transaction_collection.find_one(
        query,
        sort=[("block_number", DESCENDING)],
    )
    if result:
        return BlockNumber(result["block_number"])
    return None
