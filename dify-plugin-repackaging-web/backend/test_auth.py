#!/usr/bin/env python3
"""
Test script for authentication functionality.
This script demonstrates how to use the authentication endpoints.
"""

import base64
import requests
import sys


def test_no_auth_public_endpoint(base_url: str):
    """Test accessing public endpoints without authentication."""
    print("\n=== Test 1: Public endpoints (no auth required) ===")

    # Test health endpoint
    response = requests.get(f"{base_url}/health")
    print(f"GET /health: {response.status_code}")
    print(f"Response: {response.json()}")

    return response.status_code == 200


def test_no_auth_protected_endpoint(base_url: str):
    """Test accessing protected endpoints without authentication."""
    print("\n=== Test 2: Protected endpoint without auth (should fail) ===")

    response = requests.get(f"{base_url}/api/v1/marketplace/plugins")
    print(f"GET /api/v1/marketplace/plugins: {response.status_code}")
    print(f"Response: {response.json()}")

    return response.status_code == 401


def test_basic_auth(base_url: str, password: str):
    """Test authentication using HTTP Basic Auth."""
    print("\n=== Test 3: HTTP Basic Auth ===")

    # Create Basic Auth header
    credentials = base64.b64encode(f"admin:{password}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}"
    }

    response = requests.get(f"{base_url}/api/v1/marketplace/plugins", headers=headers)
    print(f"GET /api/v1/marketplace/plugins with Basic Auth: {response.status_code}")

    if response.status_code == 200:
        print("Authentication successful!")
        return True
    else:
        print(f"Response: {response.json()}")
        return False


def test_token_auth(base_url: str, password: str):
    """Test authentication using X-Auth-Token header."""
    print("\n=== Test 4: X-Auth-Token header ===")

    headers = {
        "X-Auth-Token": password
    }

    response = requests.get(f"{base_url}/api/v1/marketplace/plugins", headers=headers)
    print(f"GET /api/v1/marketplace/plugins with X-Auth-Token: {response.status_code}")

    if response.status_code == 200:
        print("Authentication successful!")
        return True
    else:
        print(f"Response: {response.json()}")
        return False


def test_wrong_password(base_url: str):
    """Test authentication with wrong password."""
    print("\n=== Test 5: Wrong password (should fail) ===")

    headers = {
        "X-Auth-Token": "wrong_password_123"
    }

    response = requests.get(f"{base_url}/api/v1/marketplace/plugins", headers=headers)
    print(f"GET /api/v1/marketplace/plugins with wrong password: {response.status_code}")
    print(f"Response: {response.json()}")

    return response.status_code == 401


def test_rate_limiting(base_url: str):
    """Test rate limiting for failed authentication attempts."""
    print("\n=== Test 6: Rate limiting (should trigger after 5 attempts) ===")

    for i in range(7):
        headers = {
            "X-Auth-Token": f"wrong_password_{i}"
        }
        response = requests.get(f"{base_url}/api/v1/marketplace/plugins", headers=headers)
        print(f"Attempt {i+1}: {response.status_code}")

        if response.status_code == 429:
            print("Rate limiting triggered successfully!")
            return True

    return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_auth.py <base_url> [password]")
        print("Example: python test_auth.py http://localhost:8000 mypassword123")
        sys.exit(1)

    base_url = sys.argv[1].rstrip('/')
    password = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Testing authentication at: {base_url}")
    if password:
        print(f"Using password: {password}")
    else:
        print("No password provided - testing without authentication")

    results = []

    # Test public endpoints
    results.append(("Public endpoints", test_no_auth_public_endpoint(base_url)))

    if password:
        # Test protected endpoints without auth
        results.append(("Protected endpoint without auth", test_no_auth_protected_endpoint(base_url)))

        # Test authentication methods
        results.append(("Basic Auth", test_basic_auth(base_url, password)))
        results.append(("Token Auth", test_token_auth(base_url, password)))
        results.append(("Wrong password", test_wrong_password(base_url)))
        results.append(("Rate limiting", test_rate_limiting(base_url)))

    # Print summary
    print("\n" + "="*50)
    print("Test Summary:")
    print("="*50)
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "="*50)


if __name__ == "__main__":
    main()
