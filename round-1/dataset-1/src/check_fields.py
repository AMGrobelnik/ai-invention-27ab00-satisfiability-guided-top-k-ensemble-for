#!/usr/bin/env python3
"""Check field names in source datasets."""
import json

# Check RuleTaker
print("=== RuleTaker ===")
with open("temp/datasets/full_ruletaker.json") as f:
    data = json.load(f)
print("Fields:", list(data[0].keys()))
print("First example:")
print(json.dumps(data[0], indent=2)[:500])
print()

# Check FOLIO  
print("=== FOLIO ===")
with open("temp/datasets/full_folio.json") as f:
    data = json.load(f)
print("Fields:", list(data[0].keys()))
print("First example:")
print(json.dumps(data[0], indent=2)[:500])
print()

# Check ProofWriter
print("=== ProofWriter ===")
with open("temp/datasets/full_proofwriter.json") as f:
    data = json.load(f)
print("Fields:", list(data[0].keys()))
print("First example:")
print(json.dumps(data[0], indent=2)[:500])
