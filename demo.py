#!/usr/bin/env python3
"""
API Demo Script for LLM-Powered OCR Correction Pipeline

This script demonstrates the basic API usage for both OpenAI GPT-5 series 
and Google Gemini 2.5 series models with the parameters used in our OCR 
correction pipeline. Use this for minimum availability testing.

Requirements:
- OPENAI_API_KEY environment variable for OpenAI models
- GEMINI_API_KEY environment variable for Gemini models
"""

import os
import sys

def test_openai_api():
    """Test OpenAI GPT-5 series API availability"""
    print("🧪 Testing OpenAI GPT-5 series API...")
    
    try:
        from openai import OpenAI
        client = OpenAI()
        
        # Test the exact API format used in our pipeline
        response = client.responses.create(
            model="gpt-5-nano",
            instructions="You are an expert at correcting OCR errors in French medical directories from the 19th century. Extract structured data in TSV format.",
            input="Docteur Dupont 1885 Médecin rue de la Paix 12 consultations 2 à 4h"
            # Note: GPT-5 series doesn't support temperature parameter in responses.create API
        )
        
        print("✅ OpenAI API working successfully")
        print(f"📝 Response preview: {response.output_text[:100]}...")
        return True
        
    except ImportError:
        print("❌ OpenAI package not installed: pip install openai")
        return False
    except Exception as e:
        print(f"❌ OpenAI API error: {e}")
        return False

def test_gemini_api():
    """Test Google Gemini 2.5 series API availability"""
    print("\n🧪 Testing Google Gemini 2.5 series API...")
    
    try:
        from google import genai
        
        # Check for API key
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("❌ GEMINI_API_KEY environment variable not set")
            return False
        
        client = genai.Client(api_key=api_key)
        
        # Test the exact API format used in our pipeline
        instructions = "You are an expert at correcting OCR errors in French medical directories from the 19th century. Extract structured data in TSV format with columns: nom|année|notes|adresse|horaires"
        test_input = "Docteur Dupont 1885 Médecin rue de la Paix 12 consultations 2 à 4h"
        full_prompt = f"{instructions}\n\n### TEXTE OCR À TRAITER:\n{test_input}"
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt,
            config={
                'temperature': 0.0,  # Deterministic output for structured data extraction
            }
        )
        
        print("✅ Gemini API working successfully")
        print(f"📝 Response preview: {response.text[:100]}...")
        return True
        
    except ImportError:
        print("❌ Google GenAI package not installed: pip install google-genai")
        return False
    except Exception as e:
        print(f"❌ Gemini API error: {e}")
        return False

def main():
    """Run API availability tests"""
    print("🚀 LLM OCR Correction Pipeline - API Availability Test")
    print("=" * 60)
    
    openai_ok = test_openai_api()
    gemini_ok = test_gemini_api()
    
    print("\n📊 Test Summary:")
    print(f"OpenAI GPT-5 series: {'✅ Available' if openai_ok else '❌ Unavailable'}")
    print(f"Gemini 2.5 series:  {'✅ Available' if gemini_ok else '❌ Unavailable'}")
    
    if openai_ok or gemini_ok:
        print("\n� API Status Results:")
        if openai_ok and gemini_ok:
            print("✅ Both APIs are working! Full pipeline functionality available.")
        elif openai_ok:
            print("✅ OpenAI GPT-5 series is working")
            print("❌ Gemini 2.5 series is not available")
        elif gemini_ok:
            print("❌ OpenAI GPT-5 series is not available") 
            print("✅ Gemini 2.5 series is working")
            
        print("\nNext steps:")
        if openai_ok:
            print("  • Run: python llm-correction.py --year 1887 --pages 32 --model gpt-5-nano")
        if gemini_ok:
            print("  • Run: python llm-correction.py --year 1887 --pages 32 --model gemini-2.5-flash")
        return 0
    else:
        print("\n❌ Both APIs are unavailable! Pipeline cannot run.")
        print("\nSetup instructions:")
        print("  • OpenAI: Set OPENAI_API_KEY environment variable")
        print("  • Gemini: Set GEMINI_API_KEY environment variable")
        return 1

if __name__ == "__main__":
    sys.exit(main())
