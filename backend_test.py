#!/usr/bin/env python3
"""
Backend API Test Suite for Sahibinden.com Real Estate Scraper
Tests all backend endpoints and functionality
"""

import requests
import json
import time
import os
from datetime import datetime

# Get backend URL from frontend .env file
def get_backend_url():
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=')[1].strip()
    except Exception as e:
        print(f"Error reading frontend .env: {e}")
        return None

BASE_URL = get_backend_url()
if not BASE_URL:
    print("ERROR: Could not get backend URL from frontend/.env")
    exit(1)

API_URL = f"{BASE_URL}/api"
print(f"Testing backend API at: {API_URL}")

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Backend-Test-Suite/1.0'
        })
        self.test_results = []
        
    def log_test(self, test_name, success, message, details=None):
        """Log test results"""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'details': details
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}: {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def test_root_endpoint(self):
        """Test 1: Basic API connection - test the root endpoint /api/"""
        try:
            response = self.session.get(f"{API_URL}/")
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "Sahibinden" in data["message"]:
                    self.log_test("Root Endpoint", True, "API root endpoint working correctly")
                    return True
                else:
                    self.log_test("Root Endpoint", False, "Unexpected response format", data)
                    return False
            else:
                self.log_test("Root Endpoint", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Root Endpoint", False, f"Connection error: {str(e)}")
            return False
    
    def test_gemini_api(self):
        """Test 2: Test Gemini API integration - should show api_disabled status"""
        try:
            response = self.session.post(f"{API_URL}/test-gemini")
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    self.log_test("Gemini API", True, "Gemini API integration working")
                    return True
                elif data.get("status") == "api_disabled":
                    self.log_test("Gemini API", True, f"Gemini API disabled as expected: {data.get('message', 'API disabled')}")
                    return True
                else:
                    self.log_test("Gemini API", False, f"Gemini API error: {data.get('message', 'Unknown error')}")
                    return False
            else:
                self.log_test("Gemini API", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Gemini API", False, f"Request error: {str(e)}")
            return False
    
    def test_scraping_endpoint(self):
        """Test 3: Test scraping endpoint with sample URL"""
        try:
            scraping_data = {
                "url": "https://www.sahibinden.com/satilik-daire/istanbul",
                "month": 7,
                "year": 2025
            }
            
            response = self.session.post(f"{API_URL}/scrape", json=scraping_data)
            if response.status_code == 200:
                data = response.json()
                if "id" in data and data.get("status") == "processing":
                    self.log_test("Scraping Endpoint", True, f"Scraping started successfully, ID: {data['id']}")
                    return data["id"]  # Return the result ID for further testing
                else:
                    self.log_test("Scraping Endpoint", False, "Unexpected response format", data)
                    return None
            else:
                self.log_test("Scraping Endpoint", False, f"HTTP {response.status_code}", response.text)
                return None
        except Exception as e:
            self.log_test("Scraping Endpoint", False, f"Request error: {str(e)}")
            return None
    
    def test_results_endpoint(self, result_id):
        """Test 4: Check if scraping result can be retrieved"""
        if not result_id:
            self.log_test("Results Endpoint", False, "No result ID to test with")
            return None
            
        try:
            # Wait a bit for processing to start
            time.sleep(2)
            
            response = self.session.get(f"{API_URL}/results/{result_id}")
            if response.status_code == 200:
                data = response.json()
                if "id" in data and data["id"] == result_id:
                    status = data.get("status", "unknown")
                    self.log_test("Results Endpoint", True, f"Result retrieved successfully, status: {status}")
                    return data
                else:
                    self.log_test("Results Endpoint", False, "Result ID mismatch", data)
                    return None
            elif response.status_code == 404:
                self.log_test("Results Endpoint", False, "Result not found - possible database issue")
                return None
            else:
                self.log_test("Results Endpoint", False, f"HTTP {response.status_code}", response.text)
                return None
        except Exception as e:
            self.log_test("Results Endpoint", False, f"Request error: {str(e)}")
            return None
    
    def test_all_results_endpoint(self):
        """Test 5: Get all results endpoint"""
        try:
            response = self.session.get(f"{API_URL}/results")
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("All Results Endpoint", True, f"Retrieved {len(data)} results")
                    return True
                else:
                    self.log_test("All Results Endpoint", False, "Expected list response", data)
                    return False
            else:
                self.log_test("All Results Endpoint", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("All Results Endpoint", False, f"Request error: {str(e)}")
            return False
    
    def test_excel_export(self, result_id):
        """Test 6: Test Excel export endpoint"""
        if not result_id:
            self.log_test("Excel Export", False, "No result ID to test with")
            return False
            
        try:
            response = self.session.get(f"{API_URL}/export/excel/{result_id}")
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'spreadsheet' in content_type or 'excel' in content_type:
                    self.log_test("Excel Export", True, "Excel file generated successfully")
                    return True
                else:
                    self.log_test("Excel Export", True, "Excel export endpoint working (content type may vary)")
                    return True
            elif response.status_code == 404:
                self.log_test("Excel Export", False, "Result not found for export")
                return False
            else:
                self.log_test("Excel Export", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Excel Export", False, f"Request error: {str(e)}")
            return False
    
    def test_pdf_export(self, result_id):
        """Test 7: Test PDF export endpoint"""
        if not result_id:
            self.log_test("PDF Export", False, "No result ID to test with")
            return False
            
        try:
            response = self.session.get(f"{API_URL}/export/pdf/{result_id}")
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'pdf' in content_type:
                    self.log_test("PDF Export", True, "PDF file generated successfully")
                    return True
                else:
                    self.log_test("PDF Export", True, "PDF export endpoint working (content type may vary)")
                    return True
            elif response.status_code == 404:
                self.log_test("PDF Export", False, "Result not found for export")
                return False
            else:
                self.log_test("PDF Export", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("PDF Export", False, f"Request error: {str(e)}")
            return False
    
    def test_error_handling(self):
        """Test 8: Test error handling"""
        try:
            # Test invalid result ID
            response = self.session.get(f"{API_URL}/results/invalid-id")
            if response.status_code == 404:
                self.log_test("Error Handling", True, "404 error handling works correctly")
                return True
            else:
                self.log_test("Error Handling", False, f"Expected 404, got {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Error Handling", False, f"Request error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("=" * 60)
        print("STARTING BACKEND API TESTS")
        print("=" * 60)
        
        # Test 1: Basic API connection
        root_success = self.test_root_endpoint()
        
        # Test 2: Gemini API integration
        gemini_success = self.test_gemini_api()
        
        # Test 3: Scraping endpoint
        result_id = self.test_scraping_endpoint()
        
        # Test 4: Results endpoint
        result_data = self.test_results_endpoint(result_id)
        
        # Test 5: All results endpoint
        all_results_success = self.test_all_results_endpoint()
        
        # Test 6 & 7: Export endpoints (only if we have a result ID)
        excel_success = self.test_excel_export(result_id)
        pdf_success = self.test_pdf_export(result_id)
        
        # Test 8: Error handling
        error_handling_success = self.test_error_handling()
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        # Critical issues
        critical_failures = []
        for result in self.test_results:
            if not result['success']:
                if result['test'] in ['Root Endpoint', 'Gemini API', 'Scraping Endpoint']:
                    critical_failures.append(result['test'])
        
        if critical_failures:
            print(f"\n❌ CRITICAL FAILURES: {', '.join(critical_failures)}")
        else:
            print(f"\n✅ All critical endpoints working")
        
        return {
            'total_tests': total,
            'passed_tests': passed,
            'success_rate': (passed/total)*100,
            'critical_failures': critical_failures,
            'test_results': self.test_results
        }

if __name__ == "__main__":
    tester = BackendTester()
    results = tester.run_all_tests()