import subprocess

# Simple OCR with PSM 3 and French language
image_path = "rosenwald-images/1887/1887-page-001.png"

# Run tesseract with PSM 3 (Automatic page segmentation) and French language
result = subprocess.run([
    'tesseract', image_path, 'stdout', 
    '-l', 'fra',           # French language
    '--psm', '3'           # Automatic page segmentation
], capture_output=True, text=True)

if result.returncode == 0:
    print(result.stdout)
else:
    print(f"Error: {result.stderr}")