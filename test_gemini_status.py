#!/usr/bin/env python3
"""
Test Gemini API status and connectivity
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv

def test_gemini_api():
    """Test Gemini API connectivity and quota"""
    print("🔍 Testing Gemini API Status")
    print("=" * 40)
    
    # Load environment variables
    load_dotenv()
    
    # Get configuration
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    print(f"Model: {model_name}")
    print(f"API Key: {'✅ Configured' if api_key else '❌ Missing'}")
    
    if not api_key:
        print("❌ No Gemini API key found in .env file")
        return False
    
    try:
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Initialize the model
        model = genai.GenerativeModel(model_name)
        
        print("\n🧪 Testing API connectivity...")
        
        # Test with a simple prompt
        test_prompt = "Hello, please respond with 'API test successful' if you can read this."
        
        response = model.generate_content(
            test_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=50,
                top_p=0.8,
                top_k=40
            )
        )
        
        if response and response.text:
            print("✅ Gemini API is working!")
            print(f"Response: {response.text}")
            
            # Test with a medical query
            print("\n🏥 Testing medical query...")
            medical_prompt = "I have a headache. What could be the cause?"
            
            medical_response = model.generate_content(
                medical_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=200,
                    top_p=0.8,
                    top_k=40
                )
            )
            
            if medical_response and medical_response.text:
                print("✅ Medical query test successful!")
                print(f"Response: {medical_response.text[:100]}...")
                return True
            else:
                print("❌ Medical query failed - no response")
                return False
                
        else:
            print("❌ No response from Gemini API")
            return False
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Gemini API error: {error_msg}")
        
        # Check for specific error types
        if "429" in error_msg or "quota" in error_msg.lower():
            print("💡 This appears to be a quota/rate limit issue")
            print("   - You may have exceeded your daily quota")
            print("   - Wait for the quota to reset (usually 24 hours)")
            print("   - Or upgrade your Gemini API plan")
        elif "401" in error_msg or "authentication" in error_msg.lower():
            print("💡 This appears to be an authentication issue")
            print("   - Check if your API key is correct")
            print("   - Verify the API key has proper permissions")
        elif "403" in error_msg or "forbidden" in error_msg.lower():
            print("💡 This appears to be a permissions issue")
            print("   - Your API key may not have access to this model")
            print("   - Check your Gemini API project settings")
        
        return False

def main():
    success = test_gemini_api()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 Gemini API is working correctly!")
        print("✅ The chat should work with AI responses")
    else:
        print("⚠️  Gemini API has issues")
        print("💡 The chat will work but show 'AI unavailable' messages")
        print("\n🔧 To fix:")
        print("1. Check your Gemini API quota at https://makersuite.google.com/")
        print("2. Wait for quota reset if exceeded")
        print("3. Verify API key is correct in .env file")
        print("4. Check API key permissions")
    
    return success

if __name__ == "__main__":
    main()