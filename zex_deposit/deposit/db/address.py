import requests

from eth_typing import ChecksumAddress
from web3 import Web3
from pymongo import DESCENDING

from deposit.config import (
    USER_DEPOSIT_BYTECODE_HASH,
    USER_DEPOSIT_FACTORY_ADDRESS,
    ZEX_BASE_URL,
    ZexPath,
)
from .database import address_collection
from .models import UserAddress, UserId


class UserNotExists(Exception):
    pass


async def get_active_address() -> set[ChecksumAddress]:
    res = set()
    async for address in address_collection.find({"is_active": True}):
        res.add(Web3.to_checksum_address(address["address"]))
    return res


async def get_last_user_id() -> UserId:
    result = await address_collection.find_one({}, sort=[("user_id", DESCENDING)])
    if result:
        return UserId(result["user_id"])
    raise UserNotExists()


async def insert_user_address(address: UserAddress):
    await address_collection.insert_one(address.model_dump())


async def insert_many_user_address(users_address: list[UserAddress]):
    await address_collection.insert_many(
        user_address.model_dump() for user_address in users_address
    )


def compute_create2_address(
    salt,
    deployer_address=USER_DEPOSIT_FACTORY_ADDRESS,
    bytecode_hash=USER_DEPOSIT_BYTECODE_HASH,
):
    """
    Computes the CREATE2 address for a contract deployment.

    :param deployer_address: The address of the deploying contract (factory).
    :param salt: A bytes32 value used as the salt in the CREATE2 computation.
    :param bytecode_hash: The bytecode hash of the contract to deploy.
    :return: The computed deployment address as a checksum address.
    """
    # Ensure deployer_address is in bytes format
    if isinstance(deployer_address, str):
        deployer_address = Web3.to_bytes(hexstr=deployer_address)  # type: ignore
    elif isinstance(deployer_address, bytes):
        deployer_address = deployer_address
    else:
        raise TypeError("deployer_address must be a string or bytes.")

    if len(deployer_address) != 20:
        raise ValueError("Invalid deployer address length; must be 20 bytes.")

    # Ensure salt is a 32-byte value
    if isinstance(salt, int):
        salt = salt.to_bytes(32, "big")
    elif isinstance(salt, str):
        salt = Web3.to_bytes(hexstr=salt)  # type: ignore
    elif isinstance(salt, bytes):
        salt = salt
    else:
        raise TypeError("salt must be an int, string, or bytes.")

    if len(salt) != 32:
        raise ValueError("Invalid salt length; must be 32 bytes.")

    # Ensure bytecode is in bytes format
    if isinstance(bytecode_hash, str):
        bytecode_hash = Web3.to_bytes(hexstr=bytecode_hash)  # type: ignore
    else:
        raise TypeError("bytecode must be a string or bytes.")

    # Prepare the data as per the CREATE2 formula
    data = b"\xff" + deployer_address + salt + bytecode_hash

    # Compute the keccak256 hash of the data
    address_bytes = Web3.keccak(data)[12:]  # Take the last 20 bytes

    # Return the address in checksummed format
    return Web3.to_checksum_address(address_bytes)


def get_last_zex_user_id() -> UserId | None:
    try:
        res = requests.get(f"{ZEX_BASE_URL}/{ZexPath.LATEST_USER_URL.value}")
    except requests.RequestException:
        return
    else:
        return res.json().get("id")


def get_users_address_to_insert(
    first_to_compute: UserId, last_to_compute: UserId
) -> list[UserAddress]:
    users_address_to_insert = []
    for user_id in range(first_to_compute, last_to_compute + 1):
        users_address_to_insert.append(
            UserAddress(user_id=user_id, address=compute_create2_address(salt=user_id))
        )
    return users_address_to_insert


async def insert_new_adderss_to_db():
    last_zex_user_id = get_last_zex_user_id()
    if last_zex_user_id is None:
        return
    try:
        first_id_to_compute = await get_last_user_id() + 1
    except UserNotExists:
        first_id_to_compute = 0
    users_address_to_insert = get_users_address_to_insert(
        first_id_to_compute, last_zex_user_id
    )
    if len(users_address_to_insert) == 0:
        return
    await insert_many_user_address(users_address=users_address_to_insert)
