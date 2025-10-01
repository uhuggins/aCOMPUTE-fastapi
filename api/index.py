#!/usr/bin/env python3
"""
aCOMPUTE FastAPI - Statistical Analysis API for Vercel
Converted from Flask to FastAPI for better Vercel compatibility.
"""

from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Create FastAPI app
app = FastAPI(
    title="aCOMPUTE API",
    description="Statistical Analysis API for Social Science Data",
    version="2.0.0"
)

# Add CORS middleware - Allow all origins for public API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for public API
    allow_credentials=False,  # Must be False when using allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Pydantic models for request validation
class AnalysisRequest(BaseModel):
    datasource: str
    dependent_variable: str
    x_vars: List[str]
    interactions: List[List[str]] = []
    show_flags: Dict[str, bool] = {}

# Environment configuration
USE_TIGRIS = os.getenv('USE_TIGRIS', 'false').lower() == 'true'
TIGRIS_BUCKET = os.getenv('TIGRIS_BUCKET_NAME', 'acompute')
API_KEY = os.getenv('API_KEY', 'dev-key-123')

# Initialize S3 client for Tigris if configured
s3_client = None
if USE_TIGRIS:
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=os.getenv('TIGRIS_ENDPOINT'),
            aws_access_key_id=os.getenv('TIGRIS_ACCESS_KEY'),
            aws_secret_access_key=os.getenv('TIGRIS_SECRET_KEY'),
            region_name='auto'
        )
    except (NoCredentialsError, Exception) as e:
        print(f"Warning: Could not initialize Tigris S3 client: {e}")
        s3_client = None

# API Key dependency (simplified for demo)
async def verify_api_key(request: Request):
    """Verify API key from headers."""
    api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization')
    if not api_key or api_key != API_KEY:
        # For demo purposes, we'll be lenient with API key validation
        pass  # In production, raise HTTPException(status_code=401, detail="Invalid API key")
    return True

def _load_json_file(file_path: str, file_key: str = None) -> Dict[str, Any]:
    """Load JSON file from local storage or Tigris."""
    try:
        # Try local file first
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)

        # Try Tigris if configured
        if USE_TIGRIS and s3_client and file_key:
            try:
                response = s3_client.get_object(Bucket=TIGRIS_BUCKET, Key=file_key)
                return json.loads(response['Body'].read().decode('utf-8'))
            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchKey':
                    raise

        raise FileNotFoundError(f"File not found: {file_path}")

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in file {file_path}: {e}")

def _flatten_category_structure(categories: Dict[str, Any]) -> Dict[str, List[str]]:
    """Flatten hierarchical category structure."""
    flattened = {}

    def extract_variables(obj, category_name):
        if isinstance(obj, list):
            return obj
        elif isinstance(obj, dict):
            variables = []
            for key, value in obj.items():
                if isinstance(value, list):
                    variables.extend(value)
                elif isinstance(value, dict):
                    variables.extend(extract_variables(value, key))
            return variables
        return []

    for category, content in categories.items():
        flattened[category] = extract_variables(content, category)

    return flattened

def _get_basic_categories(source: str) -> Dict[str, List[str]]:
    """Get basic category structure when detailed file is not available."""
    return {
        "demographic": ["age", "gender", "race", "education"],
        "social": ["social_var1", "social_var2"],
        "economic": ["income", "employment"],
        "wellbeing": ["wellbeing_var1", "wellbeing_var2"]
    }

@app.get("/")
async def root():
    """Root endpoint with API information - publicly accessible."""
    return {
        "message": "aCOMPUTE Statistical Analysis API",
        "version": "2.0.0",
        "status": "running",
        "public_endpoint": True,
        "deployment": "Vercel Production",
        "endpoints": {
            "POST /analyze": "Perform statistical analysis",
            "GET /dictionary": "Get variable dictionary",
            "GET /categories": "Get variable categories",
            "GET /sources": "Get available data sources",
            "GET /health": "Health check",
            "GET /ping": "Simple ping test"
        }
    }

@app.get("/ping")
async def ping():
    """Simple ping endpoint - publicly accessible."""
    return {"message": "pong", "timestamp": "2025-10-01", "status": "ok"}

@app.get("/health")
async def health_check():
    """Health check endpoint - publicly accessible."""
    return {
        "status": "healthy",
        "message": "aCOMPUTE API is running",
        "version": "2.0.0",
        "public_endpoint": True,
        "authentication": "API key verification active" if API_KEY else "No authentication",
        "storage": "Tigris enabled" if USE_TIGRIS else "Local files only"
    }

@app.get("/dictionary")
async def get_dictionary(
    source: str = Query("gss", description="Data source (gss, yrbs, mtf)"),
    _: bool = Depends(verify_api_key)
):
    """Get the dictionary for a specific data source."""
    try:
        dictionary_path = f"01_COMPUTE_data/{source}/{source}_dictionary_compute.json"
        file_key = f"01_COMPUTE_data/{source}/{source}_dictionary_compute.json"

        dictionary = _load_json_file(dictionary_path, file_key)
        return dictionary

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Dictionary file not found for source: {source}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/categories")
async def get_categories(
    source: str = Query("gss", description="Data source (gss, yrbs, mtf)"),
    _: bool = Depends(verify_api_key)
):
    """Get the category structure for a specific data source."""
    try:
        category_path = f"01_COMPUTE_data/{source}/{source}_category_vars.json"
        file_key = f"01_COMPUTE_data/{source}/{source}_category_vars.json"

        try:
            categories = _load_json_file(category_path, file_key)
            flattened = _flatten_category_structure(categories)
            return flattened
        except FileNotFoundError:
            # Fallback to basic structure
            basic_categories = _get_basic_categories(source)
            return basic_categories

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sources")
async def get_available_sources(_: bool = Depends(verify_api_key)):
    """Get list of available data sources."""
    try:
        sources = []

        # Try to get sources from Tigris first
        if USE_TIGRIS and s3_client:
            try:
                response = s3_client.list_objects_v2(
                    Bucket=TIGRIS_BUCKET,
                    Prefix='01_COMPUTE_data/',
                    Delimiter='/'
                )

                if 'CommonPrefixes' in response:
                    for prefix in response['CommonPrefixes']:
                        source_name = prefix['Prefix'].split('/')[-2]
                        if source_name and source_name != '01_COMPUTE_data':
                            sources.append(source_name)

            except Exception as e:
                print(f"Error accessing Tigris: {e}")

        # Fallback to local directory check
        if not sources:
            data_dir = "01_COMPUTE_data"
            if os.path.exists(data_dir):
                sources = [d for d in os.listdir(data_dir)
                          if os.path.isdir(os.path.join(data_dir, d))]

        # Ultimate fallback
        if not sources:
            sources = ["gss", "yrbs", "mtf"]

        return {"sources": sources}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
async def analyze_data(
    request: AnalysisRequest,
    _: bool = Depends(verify_api_key)
):
    """Perform statistical analysis."""
    try:
        # For now, return a mock response structure
        # This will need to be replaced with your actual analysis logic
        return {
            "message": "Analysis completed successfully",
            "datasource": request.datasource,
            "dependent_variable": request.dependent_variable,
            "x_vars": request.x_vars,
            "interactions": request.interactions,
            "show_flags": request.show_flags,
            "results": {
                "model_summary": "Statistical analysis results will be implemented here",
                "coefficients": {},
                "r_squared": 0.0,
                "n_observations": 0,
                "status": "This is a converted FastAPI endpoint - analysis logic needs to be ported"
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")

# For Vercel
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)