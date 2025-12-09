#!/usr/bin/env python3
"""
Modern Technology Examples
This file demonstrates how to use modern Python libraries
to replace older patterns in your healthcare automation software.
"""

# ============================================
# EXAMPLE 1: Modern Logging with Loguru
# ============================================
print("=" * 60)
print("EXAMPLE 1: Modern Logging with Loguru")
print("=" * 60)

# OLD WAY (standard logging - verbose setup)
"""
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info("Processing started")
"""

# NEW WAY (Loguru - one line!)
try:
    from loguru import logger
    
    # Remove default handler and add custom ones
    logger.remove()
    logger.add("app_{time}.log", rotation="500 MB", retention="10 days")
    logger.add(lambda msg: print(msg, end=""), colorize=True)
    
    logger.info("✅ Processing started")
    logger.debug("Debug information")
    logger.warning("⚠️ Warning message")
    logger.error("❌ Error occurred")
    logger.success("✅ Task completed successfully")
    
    # Automatic exception tracking
    try:
        1 / 0
    except Exception:
        logger.exception("Exception occurred")  # Logs full traceback automatically!
        
except ImportError:
    print("⚠️ Loguru not installed. Install with: pip install loguru")


# ============================================
# EXAMPLE 2: Modern Configuration with Pydantic
# ============================================
print("\n" + "=" * 60)
print("EXAMPLE 2: Modern Configuration with Pydantic")
print("=" * 60)

try:
    from pydantic import BaseSettings, Field, validator
    from typing import Optional
    from datetime import date
    
    class BotSettings(BaseSettings):
        """Bot configuration with automatic validation"""
        username: str = Field(..., description="Database username")
        password: str = Field(..., description="Database password")
        api_url: str = Field(default="https://api.example.com", description="API endpoint")
        timeout: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")
        max_retries: int = Field(default=3, ge=0, le=10)
        enable_logging: bool = Field(default=True)
        log_level: str = Field(default="INFO")
        
        @validator('log_level')
        def validate_log_level(cls, v):
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if v.upper() not in valid_levels:
                raise ValueError(f'log_level must be one of {valid_levels}')
            return v.upper()
        
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
    
    # Usage - automatically loads from .env file or environment variables
    # settings = BotSettings()  # Would load from .env
    # print(f"API URL: {settings.api_url}")
    # print(f"Timeout: {settings.timeout}")
    
    print("✅ Pydantic settings class defined")
    print("   - Automatic validation")
    print("   - Type hints")
    print("   - Environment variable support")
    print("   - IDE autocomplete")
    
except ImportError:
    print("⚠️ Pydantic not installed. Install with: pip install pydantic python-dotenv")


# ============================================
# EXAMPLE 3: Modern Data Validation with Pydantic
# ============================================
print("\n" + "=" * 60)
print("EXAMPLE 3: Modern Data Validation with Pydantic")
print("=" * 60)

try:
    from pydantic import BaseModel, validator, Field
    from datetime import date
    from typing import Optional
    
    class PatientRecord(BaseModel):
        """Patient record with automatic validation"""
        patient_id: str = Field(..., min_length=1, max_length=50, description="Patient identifier")
        date_of_service: date = Field(..., description="Date of service")
        procedure_code: str = Field(..., description="CPT procedure code")
        modifier: Optional[str] = Field(None, max_length=2, description="Procedure modifier")
        amount: float = Field(..., ge=0, description="Billing amount")
        counselor_name: Optional[str] = Field(None, max_length=100)
        
        @validator('procedure_code')
        def validate_procedure_code(cls, v):
            """Validate CPT code format (5 digits)"""
            if not v.isdigit() or len(v) != 5:
                raise ValueError('Procedure code must be exactly 5 digits')
            return v
        
        @validator('patient_id')
        def validate_patient_id(cls, v):
            """Normalize patient ID to uppercase"""
            return v.upper().strip()
        
        class Config:
            json_schema_extra = {
                "example": {
                    "patient_id": "ABDEL000",
                    "date_of_service": "2024-01-15",
                    "procedure_code": "90834",
                    "modifier": "95",
                    "amount": 180.00,
                    "counselor_name": "LK"
                }
            }
    
    # Valid record
    try:
        record = PatientRecord(
            patient_id="abdel000",  # Will be normalized to uppercase
            date_of_service="2024-01-15",
            procedure_code="90834",
            modifier="95",
            amount=180.00,
            counselor_name="LK"
        )
        print(f"✅ Valid record created: {record.patient_id}")
        print(f"   Date: {record.date_of_service}")
        print(f"   Procedure: {record.procedure_code}")
    except Exception as e:
        print(f"❌ Validation error: {e}")
    
    # Invalid record (will raise ValidationError)
    try:
        invalid_record = PatientRecord(
            patient_id="",
            date_of_service="2024-01-15",
            procedure_code="9083",  # Too short!
            amount=-100.00  # Negative amount!
        )
    except Exception as e:
        print(f"✅ Validation caught errors: {type(e).__name__}")
        # Pydantic provides detailed error messages
        
except ImportError:
    print("⚠️ Pydantic not installed. Install with: pip install pydantic")


# ============================================
# EXAMPLE 4: Modern HTTP Client with HTTPX
# ============================================
print("\n" + "=" * 60)
print("EXAMPLE 4: Modern HTTP Client with HTTPX")
print("=" * 60)

try:
    import httpx
    import asyncio
    
    # Synchronous usage (same API as requests)
    print("Synchronous HTTP request:")
    try:
        response = httpx.get("https://httpbin.org/json", timeout=10.0)
        if response.status_code == 200:
            print(f"✅ Request successful: {response.status_code}")
            print(f"   Response time: {response.elapsed.total_seconds():.2f}s")
    except Exception as e:
        print(f"⚠️ Request failed: {e}")
    
    # Asynchronous usage (much faster for multiple requests)
    async def fetch_multiple():
        """Fetch multiple URLs concurrently"""
        urls = [
            "https://httpbin.org/delay/1",
            "https://httpbin.org/delay/1",
            "https://httpbin.org/delay/1",
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # All requests happen concurrently!
            responses = await asyncio.gather(*[
                client.get(url) for url in urls
            ])
            return responses
    
    print("\nAsynchronous HTTP requests (concurrent):")
    try:
        import time
        start = time.time()
        # responses = asyncio.run(fetch_multiple())
        # elapsed = time.time() - start
        # print(f"✅ Fetched {len(responses)} URLs in {elapsed:.2f}s (would be ~3s sequentially)")
        print("   (Commented out to avoid network calls in example)")
    except Exception as e:
        print(f"⚠️ Async request failed: {e}")
        
except ImportError:
    print("⚠️ HTTPX not installed. Install with: pip install httpx")


# ============================================
# EXAMPLE 5: Modern Data Processing with Polars
# ============================================
print("\n" + "=" * 60)
print("EXAMPLE 5: Modern Data Processing with Polars")
print("=" * 60)

try:
    import polars as pl
    from datetime import date
    
    # Create sample patient data
    data = {
        "patient_id": ["ABDEL000", "ABRAN000", "ABDEL000", "ABRAN000", "ABDEL000"],
        "date_of_service": [date(2024, 1, 15), date(2024, 1, 16), date(2024, 1, 17), 
                           date(2024, 1, 18), date(2024, 1, 19)],
        "procedure_code": ["90834", "90837", "90834", "90837", "90834"],
        "amount": [180.00, 250.00, 180.00, 250.00, 180.00],
        "counselor": ["LK", "MM", "LK", "MM", "LK"]
    }
    
    # Create DataFrame (much faster than pandas for large datasets)
    df = pl.DataFrame(data)
    print("✅ Created Polars DataFrame")
    print(f"   Shape: {df.shape}")
    
    # Filter and aggregate (lazy evaluation - only computes what's needed)
    result = (
        df
        .filter(pl.col("amount") > 200)  # Filter
        .group_by("patient_id")  # Group
        .agg([
            pl.sum("amount").alias("total_amount"),
            pl.count().alias("visit_count")
        ])  # Aggregate
    )
    
    print("\n✅ Filtered and aggregated data:")
    print(result)
    
    # Lazy evaluation example (doesn't execute until .collect())
    lazy_result = (
        pl.DataFrame(data)
        .lazy()  # Start lazy evaluation
        .filter(pl.col("amount") > 200)
        .group_by("patient_id")
        .agg([pl.sum("amount")])
        # .collect()  # Only executes when you call collect()
    )
    print("\n✅ Lazy evaluation allows query optimization")
    
except ImportError:
    print("⚠️ Polars not installed. Install with: pip install polars")


# ============================================
# EXAMPLE 6: Modern Database with SQLAlchemy
# ============================================
print("\n" + "=" * 60)
print("EXAMPLE 6: Modern Database with SQLAlchemy")
print("=" * 60)

try:
    from sqlalchemy import create_engine, Column, String, Float, Date, Integer
    from sqlalchemy.orm import sessionmaker, declarative_base
    from datetime import date
    
    Base = declarative_base()
    
    class PatientRecord(Base):
        """SQLAlchemy ORM model - type-safe database operations"""
        __tablename__ = 'patient_records'
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        patient_id = Column(String(50), nullable=False, index=True)
        date_of_service = Column(Date, nullable=False)
        procedure_code = Column(String(5), nullable=False)
        amount = Column(Float, nullable=False)
        counselor = Column(String(50))
        
        def __repr__(self):
            return f"<PatientRecord(patient_id='{self.patient_id}', date='{self.date_of_service}')>"
    
    # Create in-memory database for example
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Add a record (type-safe, no SQL injection possible)
    record = PatientRecord(
        patient_id="ABDEL000",
        date_of_service=date(2024, 1, 15),
        procedure_code="90834",
        amount=180.00,
        counselor="LK"
    )
    session.add(record)
    session.commit()
    
    # Query records (type-safe)
    results = session.query(PatientRecord).filter(
        PatientRecord.patient_id == "ABDEL000"
    ).all()
    
    print(f"✅ Created and queried {len(results)} record(s)")
    print(f"   Patient: {results[0].patient_id}")
    print(f"   Date: {results[0].date_of_service}")
    print(f"   Amount: ${results[0].amount}")
    
    session.close()
    
except ImportError:
    print("⚠️ SQLAlchemy not installed. Install with: pip install sqlalchemy")


# ============================================
# SUMMARY
# ============================================
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print("""
These examples demonstrate modern Python libraries that can:
1. ✅ Simplify your code (Loguru, Pydantic)
2. ✅ Improve performance (Polars, HTTPX async, Playwright)
3. ✅ Add type safety (Pydantic, SQLAlchemy, mypy)
4. ✅ Better error handling (Pydantic validation, Loguru exceptions)
5. ✅ Modern best practices (async/await, ORM, structured logging)

Next Steps:
1. Install the libraries: pip install -r requirements_modern.txt
2. Start with Loguru for logging (easiest win)
3. Add Pydantic for new data models
4. Consider Playwright for new web automation
5. Use Polars for large data processing tasks

See MODERN_TECH_RECOMMENDATIONS.md for detailed migration guide.
""")

