#!/usr/bin/env python
"""Debug startup sequence to identify which service is blocking"""

import asyncio
import sys

async def test_services():
    print("🔍 Testing services startup sequence...\n")
    
    # Test 1: MongoDB
    print("1️⃣ Testing MongoDB connection...")
    try:
        from db.database import client
        from motor.motor_asyncio import AsyncIOMotorClient
        
        try:
            result = await asyncio.wait_for(
                client.admin.command("ping"),
                timeout=5
            )
            print("   ✅ MongoDB connected\n")
        except asyncio.TimeoutError:
            print("   ❌ MongoDB TIMEOUT (>5s) - Connection hanging\n")
            return "MongoDB"
        except Exception as e:
            print(f"   ⚠️ MongoDB error: {e}\n")
            return "MongoDB"
    except Exception as e:
        print(f"   ❌ Cannot import MongoDB client: {e}\n")
        return "MongoDB"
    
    # Test 2: Redis
    print("2️⃣ Testing Redis connection...")
    try:
        from api.core.redis_cache import get_cache
        
        try:
            cache = await asyncio.wait_for(
                get_cache(),
                timeout=5
            )
            print("   ✅ Redis connected\n")
        except asyncio.TimeoutError:
            print("   ❌ Redis TIMEOUT (>5s) - Connection hanging\n")
            return "Redis"
        except Exception as e:
            print(f"   ⚠️ Redis error: {e}\n")
            return "Redis"
    except Exception as e:
        print(f"   ❌ Cannot import Redis: {e}\n")
        return "Redis"
    
    # Test 3: Email Service
    print("3️⃣ Testing Email service...")
    try:
        from api.core.email_service import get_email_service
        
        try:
            email = await asyncio.wait_for(
                get_email_service(),
                timeout=5
            )
            print("   ✅ Email service initialized\n")
        except asyncio.TimeoutError:
            print("   ❌ Email TIMEOUT (>5s) - Connection hanging\n")
            return "Email Service"
        except Exception as e:
            print(f"   ⚠️ Email error: {e}\n")
            return "Email Service"
    except Exception as e:
        print(f"   ❌ Cannot import Email service: {e}\n")
        return "Email Service"
    
    print("✅ All services OK!")
    return None

if __name__ == "__main__":
    blocking_service = asyncio.run(test_services())
    if blocking_service:
        print(f"\n🚨 BLOCKING SERVICE FOUND: {blocking_service}")
        print(f"\nFix: Check if {blocking_service} is running/accessible")
        sys.exit(1)
    else:
        print("\n✅ Ready to start main.py")
        sys.exit(0)
