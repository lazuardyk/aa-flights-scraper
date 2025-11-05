#!/usr/bin/env python3
"""Test script to verify the parser works with saved JSON responses"""
import json
import sys
import os

# Add parent directory to path to import scrape module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrape import merge_pricing_data, generate_output

# Get the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Load saved responses
with open(os.path.join(script_dir, "award_pricing_response.json"), "r") as f:
    award_response = json.load(f)

with open(os.path.join(script_dir, "revenue_pricing_response.json"), "r") as f:
    revenue_response = json.load(f)

# Test parsing (COACH economy only)
print("Testing parser with saved responses (COACH economy only)...")
flights = merge_pricing_data(award_response, revenue_response)

# Generate output
output = generate_output("LAX", "JFK", "2025-12-15", 1, flights)

# Save output
output_path = os.path.join(script_dir, "test_output.json")
with open(output_path, "w") as f:
    json.dump(output, f, indent=2)

print(f"\nFound {len(flights)} flights with both award and cash pricing")
print(f"Results saved to {output_path}\n")

if flights:
    print("Sample flights:")
    for i, flight in enumerate(flights[:3], 1):
        segments_str = " → ".join([f"{s['flight_number']}" for s in flight["segments"]])
        print(f"  {i}. {segments_str}")
        print(f"     Duration: {flight['total_duration']}")
        print(f"     Points: {flight['points_required']:,} + ${flight['taxes_fees_usd']:.2f}")
        print(f"     Cash: ${flight['cash_price_usd']:.2f}")
        print(f"     CPP: {flight['cpp']:.2f}")
        print()
