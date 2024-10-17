from pydantic import BaseModel, Field
from datetime import datetime
from typing import TypeAlias
from eth_typing import BlockNumber, ChecksumAddress, ChainId
from enum import Enum, auto


class TransferStatus(Enum):
    PENDING = auto()
    FINALIZED = auto()
    VERIFIED = auto()
    REORG = auto()
    REJECTED = auto()


Value: TypeAlias = int
Timestamp: TypeAlias = int | float
UserId: TypeAlias = int
TxHash: TypeAlias = str

class Transfer(BaseModel):
    tx_hash: TxHash
    status: TransferStatus
    chain_id: ChainId
    value: Value
    token: ChecksumAddress
    to: ChecksumAddress
    observed_at: Timestamp = Field(default_factory=lambda: datetime.now().timestamp())
    block_number: BlockNumber

    class Config:
        use_enum_values = True


class UserAddress(BaseModel):
    user_id: UserId
    address: ChecksumAddress
    is_active: bool = Field(default=True)
