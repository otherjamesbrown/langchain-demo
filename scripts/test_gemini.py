#!/usr/bin/env python3
"""
Simple test script for Gemini integration.

This script tests the Gemini model integration with a basic invocation
to verify the configuration is correct.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.model_factory import get_llm


def test_gemini_integration():
    """Test Gemini model integration."""
    
    # Check if API key is set
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ ERROR: GOOGLE_API_KEY environment variable not set")
        print("\nTo set up Gemini testing:")
        print("1. Get your API key from: https://makersuite.google.com/app/apikey")
        print("2. Set it in your environment or .env file")
        sys.exit(1)
    
    print("🧪 Testing Gemini integration...")
    print(f"   Using model: gemini-flash-latest")
    print(f"   API key: {os.getenv('GOOGLE_API_KEY')[:10]}...")
    print()
    
    try:
        # Initialize the model
        print("1. Initializing Gemini model...")
        llm = get_llm(model_type="gemini", model="gemini-flash-latest")
        print("   ✅ Model initialized successfully")
        print()
        
        # Test basic invocation
        print("2. Testing model invocation...")
        response = llm.invoke("Say 'test successful' and nothing else.")
        print(f"   ✅ Response received")
        print()
        
        # Display results
        print("3. Results:")
        print("=" * 60)
        print(response)
        print("=" * 60)
        print()
        
        print("✅ Gemini integration test PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Gemini integration test FAILED!")
        print(f"\nError details: {type(e).__name__}: {e}")
        print()
        
        # Provide helpful debugging info
        if "404" in str(e):
            print("💡 This appears to be a 404 error. Possible causes:")
            print("   - Model name might be incorrect")
            print("   - Your API key might not have access to this model")
            print("   - Billing might not be enabled on your Google Cloud account")
        elif "API key" in str(e) or "GOOGLE_API_KEY" in str(e):
            print("💡 API key issue. Check that GOOGLE_API_KEY is set correctly.")
        elif "ImportError" in str(e):
            print("💡 Missing dependencies. Install with:")
            print("   pip install langchain-google-genai")
        
        return False


if __name__ == "__main__":
    success = test_gemini_integration()
    sys.exit(0 if success else 1)

