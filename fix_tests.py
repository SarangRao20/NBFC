import re
import os

# Get the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))

files = [
    os.path.join(script_dir, 'tests', 'test_e2e_marketplace.py'),
    os.path.join(script_dir, 'tests', 'test_comparison_api.py')
]

for filename in files:
    try:
        with open(filename, 'r') as f:
            content = f.read()
        
        # Remove employment_type parameters with various spacing
        content = re.sub(r',\s*employment_type\s*=\s*["\'][\w]*["\']', '', content)
        
        with open(filename, 'w') as f:
            f.write(content)
        
        print(f'Fixed: {filename}')
    except Exception as e:
        print(f'Error: {e}')

print('Done!')
