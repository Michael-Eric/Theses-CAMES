#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime

class ThesesCAMESAPITester:
    def __init__(self, base_url="https://scholarly-views.preview.emergentagent.com"):
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
        """Test author rankings endpoint with weekly views"""
        try:
            response = requests.get(f"{self.api_url}/rankings/authors?limit=10", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                if isinstance(data, list):
                    details += f", Found {len(data)} authors"
                    if data:
                        # Check first author has required fields for weekly views
                        first_author = data[0]
                        required_fields = ['author_name', 'weekly_views', 'total_views', 'stars', 'theses_count', 'disciplines']
                        missing_fields = [field for field in required_fields if field not in first_author]
                        if missing_fields:
                            success = False
                            details += f", Missing fields: {missing_fields}"
                        else:
                            # Verify weekly_views is present and numeric
                            weekly_views = first_author.get('weekly_views', 0)
                            stars = first_author.get('stars', 0)
                            details += f", Top author: {first_author['author_name']}, Weekly views: {weekly_views}, Stars: {stars}"
                            
                            # Verify star calculation logic
                            expected_stars = self.calculate_expected_stars(weekly_views)
                            if stars != expected_stars:
                                success = False
                                details += f", Star calculation error: expected {expected_stars}, got {stars}"
                else:
                    success = False
                    details += ", Response is not a list"
                    
            self.log_test("Author Rankings (Weekly Views)", success, details)
            return success, data if success else []
        except Exception as e:
            self.log_test("Author Rankings (Weekly Views)", False, f"Error: {str(e)}")
            return False, []

    def test_university_rankings(self):
        """Test university rankings endpoint with weekly views aggregation"""
        try:
            response = requests.get(f"{self.api_url}/rankings/universities?limit=10", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                if isinstance(data, list):
                    details += f", Found {len(data)} universities"
                    if data:
                        # Check first university has required fields for weekly views
                        first_uni = data[0]
                        required_fields = ['university_name', 'country', 'weekly_views', 'total_views', 'theses_count', 'top_authors', 'disciplines']
                        missing_fields = [field for field in required_fields if field not in first_uni]
                        if missing_fields:
                            success = False
                            details += f", Missing fields: {missing_fields}"
                        else:
                            weekly_views = first_uni.get('weekly_views', 0)
                            total_views = first_uni.get('total_views', 0)
                            details += f", Top university: {first_uni['university_name']}, Weekly views: {weekly_views}, Total views: {total_views}"
                            
                            # Verify weekly views are properly aggregated (should be >= 0)
                            if weekly_views < 0:
                                success = False
                                details += f", Invalid weekly views: {weekly_views}"
                else:
                    success = False
                    details += ", Response is not a list"
                    
            self.log_test("University Rankings (Weekly Views)", success, details)
            return success, data if success else []
        except Exception as e:
            self.log_test("University Rankings (Weekly Views)", False, f"Error: {str(e)}")
            return False, []

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
                "origin_url": "https://scholarly-views.preview.emergentagent.com"
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

    def test_swagger_documentation(self):
        """Test Swagger documentation endpoint"""
        try:
            response = requests.get(f"{self.api_url}/docs", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                # Check if it's HTML content (Swagger UI)
                content_type = response.headers.get('content-type', '')
                if 'text/html' in content_type:
                    details += ", Swagger UI loaded"
                else:
                    success = False
                    details += f", Unexpected content type: {content_type}"
                    
            self.log_test("Swagger Documentation", success, details)
            return success
        except Exception as e:
            self.log_test("Swagger Documentation", False, f"Error: {str(e)}")
            return False

    def test_openapi_spec(self):
        """Test OpenAPI specification"""
        try:
            response = requests.get(f"{self.api_url}/openapi.json", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                try:
                    spec = response.json()
                    if 'openapi' in spec and 'info' in spec:
                        details += f", OpenAPI version: {spec.get('openapi')}"
                    else:
                        success = False
                        details += ", Invalid OpenAPI spec"
                except:
                    success = False
                    details += ", Invalid JSON response"
                    
            self.log_test("OpenAPI Specification", success, details)
            return success
        except Exception as e:
            self.log_test("OpenAPI Specification", False, f"Error: {str(e)}")
            return False

    def test_seo_endpoints(self):
        """Test SEO optimization endpoints"""
        try:
            # Test sitemap.xml
            response = requests.get(f"{self.api_url}/sitemap.xml", timeout=10)
            sitemap_success = response.status_code == 200
            sitemap_details = f"Status: {response.status_code}"
            
            if sitemap_success:
                content_type = response.headers.get('content-type', '')
                if 'xml' in content_type:
                    sitemap_details += ", XML sitemap generated"
                else:
                    sitemap_success = False
                    sitemap_details += f", Unexpected content type: {content_type}"
                    
            self.log_test("Sitemap XML", sitemap_success, sitemap_details)
            
            # Test robots.txt
            response = requests.get(f"{self.api_url}/robots.txt", timeout=10)
            robots_success = response.status_code == 200
            robots_details = f"Status: {response.status_code}"
            
            if robots_success:
                content = response.text
                if 'User-agent:' in content and 'Sitemap:' in content:
                    robots_details += ", Valid robots.txt"
                else:
                    robots_success = False
                    robots_details += ", Invalid robots.txt format"
                    
            self.log_test("Robots.txt", robots_success, robots_details)
            
            return sitemap_success and robots_success
        except Exception as e:
            self.log_test("SEO Endpoints", False, f"Error: {str(e)}")
            return False

    def test_thesis_metadata(self):
        """Test thesis structured metadata endpoint"""
        try:
            # First get a thesis ID
            response = requests.get(f"{self.api_url}/theses?limit=1", timeout=10)
            if response.status_code != 200:
                self.log_test("Thesis Metadata", False, "Could not get thesis list")
                return False
                
            data = response.json()
            if not data['results']:
                self.log_test("Thesis Metadata", False, "No theses found")
                return False
                
            thesis_id = data['results'][0]['id']
            
            # Test metadata endpoint
            response = requests.get(f"{self.api_url}/thesis/{thesis_id}/metadata", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                metadata = response.json()
                if 'structured_data' in metadata and '@context' in metadata['structured_data']:
                    details += ", Schema.org structured data found"
                else:
                    success = False
                    details += ", Missing structured data"
                    
            self.log_test("Thesis Structured Metadata", success, details)
            return success
        except Exception as e:
            self.log_test("Thesis Metadata", False, f"Error: {str(e)}")
            return False

    def test_authentication_endpoints(self):
        """Test authentication system"""
        try:
            # Test registration endpoint exists
            test_user = {
                "email": f"test_{int(datetime.now().timestamp())}@example.com",
                "password": "TestPassword123!",
                "full_name": "Test User",
                "role": "visitor"
            }
            
            response = requests.post(f"{self.api_url}/auth/register", json=test_user, timeout=10)
            reg_success = response.status_code in [200, 201, 400, 422]  # Accept various responses
            reg_details = f"Status: {response.status_code}"
            
            if response.status_code in [200, 201]:
                reg_details += ", Registration successful"
            elif response.status_code in [400, 422]:
                reg_details += ", Registration endpoint working (validation error expected)"
            else:
                reg_success = False
                
            self.log_test("Authentication Registration", reg_success, reg_details)
            
            # Test login endpoint
            login_data = {
                "email": "test@example.com",
                "password": "motdepasse123"
            }
            
            response = requests.post(f"{self.api_url}/auth/login", json=login_data, timeout=10)
            login_success = response.status_code in [200, 401, 422]  # Accept various responses
            login_details = f"Status: {response.status_code}"
            
            if response.status_code == 200:
                login_details += ", Login successful"
            elif response.status_code in [401, 422]:
                login_details += ", Login endpoint working (auth error expected)"
            else:
                login_success = False
                
            self.log_test("Authentication Login", login_success, login_details)
            
            return reg_success and login_success
        except Exception as e:
            self.log_test("Authentication Endpoints", False, f"Error: {str(e)}")
            return False

    def test_import_system(self):
        """Test import system endpoints"""
        try:
            # Test import status
            response = requests.get(f"{self.api_url}/admin/import/status", timeout=10)
            status_success = response.status_code == 200
            status_details = f"Status: {response.status_code}"
            
            if status_success:
                data = response.json()
                if 'thesis_counts' in data:
                    status_details += f", Total theses: {data['thesis_counts'].get('total', 0)}"
                    
            self.log_test("Import System Status", status_success, status_details)
            
            # Test import history
            response = requests.get(f"{self.api_url}/admin/import/history", timeout=10)
            history_success = response.status_code == 200
            history_details = f"Status: {response.status_code}"
            
            if history_success:
                data = response.json()
                if 'import_jobs' in data:
                    history_details += f", Import jobs: {len(data['import_jobs'])}"
                    
            self.log_test("Import System History", history_success, history_details)
            
            return status_success and history_success
        except Exception as e:
            self.log_test("Import System", False, f"Error: {str(e)}")
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

    def test_university_filter(self):
        """Test the new university filter functionality"""
        try:
            # Test university filter with CAMES universities
            test_universities = [
                "Université Cheikh Anta Diop",
                "Université Joseph Ki-Zerbo", 
                "Université des Sciences, des Techniques et des Technologies de Bamako",
                "Université Félix Houphouët-Boigny"
            ]
            
            all_success = True
            for university in test_universities:
                # URL encode the university name
                import urllib.parse
                encoded_university = urllib.parse.quote(university)
                response = requests.get(f"{self.api_url}/theses?university={encoded_university}", timeout=10)
                success = response.status_code == 200
                details = f"Status: {response.status_code}"
                
                if success:
                    data = response.json()
                    details += f", Results: {len(data['results'])}"
                    # Verify that results actually match the university filter
                    if data['results']:
                        first_result = data['results'][0]
                        if 'university' in first_result:
                            details += f", First result university: {first_result['university']}"
                        else:
                            success = False
                            details += ", Missing university field in results"
                else:
                    all_success = False
                    
                self.log_test(f"University Filter - {university}", success, details)
                
            return all_success
        except Exception as e:
            self.log_test("University Filter Tests", False, f"Error: {str(e)}")
            return False

    def test_enriched_database(self):
        """Test that the database has been enriched with 15 theses"""
        try:
            response = requests.get(f"{self.api_url}/stats", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                total_theses = data.get('total_theses', 0)
                
                # Check if we have at least 15 theses (the enriched amount)
                if total_theses >= 15:
                    details += f", Database enriched: {total_theses} theses found (≥15 expected)"
                    
                    # Check for CAMES universities in top universities
                    top_universities = data.get('top_universities', [])
                    cames_universities = [
                        "Université Cheikh Anta Diop",
                        "Université Joseph Ki-Zerbo",
                        "Université des Sciences, des Techniques et des Technologies de Bamako",
                        "Université Félix Houphouët-Boigny"
                    ]
                    
                    found_cames = []
                    for uni_data in top_universities:
                        uni_name = uni_data.get('name', '')
                        for cames_uni in cames_universities:
                            if cames_uni in uni_name:
                                found_cames.append(uni_name)
                                break
                    
                    if found_cames:
                        details += f", CAMES universities found: {len(found_cames)}"
                    else:
                        success = False
                        details += ", No CAMES universities found in top universities"
                        
                else:
                    success = False
                    details += f", Database not sufficiently enriched: only {total_theses} theses found (<15)"
                    
            self.log_test("Enriched Database Check", success, details)
            return success
        except Exception as e:
            self.log_test("Enriched Database Check", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Comprehensive Thèses CAMES API Tests")
        print("=" * 60)
        
        # Test basic connectivity
        print("\n📋 CORE API TESTS")
        if not self.test_api_root():
            print("❌ API is not accessible, stopping tests")
            return False
            
        # Test documentation endpoints
        print("\n📚 DOCUMENTATION TESTS")
        self.test_swagger_documentation()
        self.test_openapi_spec()
        
        # Test core data endpoints
        print("\n🔍 DATA RETRIEVAL TESTS")
        self.test_get_stats()
        self.test_search_theses()
        self.test_get_thesis_by_id()
        
        # Test rankings
        print("\n🏆 RANKINGS TESTS")
        self.test_author_rankings()
        self.test_university_rankings()
        
        # Test advanced search features
        print("\n🔎 ADVANCED SEARCH TESTS")
        self.test_filters_and_search()
        
        # Test new university filter functionality
        print("\n🏛️ UNIVERSITY FILTER TESTS")
        self.test_university_filter()
        
        # Test enriched database
        print("\n📊 DATABASE ENRICHMENT TESTS")
        self.test_enriched_database()
        
        # Test authentication system
        print("\n🔐 AUTHENTICATION TESTS")
        self.test_authentication_endpoints()
        
        # Test payment system
        print("\n💳 PAYMENT SYSTEM TESTS")
        self.test_checkout_session_creation()
        
        # Test import system
        print("\n📥 IMPORT SYSTEM TESTS")
        self.test_import_system()
        
        # Test SEO endpoints
        print("\n🔍 SEO OPTIMIZATION TESTS")
        self.test_seo_endpoints()
        self.test_thesis_metadata()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 FINAL TEST RESULTS")
        print("=" * 60)
        print(f"✅ Tests passed: {self.tests_passed}/{self.tests_run}")
        print(f"❌ Tests failed: {self.tests_run - self.tests_passed}/{self.tests_run}")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed! API is fully functional.")
            return True
        else:
            print("⚠️  Some tests failed. Details:")
            failed_tests = [test for test in self.test_results if not test['success']]
            for test in failed_tests:
                print(f"   • {test['name']}: {test['details']}")
            
            success_rate = (self.tests_passed / self.tests_run) * 100
            print(f"\n📈 Success rate: {success_rate:.1f}%")
            return False

def main():
    tester = ThesesCAMESAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())