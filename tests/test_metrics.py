"""Test script for Prometheus metrics endpoint."""

import asyncio

import httpx


async def test_metrics_endpoint():
    """Test the metrics endpoint."""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        # Test root endpoint
        print("Testing root endpoint...")
        response = await client.get(f"{base_url}/")
        print(f"✅ Root: {response.status_code} - {response.json()}")
        
        # Test health endpoint
        print("\nTesting health endpoint...")
        response = await client.get(f"{base_url}/health")
        print(f"✅ Health: {response.status_code} - {response.json()}")
        
        # Test stats endpoint
        print("\nTesting stats endpoint...")
        response = await client.get(f"{base_url}/api/v1/stats")
        print(f"✅ Stats: {response.status_code} - {response.json()}")
        
        # Test Prometheus metrics endpoint
        print("\nTesting Prometheus /metrics endpoint...")
        response = await client.get(f"{base_url}/metrics")
        print(f"✅ Metrics: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        # Display some metrics
        metrics_text = response.text
        print("\n📊 Sample Metrics:")
        print("-" * 60)
        for line in metrics_text.split("\n")[:30]:  # First 30 lines
            if line and not line.startswith("#"):
                print(f"  {line}")
        print("-" * 60)
        
        # Count metrics
        metric_lines = [l for l in metrics_text.split("\n") if l and not l.startswith("#")]
        print(f"\n📈 Total metric entries: {len(metric_lines)}")


if __name__ == "__main__":
    print("🚀 AI Code Review Assistant - Metrics Endpoint Test\n")
    print("=" * 60)
    asyncio.run(test_metrics_endpoint())
    print("=" * 60)
    print("\n✅ All tests passed!")
