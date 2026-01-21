#!/usr/bin/env python3  
"""  
Comprehensive test runner for Universal Document Parser  
"""  
import subprocess  
import sys  
import os  
from pathlib import Path  
  
def run_test_suite(test_name, test_file, description):  
    """Run a specific test suite and report results"""  
    print(f"\n{'='*80}")  
    print(f"🧪 {description}")  
    print(f"File: {test_file}")  
    print('='*80)  
      
    if test_file.endswith('manual.py'):  
        # Run manual tests differently  
        cmd = f"python {test_file}"  
    elif test_file == "test_real_files.py":  
        # Run real file tests with verbose output to see file details  
        cmd = f"pytest {test_file} -v -s --tb=short"  
    else:  
        cmd = f"pytest {test_file} -v --tb=short"  
      
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)  
      
    if result.returncode == 0:  
        print(f"✅ {test_name} PASSED")  
        if 'passed' in result.stdout:  
            lines = result.stdout.split('\n')  
            for line in lines:  
                if 'passed' in line and ('=' in line or 'Manual' in line):  
                    print(f"   {line.strip()}")  
    else:  
        print(f"❌ {test_name} FAILED")  
        print("STDOUT:", result.stdout[-500:])  
        if result.stderr:  
            print("STDERR:", result.stderr[-500:])  
      
    return result.returncode == 0  
  
def check_test_files():  
    """Check if test files directory exists and show summary"""  
    test_files_dir = Path(__file__).parent.parent / "test_files"  
      
    if test_files_dir.exists():  
        files = list(test_files_dir.glob("*"))  
        print(f"📁 Found {len(files)} test files in {test_files_dir.name}/:")  
          
        total_size = 0  
        txt_count = 0  
        pdf_count = 0  
          
        for f in sorted(files, key=lambda x: x.stat().st_size):  
            size = f.stat().st_size  
            total_size += size  
            size_mb = size / 1024 / 1024  
              
            if f.suffix == '.txt':  
                txt_count += 1  
            elif f.suffix == '.pdf':  
                pdf_count += 1  
                  
            print(f"   {f.name} ({size_mb:.1f} MB)")  
          
        print(f"   📊 Summary: {txt_count} text files, {pdf_count} PDF files")  
        print(f"   💾 Total size: {total_size/1024/1024:.1f} MB")  
        return True  
    else:  
        print(f"⚠️  Test files directory not found: {test_files_dir}")  
        print("   Real file tests will be skipped")  
        return False  
  
def main():  
    """Run all test suites"""  
    print("🚀 Starting Universal Document Parser Test Suite")  
      
    test_dir = Path(__file__).parent  
    os.chdir(test_dir)  
      
    # Check test files  
    has_test_files = check_test_files()  
      
    results = []  
      
    # Updated test suites list - ADD YOUR NEW TEST HERE  
    test_suites = [  
        ("Unit Tests", "test_document_parser.py", "Core functionality and utilities"),  
        ("Integration Tests", "test_integration.py", "End-to-end workflows"),  
        ("MCP Server Tests", "test_mcp_server.py", "MCP server integration"),  
        ("Manual MCP Test", "test_mcp_manual.py", "Manual MCP server validation"),  
        ("Real File Tests", "test_real_files.py", "Testing with actual documents"),  # 👈 ADD THIS LINE  
    ]  
      
    for name, file, desc in test_suites:  
        if os.path.exists(file):  
            # Skip real file tests if no test files available  
            if file == "test_real_files.py" and not has_test_files:  
                print(f"⚠️  Skipping {name} - no test files found")  
                results.append((name, False))  
                continue  
                  
            success = run_test_suite(name, file, desc)  
            results.append((name, success))  
        else:  
            print(f"⚠️  {file} not found, skipping {name}")  
            results.append((name, False))  
      
    # Summary  
    print(f"\n{'='*80}")  
    print("📊 TEST SUMMARY")  
    print('='*80)  
      
    passed = sum(1 for _, success in results if success)  
    total = len(results)  
      
    for name, success in results:  
        status = "✅ PASSED" if success else "❌ FAILED"  
        print(f"{name:25} {status}")  
      
    print(f"\nOverall: {passed}/{total} test suites passed")  
      
    if passed == total:  
        print("🎉 All test suites passed!")  
        return 0  
    else:  
        print("💥 Some test suites failed. Check individual results above.")  
        return 1  
  
if __name__ == "__main__":  
    sys.exit(main())  
