import requests
import json

# 'The valid account ID regex is /^(([a-z\d]+[-_])*[a-z\d]+\.)*([a-z\d]+[-_])*[a-z\d]+$/'
import re
# near_regex = re.compile('^(([a-z\d]+[-_])*[a-z\d]+\.)*([a-z\d]+[-_])*[a-z\d]+$')
near_regex = re.compile('/^(?=.{2,64}$)(([a-z\d]+[-_])*[a-z\d]+\.)*([a-z\d]+[-_])*[a-z\d]+$/')

print(near_regex.match('b8c72480a7d962f389ff2954386e3f529770991df04d6c750923a1b3625bbf9d'))
exit()

# Define the RPC server URL
url = "https://rpc.mainnet.near.org"  # Example NEAR testnet RPC server
# url = "https://rpc.testnet.near.org"
# Define the JSON-RPC request payload
payload = {
    "jsonrpc": "2.0",
    "id": "dontcare",
    "method": "query",
    # "method": "EXPERIMENTAL_changes",
    "params": {
        # "request_type": "view_code",
        "request_type": "view_account",
        "finality": "final",
        # "account_id": "3377c2555af5d56c33e0cf4e30b05034881342a2ac20b8ee68393192fdb25eef"
        # "account_id": "038c39e02c70eb87bcb76e1bff92c8b8778357798c81ab4c486c544349c38654"
        # 'account_id': 'assaben.testnet'

        "account_id":  "b8c72480a7d962f389ff2954386e3f529770991df04d6c750923a1b3625bbf9d",

        # "changes_type": "account_changes",
        # "account_ids": ["b8c72480a7d962f389ff2954386e3f529770991df04d6c750923a1b3625bbf9d"],
    }
}

# Set the headers
headers = {
    "Content-Type": "application/json"
}

# Make the RPC request
response = requests.post(url, headers=headers, data=json.dumps(payload))

# Check if the request was successful
if response.status_code == 200:
    # Parse the JSON response
    result = response.json()
    print(json.dumps(result, indent=4))
else:
    print(f"Error: {response.status_code}")
    print(response.text)