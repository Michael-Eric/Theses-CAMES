"""
Greenstone CAMES Connector for importing African academic theses
Connects to Greenstone CAMES repository at https://greenstone.lecames.org
"""

import asyncio
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import httpx
from bs4 import BeautifulSoup
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

class GreenstoneConnector:
    """Connector for importing theses from Greenstone CAMES repository"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.base_url = "https://greenstone.lecames.org/cgi-bin/library"
        self.session = httpx.AsyncClient(timeout=30.0)
        
        # CAMES countries mapping
        self.cames_countries = {
            "senegal": "Sénégal",
            "burkina": "Burkina Faso", 
            "mali": "Mali",
            "cote": "Côte d'Ivoire",
            "niger": "Niger",
            "benin": "Bénin",
            "togo": "Togo",
            "guinee": "Guinée",
            "guinea": "Guinée",
            "madagascar": "Madagascar",
            "cameroun": "Cameroun",
            "cameroon": "Cameroun",
            "tchad": "Tchad",
            "chad": "Tchad",
            "centrafrique": "République Centrafricaine",
            "congo": "Congo",
            "gabon": "Gabon",
            "mauritanie": "Mauritanie"
        }
    
    async def get_collection_list(self) -> List[str]:
        """Get list of available collections"""
        try:
            response = await self.session.get(self.base_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            collections = []
            
            # Look for collection links
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'c=' in href and 'collection' in href.lower():
                    # Extract collection name
                    collection_match = re.search(r'c=([^&]+)', href)
                    if collection_match:
                        collections.append(collection_match.group(1))
            
            return list(set(collections))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error getting collection list: {e}")
            return []
    
    async def search_collection(self, collection: str, query: str = "", page: int = 0) -> Dict[str, Any]:
        """Search in a specific Greenstone collection"""
        try:
            params = {
                "a": "q",
                "c": collection,
                "ct": "1",
                "qt": "1",
                "qf": "",
                "fqf": "",
                "fqs": "",
                "q": query or "thesis OR thèse OR dissertation",
                "n": "20",  # Results per page
                "r": str(page * 20),  # Start result
                "hs": "1"
            }
            
            response = await self.session.get(self.base_url, params=params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            return self.parse_search_results(soup, collection)
            
        except Exception as e:
            logger.error(f"Error searching collection {collection}: {e}")
            return {"results": [], "total": 0}
    
    def parse_search_results(self, soup: BeautifulSoup, collection: str) -> Dict[str, Any]:
        """Parse Greenstone search results"""
        results = []
        
        try:
            # Look for result items (Greenstone uses various HTML structures)
            result_elements = soup.find_all(['div', 'td'], class_=re.compile(r'result|item|doc'))
            
            if not result_elements:
                # Alternative: look for links that might be thesis records
                result_elements = soup.find_all('a', href=re.compile(r'd='))
            
            for element in result_elements[:20]:  # Limit to 20 results per page
                thesis_data = self.extract_thesis_from_element(element, collection)
                if thesis_data:
                    results.append(thesis_data)
            
            # Try to get total count
            total_text = soup.get_text()
            total_match = re.search(r'(\d+)\s*(?:results?|résultats?)', total_text, re.IGNORECASE)
            total = int(total_match.group(1)) if total_match else len(results)
            
            return {"results": results, "total": total}
            
        except Exception as e:
            logger.error(f"Error parsing search results: {e}")
            return {"results": [], "total": 0}
    
    def extract_thesis_from_element(self, element: BeautifulSoup, collection: str) -> Optional[Dict[str, Any]]:
        """Extract thesis data from a search result element"""
        try:
            # Try to find document link
            doc_link = element.find('a', href=re.compile(r'd='))
            if not doc_link:
                return None
            
            href = doc_link['href']
            doc_id_match = re.search(r'd=([^&]+)', href)
            if not doc_id_match:
                return None
            
            doc_id = doc_id_match.group(1)
            
            # Extract title
            title = ""
            title_elem = element.find(['h3', 'h4', 'strong', 'b']) or doc_link
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            if not title or len(title) < 10:
                return None
            
            # Extract other information from the element text
            element_text = element.get_text()
            
            # Try to extract author
            author = ""
            author_patterns = [
                r'[Aa]uteur\s*:?\s*([^\n\r]+)',
                r'[Bb]y\s+([^\n\r]+)',
                r'([A-Z][a-z]+\s+[A-Z][a-z]+)',  # Simple name pattern
            ]
            
            for pattern in author_patterns:
                author_match = re.search(pattern, element_text)
                if author_match:
                    author = author_match.group(1).strip()
                    break
            
            # Extract year
            year_match = re.search(r'(19|20)\d{2}', element_text)
            defense_year = year_match.group(0) if year_match else "2023"
            
            # Extract discipline/subject
            discipline = "Sciences"
            discipline_keywords = {
                "informatique": "Informatique",
                "computer": "Informatique", 
                "médecine": "Médecine",
                "medicine": "Médecine",
                "économie": "Économie",
                "economy": "Économie",
                "géographie": "Géographie",
                "geography": "Géographie",
                "linguistique": "Linguistique",
                "linguistics": "Linguistique",
                "droit": "Droit",
                "law": "Droit",
                "sociologie": "Sociologie",
                "sociology": "Sociologie"
            }
            
            element_text_lower = element_text.lower()
            for keyword, disc in discipline_keywords.items():
                if keyword in element_text_lower:
                    discipline = disc
                    break
            
            # Determine country from collection name or text
            country = "Afrique"  # Default
            for country_key, country_name in self.cames_countries.items():
                if country_key in collection.lower() or country_key in element_text_lower:
                    country = country_name
                    break
            
            # Extract keywords from title and text
            keywords = []
            # Simple keyword extraction from title
            title_words = re.findall(r'\b[a-zA-ZÀ-ÿ]{4,}\b', title.lower())
            keywords = [word.capitalize() for word in title_words[:5]]
            
            # Create full URL
            full_url = f"{self.base_url}?{href.lstrip('?')}" if not href.startswith('http') else href
            
            return {
                "title": title,
                "abstract": f"Thèse de doctorat en {discipline} soutenue en {defense_year}.",
                "keywords": keywords,
                "language": "fr",
                "discipline": discipline,
                "sub_discipline": None,
                "country": country,
                "university": f"Université {country}",
                "doctoral_school": "École Doctorale CAMES",
                "author_name": author or "Auteur inconnu",
                "author_orcid": None,
                "supervisor_names": [],
                "defense_date": defense_year,
                "pages": None,
                "degree": "Doctorat",
                "doi": None,
                "handle": None,
                "hal_id": None,
                "url_open_access": full_url,
                "file_open_access": None,
                "access_type": "open",
                "purchase_url": None,
                "license": "Libre accès",
                "source_repo": "Greenstone",
                "source_url": full_url,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "views_count": 0,
                "downloads_count": 0,
                "site_citations_count": 0,
                "external_citations_count": None,
                "thumbnail": None,
                "_greenstone_doc_id": doc_id,
                "_greenstone_collection": collection
            }
            
        except Exception as e:
            logger.error(f"Error extracting thesis from element: {e}")
            return None
    
    async def get_detailed_record(self, doc_id: str, collection: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific document"""
        try:
            params = {
                "a": "d",
                "c": collection,
                "d": doc_id,
                "dt": "hierarchy"
            }
            
            response = await self.session.get(self.base_url, params=params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract detailed metadata
            metadata = {}
            
            # Look for metadata tables or definition lists
            for table in soup.find_all('table'):
                for row in table.find_all('tr'):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        metadata[key] = value
            
            # Look for definition lists
            for dl in soup.find_all('dl'):
                terms = dl.find_all('dt')
                definitions = dl.find_all('dd')
                for term, definition in zip(terms, definitions):
                    key = term.get_text(strip=True).lower()
                    value = definition.get_text(strip=True)
                    metadata[key] = value
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error getting detailed record {doc_id}: {e}")
            return None
    
    async def check_duplicate(self, thesis_data: Dict[str, Any]) -> bool:
        """Check if thesis already exists in database"""
        try:
            # Check by Greenstone document ID
            if thesis_data.get("_greenstone_doc_id"):
                existing = await self.db.theses.find_one({
                    "_greenstone_doc_id": thesis_data["_greenstone_doc_id"]
                })
                if existing:
                    return True
            
            # Check by source URL
            if thesis_data.get("source_url"):
                existing = await self.db.theses.find_one({
                    "source_url": thesis_data["source_url"]
                })
                if existing:
                    return True
            
            # Check by title + author similarity
            title = thesis_data.get("title", "").lower().strip()
            author = thesis_data.get("author_name", "").lower().strip()
            year = thesis_data.get("defense_date", "")
            
            if title and len(title) > 10:
                existing_theses = await self.db.theses.find({
                    "defense_date": year,
                    "source_repo": {"$in": ["Greenstone", "HAL", "Other"]}
                }).to_list(length=50)
                
                for existing in existing_theses:
                    existing_title = existing.get("title", "").lower().strip()
                    
                    # Simple similarity check
                    title_words = set(title.split())
                    existing_words = set(existing_title.split())
                    
                    if title_words and existing_words:
                        overlap = len(title_words.intersection(existing_words))
                        similarity = overlap / max(len(title_words), len(existing_words))
                        if similarity > 0.6:  # 60% similarity threshold
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking duplicate: {e}")
            return False
    
    async def import_thesis(self, thesis_data: Dict[str, Any]) -> bool:
        """Import a single thesis to database"""
        try:
            # Check for duplicates
            if await self.check_duplicate(thesis_data):
                logger.info(f"Duplicate thesis skipped: {thesis_data.get('title', 'Unknown')}")
                return False
            
            # Add unique ID
            thesis_data["id"] = str(uuid.uuid4())
            
            # Insert to database
            await self.db.theses.insert_one(thesis_data)
            logger.info(f"Imported thesis: {thesis_data.get('title', 'Unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing thesis: {e}")
            return False
    
    async def import_from_greenstone(self, max_records: int = 50) -> Dict[str, int]:
        """Import theses from Greenstone CAMES"""
        stats = {
            "processed": 0,
            "imported": 0,
            "duplicates": 0,
            "errors": 0
        }
        
        try:
            logger.info("Starting Greenstone CAMES import...")
            
            # Get available collections
            collections = await self.get_collection_list()
            if not collections:
                # Use default search if no collections found
                collections = [""]
            
            logger.info(f"Found {len(collections)} collections: {collections}")
            
            for collection in collections:
                if stats["processed"] >= max_records:
                    break
                
                page = 0
                while stats["processed"] < max_records:
                    # Search in collection
                    search_results = await self.search_collection(collection, page=page)
                    
                    if not search_results["results"]:
                        break
                    
                    # Process results
                    for thesis_data in search_results["results"]:
                        if stats["processed"] >= max_records:
                            break
                        
                        stats["processed"] += 1
                        
                        # Import thesis
                        if await self.import_thesis(thesis_data):
                            stats["imported"] += 1
                        else:
                            stats["duplicates"] += 1
                    
                    page += 1
                    
                    # Limit pages per collection
                    if page >= 3:  # Max 3 pages per collection
                        break
                    
                    # Be respectful to the server
                    await asyncio.sleep(2)
            
            logger.info(f"Greenstone import completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error during Greenstone import: {e}")
            stats["errors"] += 1
            return stats
    
    async def close(self):
        """Close HTTP session"""
        await self.session.aclose()