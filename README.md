# Astrology API

A FastAPI application that calculates astrological positions using Swiss Ephemeris data files.

## Features

- Calculate planet positions
- Calculate house positions using Placidus system
- Calculate aspects between planets
- Automatic timezone detection based on coordinates
- Modern rulerships for signs and houses

## Deployment to Render

1. Create a new account on [Render](https://render.com) if you don't have one
2. Create a new Web Service
3. Connect your GitHub repository
4. Configure the service:
   - Name: astrology-api
   - Environment: Python
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main_ephe:app --host 0.0.0.0 --port $PORT`
5. Deploy!

## API Usage

The API is available at `https://astrology-api.onrender.com` (replace with your Render URL)

### Endpoints

- `POST /planets` - Calculate planet positions and aspects
  - Request body:
    ```json
    {
      "date": "2024-01-01",
      "time": "18:00:00",
      "latitude": 40.7128,
      "longitude": -74.0060
    }
    ```

## Local Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the server:
   ```bash
   uvicorn main_ephe:app --reload
   ```
4. Access the API at `http://localhost:8000`

## API Endpoints

### Get Sun Position
- **Endpoint**: `/sun-position`
- **Method**: POST
- **Request Body**:
```json
{
    "date": "2023-12-25",
    "time": "12:00:00",
    "timezone": 0.0
}
```
- **Response**:
```json
{
    "date": "2023-12-25",
    "time": "12:00:00",
    "timezone": 0.0,
    "julian_day": 2460303.0,
    "sun_position": {
        "longitude": 273.123456,
        "latitude": 0.0,
        "distance": 0.983456,
        "speed_longitude": 1.0,
        "speed_latitude": 0.0,
        "speed_distance": 0.0
    }
}
```

## Documentation

Once the API is running, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc` 