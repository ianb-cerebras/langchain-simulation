#!/usr/bin/env python3
"""
Test script for UXR integration
Tests both LangGraph (if available) and enhanced_uxr fallback
"""

import json
import os
import sys

def test_uxr_api():
    """Test the uxr_api module"""
    print("Testing UXR API Integration...")
    print("-" * 50)
    
    # Set test parameters
    test_cases = [
        {
            "question": "How do users feel about AI assistants?",
            "audience": "Technology professionals aged 25-45",
            "num_interviews": 3,
            "num_questions": 2
        },
        {
            "question": "What features do users want in a mobile app?",
            "audience": "Gen Z users",
            "num_interviews": 2,
            "num_questions": 3
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Question: {test['question']}")
        print(f"Audience: {test['audience']}")
        
        # Set environment variables
        os.environ["UXR_QUESTION"] = test["question"]
        os.environ["UXR_AUDIENCE"] = test["audience"]
        os.environ["UXR_NUM_INTERVIEWS"] = str(test["num_interviews"])
        os.environ["UXR_NUM_QUESTIONS"] = str(test["num_questions"])
        
        try:
            from uxr_api import run_langgraph_research
            
            result = run_langgraph_research(
                test["question"],
                test["audience"],
                test["num_interviews"],
                test["num_questions"]
            )
            
            # Validate result structure
            assert "keyInsights" in result, "Missing keyInsights"
            assert "observations" in result, "Missing observations"
            assert "takeaways" in result, "Missing takeaways"
            assert "participants" in result, "Missing participants"
            
            print(f"✅ Test passed!")
            print(f"   - Generated {len(result['participants'])} participants")
            print(f"   - Key insight: {result['keyInsights'][:100]}...")
            
            if "metadata" in result:
                print(f"   - Workflow used: {result['metadata'].get('workflow', 'unknown')}")
                if "execution_time" in result["metadata"]:
                    print(f"   - Execution time: {result['metadata']['execution_time']}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False
    
    print("\n" + "=" * 50)
    print("✅ All tests passed!")
    return True

def test_enhanced_uxr():
    """Test the enhanced_uxr module directly"""
    print("\nTesting Enhanced UXR (Fallback)...")
    print("-" * 50)
    
    os.environ["UXR_QUESTION"] = "Test question for fallback"
    os.environ["UXR_AUDIENCE"] = "Test audience"
    os.environ["UXR_NUM_INTERVIEWS"] = "2"
    
    try:
        from enhanced_uxr import main
        from io import StringIO
        import contextlib
        
        f = StringIO()
        with contextlib.redirect_stdout(f):
            main()
        output = f.getvalue()
        
        # Parse JSON
        json_start = output.find('{')
        json_end = output.rfind('}') + 1
        json_str = output[json_start:json_end]
        result = json.loads(json_str)
        
        assert "participants" in result
        assert len(result["participants"]) == 2
        print("✅ Enhanced UXR test passed!")
        
    except Exception as e:
        print(f"❌ Enhanced UXR test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = True
    
    # Test enhanced_uxr first (simpler, more likely to work)
    if not test_enhanced_uxr():
        success = False
    
    # Test full uxr_api integration
    if not test_uxr_api():
        success = False
    
    sys.exit(0 if success else 1)