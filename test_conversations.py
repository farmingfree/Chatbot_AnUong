#!/usr/bin/env python3
"""
Quick test script for conversation history API
"""
import requests
import json

API_URL = "http://localhost:8000"

def test_conversations():
    print("=" * 60)
    print("Testing Conversation History API")
    print("=" * 60)

    # 1. List conversations
    print("\n1. List conversations:")
    r = requests.get(f"{API_URL}/api/conversations?limit=5")
    print(f"   Status: {r.status_code}")
    if r.ok:
        data = r.json()
        print(f"   Total: {data['total']} conversations")
        for conv in data['conversations'][:3]:
            print(f"   - {conv['title']} ({conv['message_count']} messages)")

    # 2. Create new conversation
    print("\n2. Create new conversation:")
    r = requests.post(
        f"{API_URL}/api/conversations",
        json={"first_message": "Tìm quán phở ngon ở quận 1"}
    )
    print(f"   Status: {r.status_code}")
    if r.ok:
        conv = r.json()
        conv_id = conv['id']
        print(f"   Created: {conv['title']}")
        print(f"   ID: {conv_id}")

        # 3. Get messages
        print("\n3. Get conversation messages:")
        r = requests.get(f"{API_URL}/api/conversations/{conv_id}/messages")
        print(f"   Status: {r.status_code}")
        if r.ok:
            messages = r.json()
            print(f"   Messages: {len(messages)}")
            for msg in messages:
                print(f"   - [{msg['role']}] {msg['content'][:50]}...")

        # 4. Rename conversation
        print("\n4. Rename conversation:")
        r = requests.patch(
            f"{API_URL}/api/conversations/{conv_id}",
            json={"title": "Phở Quận 1 - Test"}
        )
        print(f"   Status: {r.status_code}")
        if r.ok:
            print(f"   Renamed to: {r.json()['title']}")

        # 5. Search conversations
        print("\n5. Search conversations:")
        r = requests.get(f"{API_URL}/api/conversations/search?q=phở")
        print(f"   Status: {r.status_code}")
        if r.ok:
            results = r.json()
            print(f"   Found: {len(results)} results")
            for result in results[:2]:
                print(f"   - {result['conversation']['title']}")
                print(f"     Matched: {len(result['matched_messages'])} messages")

        # 6. Delete conversation
        print("\n6. Delete conversation:")
        r = requests.delete(f"{API_URL}/api/conversations/{conv_id}")
        print(f"   Status: {r.status_code}")
        if r.ok:
            print("   Deleted successfully")

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_conversations()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Backend not running!")
        print("   Start backend: cd apps/api && uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ Error: {e}")
