"""
Project Structure Verification Script

Run this to verify the cleanup was successful and the modular structure is working.
"""

import sys
from pathlib import Path


def check_file_exists(path: str, should_exist: bool = True) -> bool:
    """Check if file exists and report status"""
    exists = Path(path).exists()
    if should_exist:
        status = "✅" if exists else "❌"
    else:
        status = "❌" if exists else "✅"
    
    action = "should exist" if should_exist else "should be deleted"
    print(f"{status} {path:50s} ({action})")
    return exists == should_exist


def main():
    print("=" * 70)
    print("PROJECT STRUCTURE VERIFICATION")
    print("=" * 70)
    
    all_good = True
    
    # Check legacy files are DELETED
    print("\n🗑️  Legacy Files (Should Be Deleted):")
    print("-" * 70)
    legacy_files = [
        "config.py",
        "database.py",
        "enums.py",
        "llm_providers.py",
        "main_old.py",
        "prompts.py",
        "schemas.py",
        "services.py",
    ]
    
    for file in legacy_files:
        if not check_file_exists(file, should_exist=False):
            all_good = False
    
    # Check new modular structure EXISTS
    print("\n📁 Modular Structure (Should Exist):")
    print("-" * 70)
    
    modular_files = [
        "app/__init__.py",
        "app/core/config.py",
        "app/core/database.py",
        "app/models/__init__.py",
        "app/routers/health.py",
        "app/routers/extraction.py",
        "app/schemas/__init__.py",
        "app/services/extraction.py",
        "app/services/llm_provider.py",
        "app/services/ocr_provider.py",
        "app/services/job_queue.py",
        "app/utils/prompts.py",
    ]
    
    for file in modular_files:
        if not check_file_exists(file, should_exist=True):
            all_good = False
    
    # Check essential files
    print("\n⚙️  Essential Files:")
    print("-" * 70)
    
    essential_files = [
        ("main.py", True),
        ("requirements.txt", True),
        (".env", True),
        (".gitignore", True),
        ("smde.db", True),
    ]
    
    for file, should_exist in essential_files:
        if not check_file_exists(file, should_exist=should_exist):
            all_good = False
    
    # Test imports
    print("\n🧪 Testing Imports:")
    print("-" * 70)
    
    try:
        from app.core.config import settings
        print(f"✅ from app.core.config import settings")
        print(f"   - JOB_TIMEOUT: {settings.JOB_TIMEOUT}s")
        print(f"   - LLM_PROVIDER: {settings.LLM_PROVIDER}")
    except Exception as e:
        print(f"❌ Failed to import config: {e}")
        all_good = False
    
    try:
        from app.services.extraction import ExtractionService
        print(f"✅ from app.services.extraction import ExtractionService")
    except Exception as e:
        print(f"❌ Failed to import extraction: {e}")
        all_good = False
    
    try:
        from app.services.ocr_provider import ocr_service
        print(f"✅ from app.services.ocr_provider import ocr_service")
    except Exception as e:
        print(f"❌ Failed to import ocr_provider: {e}")
        all_good = False
    
    try:
        from app.models import Extraction, Session
        print(f"✅ from app.models import Extraction, Session")
    except Exception as e:
        print(f"❌ Failed to import models: {e}")
        all_good = False
    
    # Summary
    print("\n" + "=" * 70)
    if all_good:
        print("✅ ALL CHECKS PASSED!")
        print("\nYour project structure is clean and modular.")
        print("Ready to commit and deploy!")
    else:
        print("⚠️  SOME CHECKS FAILED!")
        print("\nReview the output above and fix any issues.")
    print("=" * 70)
    
    return 0 if all_good else 1


if __name__ == "__main__":
    sys.exit(main())
