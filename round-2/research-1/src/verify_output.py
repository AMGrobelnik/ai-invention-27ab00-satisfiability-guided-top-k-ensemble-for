#!/usr/bin/env python3
"""Verify the output JSON files are valid and complete."""
import json
import sys

def verify_file(filepath, required_fields):
    """Verify a JSON file has all required fields."""
    print(f"\n=== Verifying: {filepath} ===")
    try:
        with open(filepath, 'r') as f:
            d = json.load(f)
        print(f"  JSON: VALID")
        
        # Check required fields
        missing = [f for f in required_fields if f not in d]
        if missing:
            print(f"  MISSING fields: {missing}")
            return False
        else:
            print(f"  All required fields present: {list(d.keys())}")
        
        # Check specific content
        print(f"  Title ({len(d.get('title', ''))} chars): {d.get('title', '')[:60]}...")
        print(f"  Layman summary: {len(d.get('layman_summary', ''))} chars")
        print(f"  Summary: {len(d.get('summary', ''))} chars")
        print(f"  Answer: {len(d.get('answer', ''))} chars")
        print(f"  Sources: {len(d.get('sources', []))} entries")
        print(f"  Follow-up questions: {len(d.get('follow_up_questions', []))} entries")
        print(f"  Output file: {d.get('out_expected_files', {})}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"  JSON: INVALID - {e}")
        return False
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

# Required fields for the output schema
required_fields = ['title', 'layman_summary', 'summary', 'out_expected_files', 'answer', 'sources', 'follow_up_questions']

# Verify both files
struct_file = '/home/adrian/projects/ai-inventor/aii_data/users/admin/runs/run_Vh8gS7VoXSfi/3_invention_loop/iter_2/gen_art/gen_art_research_1/.sdk_openhands_agent_struct_out.json'
research_file = '/home/adrian/projects/ai-inventor/aii_data/users/admin/runs/run_Vh8gS7VoXSfi/3_invention_loop/iter_2/gen_art/gen_art_research_1/research_out.json'

success1 = verify_file(struct_file, required_fields)
success2 = verify_file(research_file, required_fields)

print(f"\n=== FINAL RESULT ===")
print(f"Struct output file: {'PASS' if success1 else 'FAIL'}")
print(f"Research output file: {'PASS' if success2 else 'FAIL'}")

if success1 and success2:
    print("\nAll files are valid and complete!")
    sys.exit(0)
else:
    print("\nSome files have issues!")
    sys.exit(1)
