"""
API Gateway Client Library

Einfache Python-Bibliothek zur Interaktion mit dem API Gateway.

Beispiel:
    from client import APIGatewayClient
    
    client = APIGatewayClient()
    
    # Terminal API
    result = client.terminal.execute_command("ls -la")
    
    # Memory API
    memories = client.memory.list_memories()
    client.memory.create_memory("Wichtiger Punkt", tags=["work"])
    
    # Filesystem API
    files = client.filesystem.list_files()
    client.filesystem.upload_file("/path/to/file")
    
    # Summarizer API
    summary = client.summarizer.summarize("Long text here...")
"""

import requests
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin


class APIGatewayException(Exception):
    """Base exception for API Gateway errors"""
    pass


class APIClient:
    """Base API Client"""
    
    def __init__(self, base_url: str, gateway_url: str = "http://localhost:8080"):
        self.base_url = urljoin(gateway_url, base_url)
        self.gateway_url = gateway_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "APIGatewayClient/1.0"
        })
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request to API"""
        url = urljoin(self.base_url, endpoint)
        
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {}
        except requests.exceptions.HTTPError as e:
            raise APIGatewayException(f"HTTP Error {e.response.status_code}: {e.response.text}")
        except requests.exceptions.RequestException as e:
            raise APIGatewayException(f"Request failed: {e}")
    
    def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """GET request"""
        return self._make_request("GET", endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """POST request"""
        return self._make_request("POST", endpoint, **kwargs)
    
    def put(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """PUT request"""
        return self._make_request("PUT", endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """DELETE request"""
        return self._make_request("DELETE", endpoint, **kwargs)


class TerminalAPI(APIClient):
    """Terminal API Client"""
    
    def __init__(self, gateway_url: str = "http://localhost:8080"):
        super().__init__("/api/terminal/", gateway_url)
    
    def list_sessions(self) -> List[Dict]:
        """List all terminal sessions"""
        return self.get("sessions")
    
    def create_session(self, shell: str = "/bin/bash") -> Dict:
        """Create new terminal session"""
        return self.post("sessions", json={"shell": shell})
    
    def execute_command(self, command: str, session_id: Optional[str] = None) -> Dict:
        """Execute command in terminal"""
        data = {"command": command}
        if session_id:
            data["session_id"] = session_id
        return self.post("execute", json=data)
    
    def get_session_info(self, session_id: str) -> Dict:
        """Get session information"""
        return self.get(f"sessions/{session_id}")


class MemoryAPI(APIClient):
    """Memory API Client"""
    
    def __init__(self, gateway_url: str = "http://localhost:8080"):
        super().__init__("/api/memory/", gateway_url)
    
    def list_memories(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """List all memories"""
        return self.get("memories", params={"limit": limit, "offset": offset})
    
    def get_memory(self, memory_id: int) -> Dict:
        """Get specific memory"""
        return self.get(f"memories/{memory_id}")
    
    def create_memory(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Create new memory"""
        data = {
            "content": content,
            "tags": tags or [],
            "metadata": metadata or {}
        }
        return self.post("memories", json=data)
    
    def update_memory(
        self,
        memory_id: int,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict:
        """Update existing memory"""
        data = {}
        if content:
            data["content"] = content
        if tags:
            data["tags"] = tags
        return self.put(f"memories/{memory_id}", json=data)
    
    def delete_memory(self, memory_id: int) -> Dict:
        """Delete memory"""
        return self.delete(f"memories/{memory_id}")
    
    def search_memories(self, query: str, limit: int = 10) -> List[Dict]:
        """Search memories"""
        return self.get("search", params={"q": query, "limit": limit})


class VectorMemoryAPI(APIClient):
    """Vector Memory API Client"""
    
    def __init__(self, gateway_url: str = "http://localhost:8080"):
        super().__init__("/api/vector/", gateway_url)
    
    def search(
        self,
        vector: List[float],
        limit: int = 10,
        threshold: float = 0.5
    ) -> List[Dict]:
        """Search similar vectors"""
        return self.post("search", json={
            "vector": vector,
            "limit": limit,
            "threshold": threshold
        })
    
    def store_vector(
        self,
        vector: List[float],
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Store vector with metadata"""
        return self.post("store", json={
            "vector": vector,
            "metadata": metadata or {}
        })
    
    def list_collections(self) -> List[Dict]:
        """List collections"""
        return self.get("collections")
    
    def get_collection_info(self, collection_name: str) -> Dict:
        """Get collection information"""
        return self.get(f"collections/{collection_name}")


class FilesystemAPI(APIClient):
    """Filesystem API Client"""
    
    def __init__(self, gateway_url: str = "http://localhost:8080"):
        super().__init__("/api/filesystem/", gateway_url)
    
    def list_files(self, path: str = "/") -> List[Dict]:
        """List files in directory"""
        return self.get("files", params={"path": path})
    
    def upload_file(self, file_path: str, remote_path: str = "/") -> Dict:
        """Upload file"""
        with open(file_path, "rb") as f:
            files = {"file": f}
            return self.post("upload", files=files, data={"path": remote_path})
    
    def download_file(self, file_name: str) -> bytes:
        """Download file"""
        response = self.session.get(
            urljoin(self.base_url, f"download/{file_name}"),
            timeout=60
        )
        response.raise_for_status()
        return response.content
    
    def delete_file(self, file_name: str) -> Dict:
        """Delete file"""
        return self.delete(f"files/{file_name}")
    
    def get_file_info(self, file_name: str) -> Dict:
        """Get file information"""
        return self.get(f"files/{file_name}")


class SummarizerAPI(APIClient):
    """Summarizer API Client"""
    
    def __init__(self, gateway_url: str = "http://localhost:8080"):
        super().__init__("/api/summarizer/", gateway_url)
    
    def summarize(
        self,
        text: str,
        max_length: int = 100,
        language: str = "de"
    ) -> Dict:
        """Summarize text"""
        return self.post("summarize", json={
            "text": text,
            "max_length": max_length,
            "language": language
        })
    
    def summarize_with_context(
        self,
        text: str,
        context: str,
        max_length: int = 100
    ) -> Dict:
        """Summarize with context"""
        return self.post("summarize-context", json={
            "text": text,
            "context": context,
            "max_length": max_length
        })
    
    def extract_keywords(self, text: str) -> Dict:
        """Extract keywords from text"""
        return self.post("keywords", json={"text": text})


class APIGatewayClient:
    """Main API Gateway Client"""
    
    def __init__(self, gateway_url: str = "http://localhost:8080"):
        self.gateway_url = gateway_url
        self.terminal = TerminalAPI(gateway_url)
        self.memory = MemoryAPI(gateway_url)
        self.vector = VectorMemoryAPI(gateway_url)
        self.filesystem = FilesystemAPI(gateway_url)
        self.summarizer = SummarizerAPI(gateway_url)
    
    def health_check(self) -> bool:
        """Check gateway health"""
        try:
            response = requests.get(f"{self.gateway_url}/health", timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def get_info(self) -> Dict:
        """Get gateway info"""
        try:
            response = requests.get(f"{self.gateway_url}/api-info", timeout=3)
            return response.json()
        except:
            return {}


if __name__ == "__main__":
    # Example usage
    import json
    
    print("API Gateway Client - Beispiele\n")
    
    client = APIGatewayClient()
    
    # Health Check
    print("1. Health Check")
    if client.health_check():
        print("   ✓ Gateway ist erreichbar\n")
    else:
        print("   ✗ Gateway ist nicht erreichbar\n")
    
    # Gateway Info
    print("2. Gateway Info")
    info = client.get_info()
    print(f"   {json.dumps(info, indent=2)}\n")
    
    # Memory API Example
    print("3. Memory API - Beispiel")
    try:
        # Create memory
        memory = client.memory.create_memory(
            "Wichtige Information",
            tags=["example", "test"],
            metadata={"source": "example"}
        )
        print(f"   ✓ Memory erstellt: {json.dumps(memory, indent=2)}\n")
    except APIGatewayException as e:
        print(f"   Note: {e}\n")
    
    # List memories
    try:
        memories = client.memory.list_memories(limit=5)
        print(f"   ✓ Memories geladen: {len(memories)} Einträge\n")
    except APIGatewayException as e:
        print(f"   Note: {e}\n")
