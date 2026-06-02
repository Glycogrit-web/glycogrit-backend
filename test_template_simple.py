#!/usr/bin/env python3
"""
Simple test to show the template validation logic
"""

# The 4 required tags (uppercase format)
REQUIRED_TAGS = {
    "{{PARTICIPANT_NAME}}",   # User name
    "{{ACTIVITY_DISTANCE}}",  # Activity distance selected for tier registration
    "{{ACTIVITY_NAME}}",      # Activity name selected for tier registration
    "{{EVENT_NAME}}",         # Event name in which user registered
}

# All supported tags (uppercase + lowercase for compatibility)
SUPPORTED_TAGS = {
    "{{PARTICIPANT_NAME}}": "Participant Name",
    "{{ACTIVITY_DISTANCE}}": "Activity Distance Completed",
    "{{ACTIVITY_NAME}}": "Activity Type",
    "{{EVENT_NAME}}": "Event/Challenge Name",
    # Legacy lowercase tags for backward compatibility
    "{{name}}": "Participant Name",
    "{{full_name}}": "Participant Full Name",
    "{{distance}}": "Distance Completed",
    "{{activity_name}}": "Activity Type",
    "{{challenge_name}}": "Challenge/Event Name",
    "{{event_name}}": "Event Name",
    "{{date}}": "Completion Date",
    "{{sport}}": "Sport Type",
    "{{certificate_number}}": "Certificate Number",
    "{{digital_signature}}": "Digital Signature",
    "{{registration_number}}": "Registration Number",
    "{{bib_number}}": "Bib Number",
}

def validate_required_tags(detected_tags):
    """
    Validate that all required tags are present

    Args:
        detected_tags: List of tag strings detected by OCR

    Returns:
        Tuple of (is_valid, missing_tags)
    """
    detected_tag_names = set(detected_tags)
    missing_tags = REQUIRED_TAGS - detected_tag_names

    if missing_tags:
        print(f"\n⚠️  Required tags missing: {missing_tags}")
        print(f"Detected: {detected_tag_names}")
        return False, sorted(list(missing_tags))

    print(f"\n✅ All required tags detected: {REQUIRED_TAGS}")
    return True, []


def test_scenario(scenario_name, detected_tags):
    """Test a specific scenario"""
    print(f"\n{'='*80}")
    print(f"SCENARIO: {scenario_name}")
    print(f"{'='*80}")

    print(f"\nDetected tags: {detected_tags}")

    is_valid, missing_tags = validate_required_tags(detected_tags)

    if is_valid:
        print("\n✅ PASS: Template would be accepted")
    else:
        print(f"\n❌ FAIL: Template would be rejected")
        print(f"Missing required tags: {', '.join(missing_tags)}")
        print(f"\nError message that would be shown:")
        print(f"  Template is missing required tags: {', '.join(missing_tags)}.")
        print(f"  Required tags: {{{{PARTICIPANT_NAME}}}}, {{{{ACTIVITY_DISTANCE}}}}, {{{{ACTIVITY_NAME}}}}, {{{{EVENT_NAME}}}}.")
        print(f"  Please add the missing tags to your template and try again.")

    return is_valid


if __name__ == "__main__":
    print("\n" + "="*80)
    print("CERTIFICATE TEMPLATE VALIDATION TEST")
    print("="*80)

    # Test Scenario 1: Perfect template with all uppercase tags
    test_scenario(
        "Perfect Template (Uppercase Tags)",
        [
            "{{PARTICIPANT_NAME}}",
            "{{ACTIVITY_DISTANCE}}",
            "{{ACTIVITY_NAME}}",
            "{{EVENT_NAME}}",
            "{{date}}",
        ]
    )

    # Test Scenario 2: Legacy template with lowercase tags (should FAIL)
    test_scenario(
        "Legacy Template (Lowercase Tags) - Expected to FAIL",
        [
            "{{name}}",
            "{{distance}}",
            "{{activity_name}}",
            "{{event_name}}",
            "{{date}}",
        ]
    )

    # Test Scenario 3: Mixed case template
    test_scenario(
        "Mixed Case Template",
        [
            "{{PARTICIPANT_NAME}}",
            "{{ACTIVITY_DISTANCE}}",
            "{{activity_name}}",  # lowercase (should fail)
            "{{event_name}}",     # lowercase (should fail)
        ]
    )

    # Test Scenario 4: Missing one required tag
    test_scenario(
        "Missing ACTIVITY_NAME Tag",
        [
            "{{PARTICIPANT_NAME}}",
            "{{ACTIVITY_DISTANCE}}",
            "{{EVENT_NAME}}",
            "{{date}}",
        ]
    )

    # Test Scenario 5: Template for your image (simulated)
    # This simulates what OCR might detect from your certificate template
    print("\n\n" + "="*80)
    print("SIMULATION: Your Certificate Template")
    print("="*80)
    print("\nAssuming your certificate template image contains:")
    print("  1. A placeholder for participant name")
    print("  2. A placeholder for activity distance")
    print("  3. A placeholder for activity type")
    print("  4. A placeholder for event name")
    print("\nFor the template to be accepted, Tesseract OCR must detect these as:")
    print("  • {{PARTICIPANT_NAME}}")
    print("  • {{ACTIVITY_DISTANCE}}")
    print("  • {{ACTIVITY_NAME}}")
    print("  • {{EVENT_NAME}}")
    print("\nYou should place these exact tags in your template image.")
    print("\nNote: If you want to use the deployed Railway API to test,")
    print("you would need to:")
    print("  1. Log in as admin")
    print("  2. Upload your template via the admin panel")
    print("  3. The system will automatically run OCR and validate")

    print("\n" + "="*80 + "\n")
