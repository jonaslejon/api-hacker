# api-hacker
Reads and Swagger/OpenAPI JSON file and routes the requests via Burp Suite

## Usage

```
python3 api-hacker.py --no-verify --delay 1 --threads 1 --proxy http://127.0.0.1:8080 --base_url https://api.test.se --timeout 100 --openapi_file ../swagger.json -H "Authorization: Bearer XXXXXXXXXXX"
```
