import os

file_path = 'core/engine.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

replacement = "await BinanceAsyncClient.create(api_key, api_secret, requests_params={'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', 'Accept': 'application/json'}})"

new_content = content.replace("await BinanceAsyncClient.create(api_key, api_secret)", replacement)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print("Updated core/engine.py")
