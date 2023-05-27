#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##
## API-hacker - A tool to send HTTP requests based on an OpenAPI file
## 

import json
import requests
import time
import argparse
import sys
import concurrent.futures
import re
import random
import urllib3
from urllib.parse import urlparse
from pyfiglet import Figlet

# Routing requests through a proxy yields a warning, disable it
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CLI_NAME = "API-hacker"
HTTP_UA = 'Mozilla/5.0'
VERSION = "0.1.2"

def replace_id(url):
    """Replace the {id} part of the URL with a random number between 1 and 100."""
    pattern = r'\{.*(key|Id)\}'
    if re.search(pattern, url):
        new_url = re.sub(pattern, str(random.randint(1, 100)), url)
        return new_url
    else:
        return url

def uri_validator(x):
    try:
        result = urlparse(x)
        return all([result.scheme, result.netloc])
    except:
        return False


def populate_headers(set_header):
    # Convert the argument "Authorization: Bearer XXXX" to a dictionary
    headers = {}
    if set_header:
        for header in set_header:
            key, value = header.split(':', 1)
            headers[key.strip()] = value.strip()

    headers['Content-Type'] = "application/json"
    headers['Accept'] = "application/json"
    headers['User-Agent'] = HTTP_UA
    return headers

def send_request(method, url, proxy, timeout, set_header, verify, parameters):
    # Set up the proxies for the request
    proxies = {
        'http': proxy,
        'https': proxy,
    }

    # Replace the {somethingId} part of the URL with a random number between 1 and 100
    url = replace_id(url)

    # Set hte user_agent, authorization etc
    headers = populate_headers(set_header)

    # Create the POST body from the parameters. Prefill with random values
    post_body = {param['name']: random.randint(1, 100) for param in parameters} if parameters else None

    # Send the HTTP request
    if method == 'get':
        response = requests.get(url, json=post_body, proxies=proxies, timeout=timeout, verify=verify, headers=headers)
    elif method == 'post':
        response = requests.post(url, json=post_body, proxies=proxies, timeout=timeout, verify=verify, headers=headers)
    elif method == 'put':
        response = requests.put(url, proxies=proxies, timeout=timeout, verify=verify, headers=headers)
    elif method == 'delete':
        response = requests.delete(url, proxies=proxies, timeout=timeout, verify=verify, headers=headers)
    elif method == 'patch':
        response = requests.patch(url, proxies=proxies ,timeout=timeout, verify=verify, headers=headers)
    else:
        print(f'Unknown method {method} for path {url}')
        return

    if response.status_code == 401:
        if response.headers.get('WWW-Authenticate'):
            print(f"Server wants the WWW-Authenticate header: {response.headers.get('WWW-Authenticate')}")
        print("! Error: HTTP Error code 401, did you provide authentication? Continuing.")

def is_server_up(url, proxy, timeout, set_header, verify):
    # Set up the proxies for the request
    proxies = {
        'http': proxy,
        'https': proxy,
    }

    # Set hte user_agent, authorization etc
    headers = populate_headers(set_header)
    try:
        response = requests.get(url, proxies=proxies, timeout=timeout, verify=verify, headers=headers)
        return response.status_code == 200
    # Catch all exceptions
    except Exception as e:
        print(f"Exception while checking if server is up: {e}")
        return False
    
def main():

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Send HTTP requests based on an OpenAPI file.')
    parser.add_argument('--delay', type=int, default=0, help='Delay between each request in seconds')
    parser.add_argument('--threads', type=int, default=1, help='Number of concurrent threads')
    parser.add_argument('--proxy', type=str, default=None, help='HTTP proxy to use for requests')
    parser.add_argument('--timeout', type=int, default=5, help='HTTP timeout value')
    parser.add_argument('--base_url', type=str, default=None, help='Base URL for the API')
    parser.add_argument('--openapi_file', type=str, required=True, help='Path to the OpenAPI JSON file')
    parser.add_argument('-H', '--header', action='append', help='HTTP header to add to the request')
    parser.add_argument('--verify', action='store_true', help='Verify SSL certificate')
    parser.add_argument('--no-verify', dest='tls_verify', action='store_false')
    parser.set_defaults(tls_verify=True)
    # Read version
    parser.add_argument('--version', '-v', action="version", version=VERSION)
    args = parser.parse_args()

    if args.tls_verify is False:
        print("Warning: SSL verification is disabled.")
  

    # Print the banner
    f = Figlet(font='slant')
    print(f.renderText(CLI_NAME))
    print(f"# {CLI_NAME} - version: {VERSION}\n")

    if args.delay > 60:
        print("Warning: Delay between each request is more then 60 seconds.")

    # Check if proxy is set and valid
    if args.proxy:
        if uri_validator(args.proxy) is False:
            print(f"Invalid proxy: {args.proxy}")
            exit(1)

    # Load the OpenAPI JSON file
    with open(args.openapi_file, encoding="utf-8") as f:
        api_spec = json.load(f)

    # Set the base URL for the API
    base_url = args.base_url if args.base_url else api_spec.get('servers', [{}])[0].get('url', '')

    if not base_url:
        print("Error: No base URL provided and no 'servers' field in OpenAPI file. Hint: Use the --base_url argument.")
        exit(1)

    # Count the total number of tests
    total_tests = sum(len(methods) for methods in api_spec['paths'].values())
    # Print total number of tests
    print(f"# Total number of tests: {total_tests} on base url: {base_url}")

    # Check if the server is up
    print("% Checking if API is up...")
    if not is_server_up(base_url, args.proxy, args.timeout, args.header, args.tls_verify):
        print(f"Error: Server at {base_url} is not up. Exiting.")
        exit(1)

    print("- API is up, starting tests...")
    # Create a thread pool executor
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
        # Initialize the test number
        test_number = 0

        # Loop over each path in the API
        for path, path_spec in api_spec['paths'].items():
            # Loop over each method for this path
            for method, method_spec in path_spec.items():
                # Increment the test number
                test_number += 1

                # Construct the full URL for this path
                url = base_url + path

                print(f"{test_number}/{total_tests} - {method.upper()} {url}")

                parameters = method_spec.get('parameters', [])

                # Start a new thread to send the HTTP request
                executor.submit(send_request, method, url, args.proxy, args.timeout, args.header, args.tls_verify, parameters)

                # Delay in ms before starting the next thread
                time.sleep(args.delay)

        print("! Done.")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting due to ctrl-c.")
        sys.exit(1)