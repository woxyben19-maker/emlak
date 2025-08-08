from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import asyncio
import json
import aiofiles
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from emergentintegrations.llm.chat import LlmChat, UserMessage
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfutils
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import io


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Gemini API configuration
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class ScrapingRequest(BaseModel):
    url: str
    month: int
    year: int = 2025

class PropertyListing(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_name: str = ""
    contact_number: str = ""
    room_count: str = ""
    net_area: str = ""
    is_in_complex: str = ""
    complex_name: str = ""
    heating_type: str = ""
    parking_type: str = ""
    credit_suitable: str = ""
    price: str = ""
    listing_date: str = ""
    raw_html: str = ""
    processed_date: datetime = Field(default_factory=datetime.utcnow)

class ScrapingResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    month: int
    year: int
    total_listings: int
    processed_listings: int
    status: str
    listings: List[PropertyListing] = []
    created_date: datetime = Field(default_factory=datetime.utcnow)

# Utility functions
async def init_gemini_chat():
    """Initialize Gemini chat with proper configuration"""
    chat = LlmChat(
        api_key=GEMINI_API_KEY,
        session_id=str(uuid.uuid4()),
        system_message="""Sen Türk emlak verilerini analiz eden bir uzmansın. Verilen HTML içeriğinden emlak ilan bilgilerini çıkartmalısın.

        Çıkartman gereken bilgiler:
        1. owner_name: İlan sahibinin adı
        2. contact_number: İletişim telefon numarası
        3. room_count: Oda sayısı (örn: 3+1, 2+1)
        4. net_area: Net metrekare
        5. is_in_complex: Site içinde mi? (evet/hayır)
        6. complex_name: Site adı (varsa)
        7. heating_type: Isıtma türü
        8. parking_type: Otopark türü (açık/kapalı/yok)
        9. credit_suitable: Krediye uygun mu? (evet/hayır/belirtilmemiş)
        10. price: Fiyat

        Yanıtını JSON formatında ver. Bilgi bulunamazsa boş string ("") kullan."""
    ).with_model("gemini", "gemini-2.0-flash")
    return chat

async def scrape_sahibinden_listings(url: str, target_month: int, target_year: int = 2025):
    """Scrape Sahibinden.com listings using Playwright"""
    listings = []
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Set user agent to avoid detection
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            await page.goto(url, wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            # Get all listing links
            listing_links = await page.query_selector_all('a[href*="/ilan/"]')
            listing_urls = []
            
            for link in listing_links:
                href = await link.get_attribute('href')
                if href and '/ilan/' in href and not href.startswith('http'):
                    full_url = f"https://www.sahibinden.com{href}"
                    listing_urls.append(full_url)
            
            # Process each listing
            for listing_url in listing_urls[:10]:  # Limit to first 10 for testing
                try:
                    await page.goto(listing_url, wait_until='networkidle')
                    await page.wait_for_timeout(2000)
                    
                    # Check if listing is from target month
                    listing_date = await page.query_selector('.classifiedInfoValue')
                    if listing_date:
                        date_text = await listing_date.inner_text()
                        # Simple month check - you might want to improve this
                        if str(target_month) in date_text or f"{target_year}" in date_text:
                            # Get full page content
                            content = await page.content()
                            
                            # Create a basic PropertyListing object
                            listing = PropertyListing(raw_html=content[:5000])  # Limit HTML size
                            listings.append(listing)
                    
                except Exception as e:
                    logging.error(f"Error processing listing {listing_url}: {e}")
                    continue
            
            await browser.close()
            
    except Exception as e:
        logging.error(f"Error in scraping: {e}")
        raise HTTPException(status_code=500, detail=f"Scraping error: {str(e)}")
    
    return listings

async def process_listing_with_ai(listing: PropertyListing) -> PropertyListing:
    """Process a single listing using Gemini AI"""
    try:
        # Initialize Gemini chat
        chat = await init_gemini_chat()
        
        # Parse HTML content with BeautifulSoup
        soup = BeautifulSoup(listing.raw_html, 'html.parser')
        
        # Extract text content
        text_content = soup.get_text()[:3000]  # Limit text length
        
        # Create prompt for AI
        prompt = f"""
        Lütfen bu emlak ilanı HTML içeriğinden bilgileri çıkart:
        
        {text_content}
        
        JSON formatında şu bilgileri ver:
        {{
            "owner_name": "",
            "contact_number": "",
            "room_count": "",
            "net_area": "",
            "is_in_complex": "",
            "complex_name": "",
            "heating_type": "",
            "parking_type": "",
            "credit_suitable": "",
            "price": ""
        }}
        """
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        # Parse AI response
        try:
            # Extract JSON from response
            response_text = response.strip()
            if '```json' in response_text:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_text = response_text[json_start:json_end]
            else:
                json_text = response_text
                
            ai_data = json.loads(json_text)
            
            # Update listing with AI extracted data
            listing.owner_name = ai_data.get('owner_name', '')
            listing.contact_number = ai_data.get('contact_number', '')
            listing.room_count = ai_data.get('room_count', '')
            listing.net_area = ai_data.get('net_area', '')
            listing.is_in_complex = ai_data.get('is_in_complex', '')
            listing.complex_name = ai_data.get('complex_name', '')
            listing.heating_type = ai_data.get('heating_type', '')
            listing.parking_type = ai_data.get('parking_type', '')
            listing.credit_suitable = ai_data.get('credit_suitable', '')
            listing.price = ai_data.get('price', '')
            
        except json.JSONDecodeError as e:
            logging.error(f"JSON parse error: {e}")
            logging.error(f"AI Response: {response}")
    
    except Exception as e:
        logging.error(f"Error processing listing with AI: {e}")
    
    return listing

# Routes
@api_router.get("/")
async def root():
    return {"message": "Sahibinden Emlak Veri Çıkarıcı API"}

@api_router.post("/scrape", response_model=ScrapingResult)
async def start_scraping(request: ScrapingRequest, background_tasks: BackgroundTasks):
    """Start scraping process for given URL and month"""
    
    # Create result object
    result = ScrapingResult(
        url=request.url,
        month=request.month,
        year=request.year,
        total_listings=0,
        processed_listings=0,
        status="processing"
    )
    
    # Save initial result to database
    await db.scraping_results.insert_one(result.dict())
    
    # Start background scraping task
    background_tasks.add_task(perform_scraping, result.id, request)
    
    return result

async def perform_scraping(result_id: str, request: ScrapingRequest):
    """Background task to perform the actual scraping"""
    try:
        # Update status
        await db.scraping_results.update_one(
            {"id": result_id},
            {"$set": {"status": "scraping"}}
        )
        
        # Scrape listings
        listings = await scrape_sahibinden_listings(request.url, request.month, request.year)
        
        # Update total count
        await db.scraping_results.update_one(
            {"id": result_id},
            {"$set": {"total_listings": len(listings), "status": "processing_ai"}}
        )
        
        # Process each listing with AI
        processed_listings = []
        for listing in listings:
            processed_listing = await process_listing_with_ai(listing)
            processed_listings.append(processed_listing)
            
            # Update progress
            await db.scraping_results.update_one(
                {"id": result_id},
                {"$set": {"processed_listings": len(processed_listings)}}
            )
        
        # Save final results
        await db.scraping_results.update_one(
            {"id": result_id},
            {"$set": {
                "listings": [listing.dict() for listing in processed_listings],
                "status": "completed"
            }}
        )
        
    except Exception as e:
        logging.error(f"Scraping error: {e}")
        await db.scraping_results.update_one(
            {"id": result_id},
            {"$set": {"status": "error", "error_message": str(e)}}
        )

@api_router.get("/results/{result_id}", response_model=ScrapingResult)
async def get_scraping_result(result_id: str):
    """Get scraping results by ID"""
    result = await db.scraping_results.find_one({"id": result_id})
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return ScrapingResult(**result)

@api_router.get("/results", response_model=List[ScrapingResult])
async def get_all_results():
    """Get all scraping results"""
    results = await db.scraping_results.find().sort("created_date", -1).to_list(50)
    return [ScrapingResult(**result) for result in results]

@api_router.get("/export/excel/{result_id}")
async def export_excel(result_id: str):
    """Export results to Excel"""
    result = await db.scraping_results.find_one({"id": result_id})
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    # Convert to DataFrame
    data = []
    for listing in result.get('listings', []):
        data.append({
            'İlan Sahibi': listing.get('owner_name', ''),
            'Telefon': listing.get('contact_number', ''),
            'Oda Sayısı': listing.get('room_count', ''),
            'Net m²': listing.get('net_area', ''),
            'Site İçi': listing.get('is_in_complex', ''),
            'Site Adı': listing.get('complex_name', ''),
            'Isıtma': listing.get('heating_type', ''),
            'Otopark': listing.get('parking_type', ''),
            'Krediye Uygun': listing.get('credit_suitable', ''),
            'Fiyat': listing.get('price', '')
        })
    
    df = pd.DataFrame(data)
    
    # Save to file
    filename = f"emlak_listesi_{result_id}.xlsx"
    filepath = f"/tmp/{filename}"
    df.to_excel(filepath, index=False)
    
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@api_router.get("/export/pdf/{result_id}")
async def export_pdf(result_id: str):
    """Export results to PDF"""
    result = await db.scraping_results.find_one({"id": result_id})
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    # Create PDF
    filename = f"emlak_listesi_{result_id}.pdf"
    filepath = f"/tmp/{filename}"
    
    doc = SimpleDocTemplate(filepath, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Build content
    content = []
    
    # Title
    title = Paragraph("Emlak İlan Listesi", styles['Title'])
    content.append(title)
    content.append(Spacer(1, 12))
    
    # Create table data
    headers = ['İlan Sahibi', 'Telefon', 'Oda Sayısı', 'Net m²', 'Site İçi', 
              'Site Adı', 'Isıtma', 'Otopark', 'Krediye Uygun', 'Fiyat']
    
    table_data = [headers]
    
    for listing in result.get('listings', []):
        row = [
            listing.get('owner_name', '')[:15],
            listing.get('contact_number', '')[:15],
            listing.get('room_count', ''),
            listing.get('net_area', ''),
            listing.get('is_in_complex', ''),
            listing.get('complex_name', '')[:10],
            listing.get('heating_type', '')[:10],
            listing.get('parking_type', ''),
            listing.get('credit_suitable', ''),
            listing.get('price', '')[:15]
        ]
        table_data.append(row)
    
    # Create table
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTSIZE', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    content.append(table)
    doc.build(content)
    
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type='application/pdf'
    )

# Test endpoint for Gemini
@api_router.post("/test-gemini")
async def test_gemini():
    """Test Gemini API connection"""
    try:
        chat = await init_gemini_chat()
        test_message = UserMessage(text="Merhaba, test mesajı. Sadece 'Test başarılı!' yaz.")
        response = await chat.send_message(test_message)
        return {"status": "success", "response": response}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()