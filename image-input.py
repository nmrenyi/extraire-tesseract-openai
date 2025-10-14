#!/usr/bin/env python3
"""
Dual Model Image OCR Processing for Rosenwald Medical Directory
Uses both OpenAI Vision API and Google Gemini Vision API to extract structured medical directory data
"""

from openai import OpenAI
from google import genai
from pathlib import Path
import os
import argparse

def load_instructions():
    """Load the instruction template from instructions-image-input.txt and instructions-example-output.tsv"""
    # Load image-specific instructions
    with open("instructions-image-input.txt", 'r', encoding='utf-8') as f:
        instructions = f.read().strip()
    
    # Load example output
    with open("instructions-example-output.tsv", 'r', encoding='utf-8') as f:
        example_output = f.read().strip()
    
    # Combine instructions with example
    full_prompt = f"{instructions}\n\n### EXEMPLE DE FORMAT ATTENDU:\n{example_output}\n\n### IMAGE À TRAITER:\nAnalysez l'image ci-jointe et extrayez les données médicales selon les instructions ci-dessus."
    
    return full_prompt

def process_with_openai(image_path, output_path, model="gpt-5"):
    """Process image with OpenAI Vision API"""
    print(f"🔵 Processing with {model.upper()} Vision API...")
    
    client = OpenAI()
    
    # Load instructions
    prompt = load_instructions()
    
    # Upload image file
    with open(image_path, "rb") as file_content:
        file_upload = client.files.create(
            file=file_content,
            purpose="vision",
        )
        file_id = file_upload.id
    
    print(f"Image uploaded with file ID: {file_id}")
    
    # Process with OpenAI Vision API
    response = client.responses.create(
        model=model,
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {
                    "type": "input_image", 
                    "file_id": file_id,
                },
            ],
        }],
    )
    
    # Extract and save result
    result_text = response.output_text.strip()
    
    # Save to output file
    openai_output = output_path.replace('.tsv', f'-{model}.tsv')
    with open(openai_output, 'w', encoding='utf-8') as f:
        f.write(result_text)
    
    print(f"✅ {model.upper()} results saved to: {openai_output}")
    return result_text

def process_with_gemini(image_path, output_path, model="gemini-2.5-flash"):
    """Process image with Google Gemini Vision API"""
    print(f"🔴 Processing with {model.upper()} Vision API...")
    
    # Check for API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY environment variable not set")
        return None
    
    client = genai.Client(api_key=api_key)
    
    # Load instructions
    prompt = load_instructions()
    
    # Upload image file
    uploaded_file = client.files.upload(file=image_path)
    print(f"Image uploaded with file ID: {uploaded_file.name}")
    
    # Process with Gemini Vision API
    response = client.models.generate_content(
        model=model,
        contents=[uploaded_file, prompt],
        config={
            'temperature': 0.0,  # Deterministic output for structured data extraction
        }
    )
    
    # Extract and save result
    result_text = response.text.strip()
    
    # Save to output file
    gemini_output = output_path.replace('.tsv', f'-{model}.tsv')
    with open(gemini_output, 'w', encoding='utf-8') as f:
        f.write(result_text)
    
    print(f"✅ {model.upper()} results saved to: {gemini_output}")
    return result_text

def main():
    """Main processing function"""
    parser = argparse.ArgumentParser(description='Process image with OpenAI and/or Gemini vision models')
    parser.add_argument('--model', 
                       choices=['gpt-5', 'gpt-5-mini', 'gemini-2.5-pro', 'gemini-2.5-flash', 'openai', 'gemini', 'both'], 
                       default='both',
                       help='Which model to use (default: both)')
    parser.add_argument('--image', default='rosenwald-images/1887/1887-page-0032.png',
                       help='Path to input image')
    parser.add_argument('--output', default='llm-corrected-results/only-llm/1887-page-0032.tsv',
                       help='Path for output file')
    
    args = parser.parse_args()
    
    # Check if image exists
    if not Path(args.image).exists():
        print(f"❌ Error: Image file '{args.image}' does not exist")
        return False
    
    # Create output directory
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Processing image: {args.image}")
    print(f"Output directory: {Path(args.output).parent}")
    print(f"Selected model(s): {args.model}")
    print("-" * 60)
    
    results = {}
    
    # Determine which models to run
    openai_models = ['gpt-5', 'gpt-5-mini']
    gemini_models = ['gemini-2.5-pro', 'gemini-2.5-flash']
    
    try:
        # Process with selected models
        if args.model in openai_models:
            results[args.model] = process_with_openai(args.image, args.output, args.model)
            print()
        elif args.model in gemini_models:
            results[args.model] = process_with_gemini(args.image, args.output, args.model)
            print()
        elif args.model == 'openai':
            # Run both OpenAI models
            for model in openai_models:
                results[model] = process_with_openai(args.image, args.output, model)
                print()
        elif args.model == 'gemini':
            # Run both Gemini models
            for model in gemini_models:
                results[model] = process_with_gemini(args.image, args.output, model)
                print()
        elif args.model == 'both':
            # Run all models
            for model in openai_models:
                results[model] = process_with_openai(args.image, args.output, model)
                print()
            for model in gemini_models:
                results[model] = process_with_gemini(args.image, args.output, model)
                print()
        
        # Summary
        print("📊 Processing Summary:")
        print("-" * 30)
        for model, result in results.items():
            if result:
                lines = len([line for line in result.split('\n') if line.strip() and not line.startswith('nom')])
                print(f"{model.upper()}: {lines} medical entries extracted")
            else:
                print(f"{model.upper()}: Failed to process")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        return False

if __name__ == "__main__":
    main()
