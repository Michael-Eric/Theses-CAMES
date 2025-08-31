"""
HAL Connector for importing French academic theses
Connects to HAL (Hyper Articles en Ligne) via OAI-PMH protocol
"""

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import httpx
import xmltodict
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

class HALConnector:
    """Connector for importing theses from HAL repository"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.base_url = "https://hal.science/oai/hal"
        self.session = httpx.AsyncClient(timeout=30.0)
        
        # HAL sets for CAMES countries - these are example sets
        self.cames_sets = [
            "country:senegal",
            "country:burkina-faso", 
            "country:mali",
            "country:cote-divoire",
            "country:niger",
            "country:benin",
            "country:togo",
            "country:guinea",
            "country:madagascar",
            "country:cameroun",
            "country:tchad",
            "country:centrafrique",
            "country:congo",
            "country:gabon",
            "country:mauritanie"
        ]
    
    async def list_records(self, resumption_token: Optional[str] = None, set_spec: Optional[str] = None) -> Dict[str, Any]:
        """List records from HAL OAI-PMH endpoint"""
        params = {
            "verb": "ListRecords",
            "metadataPrefix": "oai_dc"
        }
        
        if resumption_token:
            params["resumptionToken"] = resumption_token
        else:
            if set_spec:
                params["set"] = set_spec
            params["from"] = "2020-01-01"  # Get records from 2020 onwards
        
        try:
            response = await self.session.get(self.base_url, params=params)
            response.raise_for_status()
            
            # Parse XML response
            data = xmltodict.parse(response.text)
            return data
            
        except Exception as e:
            logger.error(f"Error fetching HAL records: {e}")
            return {}
    
    def extract_thesis_data(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract thesis data from HAL record"""
        try:
            header = record.get("header", {})
            metadata = record.get("metadata", {}).get("oai_dc:dc", {})
            
            if not metadata:
                return None
            
            # Check if this is a thesis/dissertation
            doc_type = metadata.get("dc:type", [])
            if isinstance(doc_type, str):
                doc_type = [doc_type]
            
            is_thesis = any("thesis" in t.lower() or "thèse" in t.lower() or "dissertation" in t.lower() 
                          for t in doc_type if isinstance(t, str))
            
            if not is_thesis:
                return None
            
            # Extract basic information
            title = metadata.get("dc:title")
            if isinstance(title, list):
                title = title[0] if title else ""
            elif not isinstance(title, str):
                title = str(title) if title else ""
            
            description = metadata.get("dc:description", "")
            if isinstance(description, list):
                description = description[0] if description else ""
            
            # Extract author
            creator = metadata.get("dc:creator", "")
            if isinstance(creator, list):
                creator = creator[0] if creator else ""
            
            # Extract subject/keywords
            subjects = metadata.get("dc:subject", [])
            if isinstance(subjects, str):
                subjects = [subjects]
            keywords = [s.strip() for s in subjects if isinstance(s, str)]
            
            # Extract language
            language = metadata.get("dc:language", "fr")
            if isinstance(language, list):
                language = language[0] if language else "fr"
            
            # Extract date
            date_str = metadata.get("dc:date", "")
            if isinstance(date_str, list):
                date_str = date_str[0] if date_str else ""
            
            # Extract year from date
            year_match = re.search(r'(\d{4})', str(date_str))
            defense_year = year_match.group(1) if year_match else "2023"
            
            # Extract identifier (HAL ID)
            identifier = header.get("identifier", "")
            hal_id = identifier.replace("oai:hal.science:", "") if identifier else ""
            
            # Extract URL
            url = f"https://hal.science/{hal_id}" if hal_id else ""
            
            # Extract discipline from subjects
            discipline = "Sciences"
            if keywords:
                first_keyword = keywords[0].lower()
                if any(term in first_keyword for term in ["inform", "comput", "data"]):
                    discipline = "Informatique"
                elif any(term in first_keyword for term in ["medic", "health", "santé"]):
                    discipline = "Médecine"
                elif any(term in first_keyword for term in ["econ", "business"]):
                    discipline = "Économie"
                elif any(term in first_keyword for term in ["geo", "climat", "environment"]):
                    discipline = "Géographie"
                elif any(term in first_keyword for term in ["ling", "lang"]):
                    discipline = "Linguistique"
            
            # Determine country from set or keywords
            country = "France"  # Default for HAL
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if "sénégal" in keyword_lower or "senegal" in keyword_lower:
                    country = "Sénégal"
                elif "burkina" in keyword_lower:
                    country = "Burkina Faso"
                elif "mali" in keyword_lower:
                    country = "Mali"
                elif "côte d'ivoire" in keyword_lower or "ivory coast" in keyword_lower:
                    country = "Côte d'Ivoire"
                # Add more country mappings as needed
            
            return {
                "title": title.strip(),
                "abstract": description.strip(),
                "keywords": keywords[:10],  # Limit to 10 keywords
                "language": language[:2].lower(),
                "discipline": discipline,
                "sub_discipline": None,
                "country": country,
                "university": "Université (HAL)",  # Will be refined later
                "doctoral_school": None,
                "author_name": creator.strip(),
                "author_orcid": None,
                "supervisor_names": [],
                "defense_date": defense_year,
                "pages": None,
                "degree": "Doctorat",
                "doi": None,
                "handle": None,
                "hal_id": hal_id,
                "url_open_access": url,
                "file_open_access": None,
                "access_type": "open",
                "purchase_url": None,
                "license": "CC BY",
                "source_repo": "HAL",
                "source_url": url,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "views_count": 0,
                "downloads_count": 0,
                "site_citations_count": 0,
                "external_citations_count": None,
                "thumbnail": None
            }
            
        except Exception as e:
            logger.error(f"Error extracting thesis data: {e}")
            return None
    
    async def check_duplicate(self, thesis_data: Dict[str, Any]) -> bool:
        """Check if thesis already exists in database"""
        try:
            # Check by HAL ID first
            if thesis_data.get("hal_id"):
                existing = await self.db.theses.find_one({"hal_id": thesis_data["hal_id"]})
                if existing:
                    return True
            
            # Check by DOI
            if thesis_data.get("doi"):
                existing = await self.db.theses.find_one({"doi": thesis_data["doi"]})
                if existing:
                    return True
            
            # Check by title + author + year (fuzzy matching)
            title = thesis_data.get("title", "").lower().strip()
            author = thesis_data.get("author_name", "").lower().strip()
            year = thesis_data.get("defense_date", "")
            
            if title and author:
                # Simple fuzzy matching - check if titles are very similar
                existing_theses = await self.db.theses.find({
                    "author_name": {"$regex": re.escape(author), "$options": "i"},
                    "defense_date": year
                }).to_list(length=10)
                
                for existing in existing_theses:
                    existing_title = existing.get("title", "").lower().strip()
                    # Check if titles have significant overlap
                    title_words = set(title.split())
                    existing_words = set(existing_title.split())
                    
                    if title_words and existing_words:
                        overlap = len(title_words.intersection(existing_words))
                        similarity = overlap / max(len(title_words), len(existing_words))
                        if similarity > 0.7:  # 70% similarity threshold
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
    
    async def import_from_hal(self, max_records: int = 100) -> Dict[str, int]:
        """Import theses from HAL"""
        stats = {
            "processed": 0,
            "imported": 0,
            "duplicates": 0,
            "errors": 0
        }
        
        try:
            logger.info("Starting HAL import...")
            
            # Import from multiple sets (or no set for general search)
            resumption_token = None
            
            while stats["processed"] < max_records:
                # Fetch records
                data = await self.list_records(resumption_token=resumption_token)
                
                if not data:
                    break
                
                # Extract records
                oai_pmh = data.get("OAI-PMH", {})
                list_records = oai_pmh.get("ListRecords", {})
                
                records = list_records.get("record", [])
                if isinstance(records, dict):
                    records = [records]
                
                if not records:
                    break
                
                # Process each record
                for record in records:
                    if stats["processed"] >= max_records:
                        break
                    
                    stats["processed"] += 1
                    
                    # Extract thesis data
                    thesis_data = self.extract_thesis_data(record)
                    if not thesis_data:
                        continue
                    
                    # Import thesis
                    if await self.import_thesis(thesis_data):
                        stats["imported"] += 1
                    else:
                        stats["duplicates"] += 1
                
                # Check for resumption token
                resumption_token = list_records.get("resumptionToken")
                if isinstance(resumption_token, dict):
                    resumption_token = resumption_token.get("#text")
                
                if not resumption_token:
                    break
                
                # Small delay to be respectful to HAL servers
                await asyncio.sleep(1)
            
            logger.info(f"HAL import completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error during HAL import: {e}")
            stats["errors"] += 1
            return stats
    
    async def close(self):
        """Close HTTP session"""
        await self.session.aclose()

# Import uuid here
import uuid