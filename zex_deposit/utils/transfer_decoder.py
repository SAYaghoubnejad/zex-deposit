from dataclasses import dataclass
from typing import TypeAlias

from web3 import Web3
from eth_typing import ChecksumAddress

from utils.abi import ERC20_ABI


FunctionHash: TypeAlias = str


class NotRecognizedSolidityFuncError(Exception):
    pass


@dataclass
class SolidityFucntion:
    name: str
    inputs: list[dict[str, str]]


# Only transferFrom and transfer func input
@dataclass(kw_only=True)
class TransferTX:
    _to: ChecksumAddress
    _value: int
    _from: ChecksumAddress | None = None


def _parse_abi(abi: list[dict]) -> dict[FunctionHash, SolidityFucntion]:
    function_selectors = {}

    for func in abi:
        if func["type"] == "function":
            func_name = func["name"]
            input_types = [inp["type"] for inp in func["inputs"]]
            func_signature = f"{func_name}({','.join(input_types)})"
            func_selector = Web3.keccak(text=func_signature)[:4].hex()
            function_selectors[func_selector] = SolidityFucntion(
                name=func_name, inputs=func["inputs"]
            )
    return function_selectors


function_selectors = _parse_abi(ERC20_ABI)


def decode_transfer_tx(tx_input: str) -> TransferTX:
    function_selector = tx_input[:10]

    if function_selector in function_selectors:
        func_info = function_selectors[function_selector]
        func_inputs = func_info.inputs

        params_data = tx_input[10:]
        decoded_input_data = dict()
        for i, param in enumerate(func_inputs):
            param_type = param["type"]
            param_name = param["name"]
            param_data = params_data[i * 64 : (i + 1) * 64]
            if param_type == "address":
                param_value = "0x" + param_data[-40:]
                param_value = Web3.to_checksum_address(param_value)

            elif param_type.startswith("uint"):
                param_value = int(param_data, 16)
            else:
                param_value = param_data

            decoded_input_data[param_name] = param_value
        decoded_tx_input = TransferTX(**decoded_input_data)
        return decoded_tx_input
    else:
        raise NotRecognizedSolidityFuncError(
            f"Function {function_selector} is not recognized"
        )
