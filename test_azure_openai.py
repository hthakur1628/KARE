#!/usr/bin/env python3
"""
Test script for Azure OpenAI integration with the new endpoint
"""

import os
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_azure_openai():
    """Test the Azure OpenAI integration"""
    print("🧪 Testing Azure OpenAI Integration...")
    print("=" * 50)
    
    # Configuration
    endpoint = os.getenv("ENDPOINT_URL", "https://kare.openai.azure.com/")
    deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4-1-mini-2025-04-14-ft-114dcd1904b84a77a945b14818aa398a")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    
    print(f"📍 Endpoint: {endpoint}")
    print(f"🚀 Deployment: {deployment}")
    print(f"🔑 API Key: {'✅ Configured' if api_key else '❌ Not configured'}")
    if api_key:
        print(f"🔑 API Key (first 10 chars): {api_key[:10]}...")
    print()
    
    # Initialize client
    client = None
    auth_method = ""
    
    try:
        if api_key:
            # Use API key authentication
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version="2025-01-01-preview"
            )
            auth_method = "API Key"
            print("✅ Using API key authentication")
        else:
            # Use Entra ID authentication
            try:
                token_provider = get_bearer_token_provider(
                    DefaultAzureCredential(),
                    "https://cognitiveservices.azure.com/.default"
                )
                client = AzureOpenAI(
                    azure_endpoint=endpoint,
                    azure_ad_token_provider=token_provider,
                    api_version="2025-01-01-preview"
                )
                auth_method = "Entra ID"
                print("✅ Using Entra ID authentication")
            except Exception as entra_error:
                print(f"⚠️  Entra ID authentication failed: {str(entra_error)}")
                print("⚠️  Please configure AZURE_OPENAI_API_KEY in .env file")
                return False
            
    except Exception as e:
        print(f"❌ Client initialization failed: {str(e)}")
        print(f"❌ Error details: {type(e).__name__}")
        return False
    
    # Test system message
    system_message = {
        "role": "system",
        "content": "You are a polite and empathetic medical assistant who replies like a human doctor. Use polite expressions and some natural reactions (like 'Oh no!', 'That sounds uncomfortable 😟'). For non-medical questions, respond normally.\n\nWhen the user mentions a symptom:\n\nFirst, ask for their age\n\nThen ask for any other symptoms\n\nThen ask for vital signs, but only the ones relevant to the symptoms:\n\nFor fever → ask for temperature\n\nFor chest pain / shortness of breath / dizziness → ask for heart rate, SpO₂, ECG (if available)\n\nFor headache / fainting / weakness → ask for blood pressure (if known)\n\nFor palpitations / anxiety → ask for heart rate and ECG\n\nFor low energy / fatigue → ask for SpO₂, pulse rate\n\nNever respond with the full answer at once — first, ask polite, intelligent follow-up questions.\nAfter collecting enough information, suggest the most likely condition (in bold) and provide safe remedies or advice based on age group.\n\nUse bold formatting for disease names and important points in your answers. Avoid sounding robotic or overly brief or wordy."
    }
    
    # Test message
    test_messages = [
        system_message,
        {
            "role": "user",
            "content": "Hello, I have been feeling dizzy lately."
        }
    ]
    
    print("\n🔄 Testing chat completion...")
    try:
        completion = client.chat.completions.create(
            model=deployment,
            messages=test_messages,
            max_tokens=500,
            temperature=0.7,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None,
            stream=False
        )
        
        print("✅ Chat completion successful!")
        print(f"📊 Usage: {completion.usage}")
        print(f"🤖 Response: {completion.choices[0].message.content}")
        print()
        
        # Test summary
        print("=" * 50)
        print("📋 TEST SUMMARY")
        print("=" * 50)
        print(f"✅ Endpoint: {endpoint}")
        print(f"✅ Deployment: {deployment}")
        print(f"✅ Authentication: {auth_method}")
        print(f"✅ API Version: 2025-01-01-preview")
        print(f"✅ Response received: {len(completion.choices[0].message.content)} characters")
        print("✅ Integration working correctly!")
        
        return True
        
    except Exception as e:
        print(f"❌ Chat completion failed: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        
        # Additional debugging info
        if hasattr(e, 'response'):
            print(f"❌ HTTP Status: {e.response.status_code if hasattr(e.response, 'status_code') else 'Unknown'}")
        
        return False

if __name__ == "__main__":
    success = test_azure_openai()
    if success:
        print("\n🎉 Azure OpenAI integration is ready!")
    else:
        print("\n💥 Azure OpenAI integration needs attention!")