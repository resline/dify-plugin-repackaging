#!/usr/bin/env python3
"""
Simple test to check if API is returning JSON properly
"""
import requests
import json

def test_api():
    base_url = "http://localhost:8000"
    
    endpoints = [
        "/api/v1/marketplace/plugins",
        "/api/v1/marketplace/authors",
        "/api/v1/marketplace/categories",
        "/api/v1/marketplace/status",
        "/api/v1/marketplace/debug"
    ]
    
    print("Testing API endpoints...\n")
    
    for endpoint in endpoints:
        url = base_url + endpoint
        print(f"Testing: {url}")
        
        try:
            response = requests.get(url, headers={"Accept": "application/json"})
            
            print(f"  Status: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('Content-Type', 'Not set')}")
            
            # Try to parse as JSON
            try:
                data = response.json()
                print(f"  JSON Valid: Yes")
                print(f"  Response keys: {list(data.keys())}")
            except json.JSONDecodeError as e:
                print(f"  JSON Valid: No - {e}")
                print(f"  Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"  Error: {e}")
        
        print()

if __name__ == "__main__":
    test_api()