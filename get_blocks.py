from web3 import Web3
import json

# Initialize a Web3 instance (no provider needed for this task)
w3 = Web3()

# Define the standard ERC20 ABI
ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_from", "type": "address"},
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transferFrom",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    # Add other ERC20 functions if necessary
]

# Build a mapping from function selectors to function definitions
function_selectors = {}

for func in ERC20_ABI:
    if func['type'] == 'function':
        # Build the function signature
        func_name = func['name']
        input_types = [inp['type'] for inp in func['inputs']]
        func_signature = f"{func_name}({','.join(input_types)})"
        # Compute the function selector
        func_selector = w3.keccak(text=func_signature)[:4].hex()
        # Store in the mapping
        function_selectors[func_selector] = {
            'name': func_name,
            'inputs': func['inputs'],
            'signature': func_signature
        }

# The transaction data you provided
tx_data = {
    'input': '0xa9059cbb000000000000000000000000094248eb440b6ebb9e54fcbd8b8ad18b037e68850000000000000000000000000000000000000000000000000de0b6b3a7640000',
    'to': '0xdAC17F958D2ee523a2206206994597C13D831ec7'
}

# Extract the function selector from the transaction input
input_data = tx_data['input']
function_selector = input_data[:10]  # Remove '0x' and take the next 8 characters

# Match the function selector
if function_selector in function_selectors:
    func_info = function_selectors[function_selector]
    func_name = func_info['name']
    func_inputs = func_info['inputs']
    func_signature = func_info['signature']
    print(f"Function called: {func_name}")
    print(f"Function signature: {func_signature}")

    # Remove the function selector from input data
    params_data = input_data[10:]

    # Decode the parameters
    params = []
    for i, param in enumerate(func_inputs):
        param_type = param['type']
        param_name = param['name']
        # Each parameter is 32 bytes (64 hex characters)
        param_data = params_data[i * 64: (i + 1) * 64]
        if param_type == 'address':
            # Addresses are right-aligned (left-padded with zeros)
            param_value = '0x' + param_data[-40:]
            param_value = Web3.to_checksum_address(param_value)
        elif param_type.startswith('uint'):
            # Unsigned integers
            param_value = int(param_data, 16)
        else:
            # Add support for other types if necessary
            param_value = param_data
        params.append((param_name, param_type, param_value))

    # Display the decoded parameters
    print("Decoded Parameters:")
    for idx, (param_name, param_type, param_value) in enumerate(params):
        print(f"  {param_name} ({param_type}): {param_value}")
else:
    print("Function selector not recognized.")
