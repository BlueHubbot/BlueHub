#!/usr/bin/env python3
"""
Test script for DocOps Auto-Reporter

This script tests the auto_reporter.py functionality without Celery.
Run this to verify the DocOps system is working correctly.

Usage:
    python .kiro/docops/test_reporter.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from auto_reporter import DocOpsReporter


def test_basic_functionality():
    """Test basic reporter functionality."""
    print("=" * 60)
    print("🧪 Testing DocOps Reporter")
    print("=" * 60)
    print()
    
    try:
        # Initialize reporter
        print("1️⃣ Initializing reporter...")
        reporter = DocOpsReporter()
        print("   ✅ Reporter initialized successfully")
        print()
        
        # Test directory structure
        print("2️⃣ Checking directory structure...")
        assert reporter.docops_dir.exists(), "DocOps directory missing"
        assert reporter.snapshots_dir.exists(), "Snapshots directory missing"
        assert reporter.sessions_dir.exists(), "Sessions directory missing"
        print("   ✅ All directories exist")
        print()
        
        # Test tasks parsing
        print("3️⃣ Testing tasks.md parsing...")
        tasks_data = reporter.parse_tasks_progress()
        print(f"   📊 Total tasks: {tasks_data['total']}")
        print(f"   ✅ Completed: {tasks_data['completed']}")
        print(f"   🔄 In Progress: {tasks_data['in_progress']}")
        print(f"   ⛔ Blocked: {tasks_data['blocked']}")
        print(f"   📈 Progress: {tasks_data['percentage']}%")
        print()
        
        # Test requirements counting
        print("4️⃣ Testing requirements.md parsing...")
        reqs_data = reporter.count_requirements()
        print(f"   📋 Total requirements: {reqs_data['total']}")
        print(f"   ✅ Completed: {reqs_data['completed']}")
        print(f"   📈 Progress: {reqs_data['percentage']}%")
        print()
        
        # Test blockers identification
        print("5️⃣ Testing blocker identification...")
        blockers = reporter.identify_blockers()
        if blockers:
            print(f"   🚫 Found {len(blockers)} blockers:")
            for i, blocker in enumerate(blockers, 1):
                print(f"      {i}. {blocker[:80]}...")
        else:
            print("   ✅ No blockers found")
        print()
        
        # Test decisions extraction
        print("6️⃣ Testing decision extraction...")
        decisions = reporter.parse_recent_decisions()
        if decisions:
            print(f"   🗂️ Found {len(decisions)} recent decisions:")
            for i, decision in enumerate(decisions[:3], 1):
                print(f"      {i}. {decision[:80]}...")
        else:
            print("   ℹ️ No decisions found")
        print()
        
        # Test snapshot generation
        print("7️⃣ Generating test snapshot...")
        snapshot_path = reporter.generate_snapshot()
        print(f"   ✅ Snapshot created: {snapshot_path}")
        print()
        
        # Test STATUS.md update
        print("8️⃣ Updating STATUS.md...")
        reporter.update_status_file()
        print("   ✅ STATUS.md updated successfully")
        print()
        
        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        print()
        print("📂 Generated files:")
        print(f"   - {snapshot_path}")
        print(f"   - {reporter.docops_dir / 'STATUS.md'}")
        print()
        print("🎉 DocOps system is working correctly!")
        
        return True
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ Test failed!")
        print("=" * 60)
        print(f"Error: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        return False


def test_celery_integration():
    """Test Celery integration (if Celery is available)."""
    print()
    print("=" * 60)
    print("🧪 Testing Celery Integration")
    print("=" * 60)
    print()
    
    try:
        from celery import Celery
        print("✅ Celery is installed")
        
        # Create dummy Celery app
        app = Celery('test', broker='redis://localhost:6379/0')
        print("✅ Dummy Celery app created")
        
        from auto_reporter import setup_celery_task
        task = setup_celery_task(app)
        print("✅ Celery task registered")
        
        print()
        print("ℹ️ To run scheduled task:")
        print("   celery -A services.celery_app beat")
        print()
        
        return True
        
    except ImportError:
        print("⚠️ Celery not installed (optional)")
        print("   Install with: pip install celery[redis]")
        return True  # Not a failure
        
    except Exception as e:
        print(f"❌ Celery integration test failed: {e}")
        return False


def show_usage_examples():
    """Show usage examples."""
    print()
    print("=" * 60)
    print("📖 Usage Examples")
    print("=" * 60)
    print()
    
    print("1️⃣ Run auto-reporter manually:")
    print("   python .kiro/docops/auto_reporter.py")
    print()
    
    print("2️⃣ Run this test script:")
    print("   python .kiro/docops/test_reporter.py")
    print()
    
    print("3️⃣ Schedule with Celery Beat:")
    print("   # In services/celery_app.py:")
    print("   from docops.auto_reporter import setup_celery_task")
    print("   setup_celery_task(celery_app)")
    print()
    print("   # Then run:")
    print("   celery -A services.celery_app beat")
    print()
    
    print("4️⃣ Use /session-end command in Kiro:")
    print("   /session-end")
    print("   (Follow the prompts)")
    print()
    
    print("5️⃣ View current status:")
    print("   cat .kiro/docops/STATUS.md")
    print()
    
    print("6️⃣ View latest snapshot:")
    print("   ls -lt .kiro/docops/snapshots/ | head -2")
    print()


def main():
    """Main test runner."""
    print()
    print("🚀 BlueHub DocOps System Test Suite")
    print()
    
    # Run tests
    basic_test = test_basic_functionality()
    celery_test = test_celery_integration()
    
    # Show usage
    show_usage_examples()
    
    # Summary
    print("=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    print()
    print(f"Basic Functionality:   {'✅ PASS' if basic_test else '❌ FAIL'}")
    print(f"Celery Integration:    {'✅ PASS' if celery_test else '❌ FAIL'}")
    print()
    
    if basic_test and celery_test:
        print("🎉 All tests passed! DocOps system is ready to use.")
        print()
        print("Next steps:")
        print("1. Review .kiro/docops/STATUS.md")
        print("2. Check the latest snapshot in .kiro/docops/snapshots/")
        print("3. Try the /session-end command in Kiro")
        print("4. Setup Celery Beat for automatic reports")
        return 0
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
