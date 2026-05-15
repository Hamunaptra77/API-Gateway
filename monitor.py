#!/usr/bin/env python3
"""
API Gateway Status & Monitoring Tool
"""

import requests
import sys
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict

GATEWAY_URL = "http://localhost:8080"
ENDPOINTS = {
    "Terminal": "/api/terminal/health",
    "Memory": "/api/memory/health", 
    "Vector Memory": "/api/vector/health",
    "Filesystem": "/api/filesystem/health",
    "Summarizer": "/api/summarizer/health",
}

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def check_gateway_health() -> bool:
    """Check if gateway is running"""
    try:
        response = requests.get(f"{GATEWAY_URL}/health", timeout=3)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def check_service_health(service_name: str, endpoint: str) -> Tuple[bool, int, str]:
    """Check health of individual service"""
    try:
        response = requests.get(f"{GATEWAY_URL}{endpoint}", timeout=5)
        status = response.status_code
        if status == 200:
            return True, status, "OK"
        else:
            return False, status, f"HTTP {status}"
    except requests.exceptions.Timeout:
        return False, 0, "Timeout"
    except requests.exceptions.ConnectionError:
        return False, 0, "Connection Error"
    except requests.exceptions.RequestException as e:
        return False, 0, str(e)

def get_gateway_info() -> Dict:
    """Get gateway info"""
    try:
        response = requests.get(f"{GATEWAY_URL}/api-info", timeout=3)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {}

def print_header():
    """Print table header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}API Gateway Status Monitor{Colors.RESET}")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

def print_gateway_status(is_running: bool):
    """Print gateway status"""
    status = f"{Colors.GREEN}✓ RUNNING{Colors.RESET}" if is_running else f"{Colors.RED}✗ DOWN{Colors.RESET}"
    print(f"\nGateway Status: {status}")
    print(f"URL: {GATEWAY_URL}")

def print_service_status(name: str, healthy: bool, status: int, message: str):
    """Print service status line"""
    status_icon = f"{Colors.GREEN}✓{Colors.RESET}" if healthy else f"{Colors.RED}✗{Colors.RESET}"
    status_text = f"{Colors.GREEN}OK{Colors.RESET}" if healthy else f"{Colors.RED}{message}{Colors.RESET}"
    print(f"  {status_icon} {name:<20} {status_text}")

def print_endpoints():
    """Print available endpoints"""
    print(f"\n{Colors.BOLD}Available Endpoints:{Colors.RESET}")
    endpoints = [
        "/api/terminal/     - Terminal/Shell Operations",
        "/api/memory/       - Memory Management (PostgreSQL)",
        "/api/vector/       - Vector Memory (Qdrant)",
        "/api/filesystem/   - File Storage Operations",
        "/api/summarizer/   - Text Summarization (LLM)",
    ]
    for endpoint in endpoints:
        print(f"  • {endpoint}")

def print_curl_examples():
    """Print curl examples"""
    print(f"\n{Colors.BOLD}Example Requests:{Colors.RESET}")
    examples = [
        ("Gateway Health", f"curl {GATEWAY_URL}/health"),
        ("Gateway Info", f"curl {GATEWAY_URL}/api-info"),
        ("Terminal API", f"curl {GATEWAY_URL}/api/terminal/info"),
        ("Memory API", f"curl {GATEWAY_URL}/api/memory/info"),
        ("Vector API", f"curl {GATEWAY_URL}/api/vector/info"),
        ("Filesystem API", f"curl {GATEWAY_URL}/api/filesystem/info"),
        ("Summarizer API", f"curl {GATEWAY_URL}/api/summarizer/info"),
    ]
    for name, cmd in examples:
        print(f"  {name}:")
        print(f"    {Colors.YELLOW}{cmd}{Colors.RESET}")

def main():
    """Main function"""
    print_header()
    
    # Check gateway
    gateway_running = check_gateway_health()
    print_gateway_status(gateway_running)
    
    if not gateway_running:
        print(f"\n{Colors.RED}Gateway is not responding!{Colors.RESET}")
        print("Make sure all services are running with: docker-compose up -d")
        return 1
    
    # Check services
    print(f"\n{Colors.BOLD}Service Status:{Colors.RESET}")
    
    healthy_count = 0
    for service_name, endpoint in ENDPOINTS.items():
        is_healthy, status, message = check_service_health(service_name, endpoint)
        print_service_status(service_name, is_healthy, status, message)
        if is_healthy:
            healthy_count += 1
    
    # Summary
    total_services = len(ENDPOINTS)
    print(f"\n{Colors.BOLD}Summary:{Colors.RESET}")
    print(f"  Services: {healthy_count}/{total_services} healthy")
    
    # Additional info
    print_endpoints()
    print_curl_examples()
    
    # Footer
    print(f"\n{'=' * 80}\n")
    
    return 0 if healthy_count == total_services else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Interrupted by user{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.RESET}")
        sys.exit(1)
