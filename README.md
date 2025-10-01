# aCOMPUTE FastAPI

FastAPI version of the aCOMPUTE statistical analysis API, optimized for Vercel deployment.

## API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `GET /dictionary?source=gss` - Get variable dictionary
- `GET /categories?source=gss` - Get variable categories
- `GET /sources` - Get available data sources
- `POST /analyze` - Perform statistical analysis

## Environment Variables

- `API_KEY` - API authentication key
- `USE_TIGRIS` - Enable Tigris cloud storage (true/false)
- `TIGRIS_BUCKET_NAME` - Tigris bucket name
- `TIGRIS_ENDPOINT` - Tigris endpoint URL
- `TIGRIS_ACCESS_KEY` - Tigris access key
- `TIGRIS_SECRET_KEY` - Tigris secret key

## Deployment

This API is designed for Vercel deployment with the `@vercel/python` runtime.

```bash
vercel deploy
```

## Usage

```python
import requests

# Get variable dictionary
response = requests.get("https://your-api.vercel.app/dictionary?source=gss")
dictionary = response.json()

# Perform analysis
analysis_data = {
    "datasource": "gss",
    "dependent_variable": "happy",
    "x_vars": ["age", "educ"],
    "interactions": [],
    "show_flags": {"year": True}
}

response = requests.post("https://your-api.vercel.app/analyze", json=analysis_data)
results = response.json()
```