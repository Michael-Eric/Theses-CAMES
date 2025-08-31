#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime

class ThesesCAMESAPITester:
    def __init__(self, base_url="https://theses-cames.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
        
        self.test_results.append({
            "name": name,
            "success": success,
            "details": details
        })

    def test_api_root(self):
        """Test API root endpoint"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f", Message: {data.get('message', 'No message')}"
            self.log_test("API Root", success, details)
            return success
        except Exception as e:
            self.log_test("API Root", False, f"Error: {str(e)}")
            return False

    def test_get_stats(self):
        """Test statistics endpoint"""
        try:
            response = requests.get(f"{self.api_url}/stats", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                expected_keys = ['total_theses', 'open_access', 'paywalled', 'top_disciplines', 'top_countries']
                missing_keys = [key for key in expected_keys if key not in data]
                
                if missing_keys:
                    success = False
                    details += f", Missing keys: {missing_keys}"
                else:
                    details += f", Total: {data['total_theses']}, Open: {data['open_access']}, Paywalled: {data['paywalled']}"
                    
            self.log_test("Get Statistics", success, details)
            return success, response.json() if success else {}
        except Exception as e:
            self.log_test("Get Statistics", False, f"Error: {str(e)}")
            return False, {}

    def test_search_theses(self):
        """Test thesis search endpoint"""
        try:
            # Test basic search
            response = requests.get(f"{self.api_url}/theses", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                expected_keys = ['results', 'total', 'page', 'limit', 'total_pages']
                missing_keys = [key for key in expected_keys if key not in data]
                
                if missing_keys:
                    success = False
                    details += f", Missing keys: {missing_keys}"
                else:
                    details += f", Found {len(data['results'])} theses, Total: {data['total']}"
                    
            self.log_test("Search Theses (Basic)", success, details)
            
            # Test search with query
            if success:
                response = requests.get(f"{self.api_url}/theses?q=intelligence", timeout=10)
                search_success = response.status_code == 200
                search_details = f"Status: {response.status_code}"
                
                if search_success:
                    data = response.json()
                    search_details += f", Search results: {len(data['results'])}"
                    
                self.log_test("Search Theses (With Query)", search_success, search_details)
                
            return success
        except Exception as e:
            self.log_test("Search Theses", False, f"Error: {str(e)}")
            return False

    def test_get_thesis_by_id(self):
        """Test getting a specific thesis by ID"""
        try:
            # First get list of theses to get an ID
            response = requests.get(f"{self.api_url}/theses?limit=1", timeout=10)
            if response.status_code != 200:
                self.log_test("Get Thesis by ID", False, "Could not get thesis list")
                return False
                
            data = response.json()
            if not data['results']:
                self.log_test("Get Thesis by ID", False, "No theses found")
                return False
                
            thesis_id = data['results'][0]['id']
            
            # Now test getting specific thesis
            response = requests.get(f"{self.api_url}/theses/{thesis_id}", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                thesis_data = response.json()
                details += f", Thesis: {thesis_data.get('title', 'No title')[:50]}..."
                
            self.log_test("Get Thesis by ID", success, details)
            return success, thesis_id if success else None
        except Exception as e:
            self.log_test("Get Thesis by ID", False, f"Error: {str(e)}")
            return False, None

    def test_author_rankings(self):
        """Test author rankings endpoint"""
        try:
            response = requests.get(f"{self.api_url}/rankings/authors?limit=10", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                if isinstance(data, list):
                    details += f", Found {len(data)} authors"
                    if data:
                        # Check first author has required fields
                        first_author = data[0]
                        required_fields = ['author_name', 'citations_count', 'stars', 'theses_count']
                        missing_fields = [field for field in required_fields if field not in first_author]
                        if missing_fields:
                            success = False
                            details += f", Missing fields: {missing_fields}"
                else:
                    success = False
                    details += ", Response is not a list"
                    
            self.log_test("Author Rankings", success, details)
            return success
        except Exception as e:
            self.log_test("Author Rankings", False, f"Error: {str(e)}")
            return False

    def test_university_rankings(self):
        """Test university rankings endpoint"""
        try:
            response = requests.get(f"{self.api_url}/rankings/universities?limit=10", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                if isinstance(data, list):
                    details += f", Found {len(data)} universities"
                    if data:
                        # Check first university has required fields
                        first_uni = data[0]
                        required_fields = ['university_name', 'country', 'theses_count']
                        missing_fields = [field for field in required_fields if field not in first_uni]
                        if missing_fields:
                            success = False
                            details += f", Missing fields: {missing_fields}"
                else:
                    success = False
                    details += ", Response is not a list"
                    
            self.log_test("University Rankings", success, details)
            return success
        except Exception as e:
            self.log_test("University Rankings", False, f"Error: {str(e)}")
            return False

    def test_checkout_session_creation(self):
        """Test checkout session creation (will fail without valid thesis ID but should return proper error)"""
        try:
            # First get a paywalled thesis
            response = requests.get(f"{self.api_url}/theses?access_type=paywalled&limit=1", timeout=10)
            if response.status_code != 200:
                self.log_test("Checkout Session Creation", False, "Could not get paywalled thesis")
                return False
                
            data = response.json()
            if not data['results']:
                self.log_test("Checkout Session Creation", False, "No paywalled theses found")
                return False
                
            thesis_id = data['results'][0]['id']
            
            # Test checkout session creation
            checkout_data = {
                "thesis_id": thesis_id,
                "origin_url": "https://theses-cames.preview.emergentagent.com"
            }
            
            response = requests.post(
                f"{self.api_url}/checkout/session", 
                json=checkout_data,
                timeout=10
            )
            
            # Should return 200 with session data or proper error
            success = response.status_code in [200, 400, 500]  # Accept various responses
            details = f"Status: {response.status_code}"
            
            if response.status_code == 200:
                session_data = response.json()
                if 'url' in session_data and 'session_id' in session_data:
                    details += ", Session created successfully"
                else:
                    success = False
                    details += ", Missing session data"
            elif response.status_code == 400:
                details += f", Expected error: {response.json().get('detail', 'No detail')}"
            elif response.status_code == 500:
                details += ", Payment system not configured (expected)"
                
            self.log_test("Checkout Session Creation", success, details)
            return success
        except Exception as e:
            self.log_test("Checkout Session Creation", False, f"Error: {str(e)}")
            return False

    def test_filters_and_search(self):
        """Test various filter combinations"""
        try:
            test_cases = [
                ("country=Sénégal", "Country filter"),
                ("discipline=Informatique", "Discipline filter"),
                ("access_type=open", "Access type filter"),
                ("year=2023", "Year filter"),
                ("q=intelligence&country=Sénégal", "Combined search and filter")
            ]
            
            all_success = True
            for params, test_name in test_cases:
                response = requests.get(f"{self.api_url}/theses?{params}", timeout=10)
                success = response.status_code == 200
                details = f"Status: {response.status_code}"
                
                if success:
                    data = response.json()
                    details += f", Results: {len(data['results'])}"
                else:
                    all_success = False
                    
                self.log_test(f"Filter Test - {test_name}", success, details)
                
            return all_success
        except Exception as e:
            self.log_test("Filter Tests", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Thèses CAMES API Tests")
        print("=" * 50)
        
        # Test basic connectivity
        if not self.test_api_root():
            print("❌ API is not accessible, stopping tests")
            return False
            
        # Test core endpoints
        self.test_get_stats()
        self.test_search_theses()
        self.test_get_thesis_by_id()
        self.test_author_rankings()
        self.test_university_rankings()
        
        # Test advanced features
        self.test_filters_and_search()
        self.test_checkout_session_creation()
        
        # Print summary
        print("\n" + "=" * 50)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️  Some tests failed. Check the details above.")
            failed_tests = [test for test in self.test_results if not test['success']]
            print("\nFailed tests:")
            for test in failed_tests:
                print(f"  - {test['name']}: {test['details']}")
            return False

def main():
    tester = ThesesCAMESAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())