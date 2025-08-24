import os
import re
import json
import glob
import requests
import time

def extract_json_from_ldb(path, out='decrypted'):
    if not os.path.exists(path):
        print('Path does not exist')
        return
   
    if not os.path.exists(out):
        os.makedirs(out)
    jsoncounter = 0
    for filename in os.listdir(path):
        if filename.endswith('.ldb'):
            with open(os.path.join(path, filename), 'rb') as f:
                data = f.read()
                matches = re.findall(b'{.*?}', data, re.DOTALL)
                for match in matches:
                    try:
                        obj = json.loads(match.decode('utf-8'))
                        if obj:
                            out_file = os.path.join(out, f'{filename}_{jsoncounter}.json')
                            with open(out_file, 'w', encoding='utf-8') as out_f:
                                json.dump(obj, out_f, indent=2, ensure_ascii=False)
                            jsoncounter += 1
                    except:
                        continue
    print(f'Extracted {jsoncounter}')

def detect_address_type(address):
    address = address.strip()
    if re.match(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$', address) or re.match(r'^bc1[a-z0-9]{39,59}$', address):
        return 'BTC'
    if re.match(r'^0x[a-fA-F0-9]{40}$', address):
        return 'ETH'
    if re.match(r'^[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}$', address) or re.match(r'^ltc1[a-z0-9]{39,59}$', address):
        return 'LTC'
    if re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address) and len(address) >= 32:
        if not (address.startswith(('1', '3', 'bc1', 'L', 'M'))):
            return 'SOL'
    return None

def get_balance(address, coin_type):
    try:
        if coin_type == 'BTC':
            url = f"https://blockstream.info/api/address/{address}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                balance_satoshi = data.get('chain_stats', {}).get('funded_txo_sum', 0) - data.get('chain_stats', {}).get('spent_txo_sum', 0)
                return balance_satoshi / 100000000
        elif coin_type == 'ETH':
            url = f"https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == '1':
                    wei_balance = int(data.get('result', 0))
                    return wei_balance / 10**18
        elif coin_type == 'LTC':
            url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}/balance"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                balance_litoshi = data.get('balance', 0)
                return balance_litoshi / 100000000
        elif coin_type == 'SOL':
            url = "https://api.mainnet-beta.solana.com"
            payload = {"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [address]}
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'result' in data:
                    lamports = data['result']['value']
                    return lamports / 10**9
    except:
        pass
    return 0

def extract_addresses_from_directory(directory_path):
    addresses = []
    json_pattern = os.path.join(directory_path, "*.json")
    json_files = glob.glob(json_pattern)
    
    if not json_files:
        return addresses
    
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                if isinstance(data, dict) and 'address' in data:
                    addresses.append(data['address'])
        except:
            continue
    
    return addresses

if __name__ == "__main__":
    path = input('Path to the metamask files the ones with .ldb extentions etc: ')
    extract_json_from_ldb(path)
    
    addresses = extract_addresses_from_directory('decrypted')
    if addresses:
        for addr in addresses:
            coin_type = detect_address_type(addr)
            if coin_type:
                balance = get_balance(addr, coin_type)
                print(f'MetamaskScanner | Coin: {coin_type} | Address: {addr} | Balance: {balance}')
    
    else:
        print('No addresses found')
    
    input('Finished')
