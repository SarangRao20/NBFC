#!/usr/bin/env python3
"""Fix tenure adjustment logic in sales_agent.py"""

import re

# Read the file
with open("agents/sales_agent.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find and replace the section in _sales_mode
old_pattern = r'(updates\["eligible_offers"\] = offers\s*)\n(\s*# If user already selected a lender via button:)'

new_text = r'''\1
            
            # ─── CHECK IF ANY OFFER HAS ADJUSTED TENURE ───────────────────
            if offers and offers[0].get("approved_tenure"):
                approved_tenure = offers[0]["approved_tenure"]
                if approved_tenure != new_terms["tenure"]:
                    log.append(f"📝 Tenure adjusted from {new_terms['tenure']} to {approved_tenure} months (closest available)")
                    new_terms["tenure"] = approved_tenure
                    # Sync all offers with the approved tenure
                    for offer in offers:
                        offer["approved_tenure"] = approved_tenure
\2'''

content_new = re.sub(old_pattern, new_text, content)

# Check if replacement was made
if content_new != content:
    print("✓ Successfully inserted tenure adjustment logic")
    # Write back
    with open("agents/sales_agent.py", "w", encoding="utf-8") as f:
        f.write(content_new)
    print("✓ File saved")
else:
    print("✗ No match found - pattern may need adjustment")
    # Try to find the line
    for i, line in enumerate(content.split('\n'), 1):
        if 'eligible_offers' in line:
            print(f"Line {i}: {line[:80]}")
