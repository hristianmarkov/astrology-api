from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator
from datetime import datetime, timedelta
import swisseph as swe
import os
from typing import Optional
from timezonefinder import TimezoneFinder
import pytz

app = FastAPI(
    title="Astrology API",
    description="API for calculating astrological positions using Swiss Ephemeris data files",
    version="1.0.9"
)

# Set ephemeris path to the absolute path where the ephe files are located
swe.set_ephe_path(r"C:\Users\Hrist\Documents\Astrology\ephe")

# Initialize timezone finder
tf = TimezoneFinder()

# List of planet names and their Swiss Ephemeris constants
PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
    "Chiron": swe.CHIRON,
    "TrueNode": swe.TRUE_NODE,
    "MeanNode": swe.MEAN_NODE,
    "Lilith": swe.MEAN_APOG  # Black Moon Lilith (mean)
}

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

ASPECTS = [
    (0, "conjunction", 8),
    (60, "sextile", 6),
    (90, "square", 6),
    (120, "trine", 6),
    (180, "opposition", 8)
]

# Modern rulerships
MODERN_RULERSHIPS = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Pluto",
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Uranus",
    "Pisces": "Neptune"
}

def format_deg_min(degrees: float) -> str:
    deg = int(degrees) % 30
    minutes = int(round((degrees - int(degrees)) * 60))
    return f"{deg}°{minutes:02d}’"

def zodiac_sign(degrees: float) -> str:
    return ZODIAC_SIGNS[int(degrees // 30) % 12]

def calc_aspects(bodies: dict) -> list:
    aspects = []
    keys = list(bodies.keys())
    for i in range(len(keys)):
        for j in range(i+1, len(keys)):
            name1, name2 = keys[i], keys[j]
            lon1, lon2 = bodies[name1]["longitude"], bodies[name2]["longitude"]
            diff = abs(lon1 - lon2) % 360
            if diff > 180:
                diff = 360 - diff
            for asp_angle, asp_name, orb in ASPECTS:
                if abs(diff - asp_angle) <= orb:
                    # Calculate if aspect is applying or separating
                    applying = (lon2 - lon1) % 360 < 180
                    # Calculate the exact orb
                    exact_orb = abs(diff - asp_angle)
                    aspects.append({
                        "planet1": name1,
                        "planet2": name2,
                        "aspect": asp_name,
                        "orb": round(exact_orb, 2),
                        "applying": applying
                    })
    return aspects

def is_retrograde(current_lon, prev_lon):
    # Handles 360° wrap
    diff = (current_lon - prev_lon) % 360
    return diff < 0.0 or diff > 180.0

def determine_house_position(longitude: float, houses: dict) -> int:
    """Determine which house a planet is in based on its longitude and house cusps."""
    lon = longitude % 360
    
    for i in range(1, 13):
        start = houses[str(i)]["longitude"] % 360
        end = houses[str(i % 12 + 1)]["longitude"] % 360
        
        if end < start:
            end += 360  # handle wrap-around
        
        lon_adjusted = lon
        if lon < start:
            lon_adjusted += 360
        
        if start <= lon_adjusted <= end:
            return i
    
    return 12  # Fallback, shouldn't happen

def calculate_moon_phase(sun_long: float, moon_long: float) -> dict:
    """Calculate the moon phase based on the angle between Sun and Moon."""
    # Calculate the angle between Sun and Moon
    angle = (moon_long - sun_long) % 360
    
    # Determine the phase
    if angle < 22.5 or angle >= 337.5:
        phase = "New Moon"
        phase_emoji = "🌑"
    elif angle < 67.5:
        phase = "Waxing Crescent"
        phase_emoji = "🌒"
    elif angle < 112.5:
        phase = "First Quarter"
        phase_emoji = "🌓"
    elif angle < 157.5:
        phase = "Waxing Gibbous"
        phase_emoji = "🌔"
    elif angle < 202.5:
        phase = "Full Moon"
        phase_emoji = "🌕"
    elif angle < 247.5:
        phase = "Waning Gibbous"
        phase_emoji = "🌖"
    elif angle < 292.5:
        phase = "Last Quarter"
        phase_emoji = "🌗"
    else:
        phase = "Waning Crescent"
        phase_emoji = "🌘"
    
    # Calculate illumination percentage
    illumination = (1 - abs(angle - 180) / 180) * 100
    
    return {
        "phase": phase,
        "phase_emoji": phase_emoji,
        "illumination": round(illumination, 1),
        "angle": round(angle, 1)
    }

class DateInput(BaseModel):
    date: str = Field(..., example="2024-03-05")
    time: Optional[str] = Field("00:00:00", example="14:30:00")
    latitude: float = Field(..., example=40.7128, description="Latitude in decimal degrees")
    longitude: float = Field(..., example=-74.0060, description="Longitude in decimal degrees")

    @validator('date')
    def validate_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")

    @validator('time')
    def validate_time(cls, v):
        try:
            datetime.strptime(v, "%H:%M:%S")
            return v
        except ValueError:
            raise ValueError("Time must be in HH:MM:SS format")

@app.get("/")
async def root():
    return {"message": "Welcome to the Astrology API (Swiss Ephemeris data files)"}

@app.post("/planets")
async def get_planet_positions(date_input: DateInput):
    try:
        print(f"Processing request for date: {date_input.date}, time: {date_input.time}")
        # Calculate timezone based on location
        timezone_str = tf.timezone_at(lat=date_input.latitude, lng=date_input.longitude)
        if timezone_str is None:
            raise HTTPException(status_code=400, detail="Could not determine timezone for the given coordinates")
        
        # Parse the input date and time
        date_time_str = f"{date_input.date} {date_input.time}"
        local_dt = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")
        
        # Convert local time to UTC
        local_tz = pytz.timezone(timezone_str)
        local_dt = local_tz.localize(local_dt)
        utc_dt = local_dt.astimezone(pytz.UTC)
        
        # Convert to Julian Day
        jd = swe.julday(
            utc_dt.year,
            utc_dt.month,
            utc_dt.day,
            utc_dt.hour + utc_dt.minute/60 + utc_dt.second/3600
        )
        
        # Julian Day for 1 hour before
        prev_dt = utc_dt - timedelta(hours=1)
        jd_prev = swe.julday(
            prev_dt.year,
            prev_dt.month,
            prev_dt.day,
            prev_dt.hour + prev_dt.minute/60 + prev_dt.second/3600
        )
        
        flags = swe.FLG_SWIEPH
        planet_positions = {}
        for name, planet_const in PLANETS.items():
            calc_result = swe.calc_ut(jd, planet_const, flags)
            calc_result_prev = swe.calc_ut(jd_prev, planet_const, flags)
            if not calc_result or len(calc_result) < 2 or not calc_result_prev or len(calc_result_prev) < 2:
                planet_positions[name] = None
                continue
            pos = calc_result[0]
            pos_prev = calc_result_prev[0]
            retrograde = is_retrograde(float(pos[0]), float(pos_prev[0]))
            planet_positions[name] = {
                "longitude": float(pos[0]),
                "longitude_formatted": format_deg_min(float(pos[0])),
                "sign": zodiac_sign(float(pos[0])),
                "latitude": float(pos[1]),
                "distance": float(pos[2]),
                "retrograde": retrograde,
                "speed_longitude": float(pos[3]) if len(pos) > 3 else 0.0,
                "speed_latitude": float(pos[4]) if len(pos) > 4 else 0.0,
                "speed_distance": float(pos[5]) if len(pos) > 5 else 0.0
            }
        
        # Calculate houses using Placidus system
        houses = {}
        try:
            # Calculate houses with additional flags for more accurate results
            flags = swe.FLG_SWIEPH | swe.FLG_SPEED
            cusps, ascmc = swe.houses_ex(jd, date_input.latitude, date_input.longitude, b'P', flags)
            
            # Add Ascendant (House 1)
            asc = ascmc[0]
            asc_sign = zodiac_sign(float(asc))
            houses["1"] = {
                "longitude": float(asc),
                "longitude_formatted": format_deg_min(float(asc)),
                "sign": asc_sign,
                "name": "Ascendant",
                "sign_ruler": MODERN_RULERSHIPS[asc_sign],
                "house_ruler": MODERN_RULERSHIPS[asc_sign]
            }
            
            # Add MC (House 10)
            mc = ascmc[1]
            mc_sign = zodiac_sign(float(mc))
            houses["10"] = {
                "longitude": float(mc),
                "longitude_formatted": format_deg_min(float(mc)),
                "sign": mc_sign,
                "name": "MC",
                "sign_ruler": MODERN_RULERSHIPS[mc_sign],
                "house_ruler": MODERN_RULERSHIPS[mc_sign]
            }
            
            # Calculate IC (House 4) - MC + 180° (mod 360)
            ic = (float(mc) + 180) % 360
            ic_sign = zodiac_sign(ic)
            houses["4"] = {
                "longitude": ic,
                "longitude_formatted": format_deg_min(ic),
                "sign": ic_sign,
                "name": "IC",
                "sign_ruler": MODERN_RULERSHIPS[ic_sign],
                "house_ruler": MODERN_RULERSHIPS[ic_sign]
            }
            
            # Calculate DSC (House 7) - Ascendant + 180° (mod 360)
            dsc = (float(asc) + 180) % 360
            dsc_sign = zodiac_sign(dsc)
            houses["7"] = {
                "longitude": dsc,
                "longitude_formatted": format_deg_min(dsc),
                "sign": dsc_sign,
                "name": "DSC",
                "sign_ruler": MODERN_RULERSHIPS[dsc_sign],
                "house_ruler": MODERN_RULERSHIPS[dsc_sign]
            }
            
            # Add other house cusps
            for i, cusp in enumerate(cusps, start=1):
                if str(i) not in houses:  # Skip if we already added this house
                    cusp_sign = zodiac_sign(float(cusp))
                    houses[str(i)] = {
                        "longitude": float(cusp),
                        "longitude_formatted": format_deg_min(float(cusp)),
                        "sign": cusp_sign,
                        "sign_ruler": MODERN_RULERSHIPS[cusp_sign],
                        "house_ruler": MODERN_RULERSHIPS[cusp_sign]
                    }
            
            # Add house positions to planets first
            for name, data in planet_positions.items():
                if data is not None:
                    house_number = determine_house_position(data["longitude"], houses)
                    data["house"] = house_number
                    data["house_formatted"] = f"House {house_number}"
            
            # Add ruler positions for all houses
            for house_num, house_data in houses.items():
                ruler_planet = house_data["sign_ruler"]
                if ruler_planet in planet_positions:
                    ruler_data = planet_positions[ruler_planet]
                    house_data["ruler_position"] = {
                        "longitude": ruler_data["longitude"],
                        "longitude_formatted": ruler_data["longitude_formatted"],
                        "sign": ruler_data["sign"],
                        "house": ruler_data["house"],
                        "house_formatted": ruler_data["house_formatted"]
                    }
            
        except Exception as e:
            print(f"Error calculating houses: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error calculating houses: {str(e)}")
        
        # Calculate moon phase
        if "Sun" in planet_positions and "Moon" in planet_positions:
            moon_phase = calculate_moon_phase(
                planet_positions["Sun"]["longitude"],
                planet_positions["Moon"]["longitude"]
            )
            planet_positions["Moon"]["phase"] = moon_phase
        
        # Combine all for aspect calculation
        aspect_bodies = {**planet_positions, **{k: v for k, v in houses.items() if "name" in v}}
        aspects = calc_aspects(aspect_bodies)
        
        result = {
            "date": date_input.date,
            "time": date_input.time,
            "timezone": timezone_str,
            "latitude": date_input.latitude,
            "longitude": date_input.longitude,
            "julian_day": float(jd),
            "planets": planet_positions,
            "houses": houses,
            "aspects": aspects
        }
        print(f"Calculated result: {result}")
        return result
    except ValueError as e:
        print(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        swe.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 