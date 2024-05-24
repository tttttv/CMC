import requests

# regex
# '^0x([A-Fa-f0-9]{40})$'

address = '0x6b20Cc4885a5868eEDDECa5aDA5C66B056E8c9aF'
r = requests.get(f'https://explorer.mantle.xyz/api/v2/addresses/{address}')
print(r.status_code)
print(r.json())

