from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import Client, create_client
import os
from dotenv import load_dotenv

# Load local .env variables if running locally
load_dotenv()

# 1. Supabase Configuration (reads securely from environment variables)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI(title="Rahala Albarr API")

# Enable CORS so the frontend can communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Models ---
class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    phone: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserUpdate(BaseModel):
    name: str
    phone: str


class TripCreate(BaseModel):
    user_id: int
    location_id: int
    trip_name: str  # <--- Added trip name here
    date: str
    duration: int
    companions: int


class LocationCreate(BaseModel):
    latitude: float
    longitude: float
    description: str


class EmergencyCreate(BaseModel):
    user_id: int
    latitude: float
    longitude: float
    description: Optional[str] = "Emergency Location"


class ForgotPassword(BaseModel):
    email: str


class ResetPassword(BaseModel):
    email: str
    new_password: str


# --- Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Welcome to Rahala Albarr API is running successfully!"}


@app.post("/register")
def register_user(user: UserRegister):
    """Add a new user to the database"""
    try:
        data = {
            "name": user.name,
            "email": user.email,
            "password": user.password,
            "phone": user.phone,
        }
        response = supabase.table("users").insert(data).execute()
        return {"status": "success", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/login")
def login_user(user: UserLogin):
    """Verify user email and password"""
    try:
        response = (
            supabase.table("users")
            .select("*")
            .eq("email", user.email)
            .eq("password", user.password)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=401, detail="Invalid email or password"
            )

        return {
            "status": "success",
            "message": "Login successful",
            "user": response.data[0],
        }
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- User Profile Update Endpoint ---

@app.put("/users/{user_id}")
def update_user_profile(user_id: int, user: UserUpdate):
    """Update user profile (name and phone)"""
    try:
        data = {
            "name": user.name,
            "phone": user.phone,
        }
        response = supabase.table("users").update(data).eq("user_id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="User not found")
            
        return {
            "status": "success",
            "message": "Profile updated successfully",
            "data": response.data,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Locations Endpoints ---

@app.get("/locations")
def get_locations():
    """Retrieve all locations"""
    try:
        response = supabase.table("location").select("*").execute()
        return {"status": "success", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/locations")
def create_location(location: LocationCreate):
    """Add a new location to the database"""
    try:
        data = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "description": location.description,
        }
        response = supabase.table("location").insert(data).execute()
        return {
            "status": "success",
            "message": "Location added successfully",
            "data": response.data,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Trips Endpoints ---

@app.get("/trips")
def get_trips():
    """Retrieve all trips with associated location data"""
    try:
        response = (
            supabase.table("trip")
            .select("*, location(latitude, longitude, description)")
            .execute()
        )
        return {"status": "success", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/trips")
def create_trip(trip: TripCreate):
    """Create a new exploration trip"""
    try:
        data = {
            "user_id": trip.user_id,
            "location_id": trip.location_id,
            "trip_name": trip.trip_name,  # <--- Included trip name here
            "date": trip.date,
            "duration": trip.duration,
            "companions": trip.companions,
        }
        response = supabase.table("trip").insert(data).execute()
        return {
            "status": "success",
            "message": "Trip created successfully",
            "data": response.data,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/trips/{trip_id}")
def get_trip_by_id(trip_id: int):
    """Retrieve details of a specific trip by its ID"""
    try:
        response = (
            supabase.table("trip")
            .select("*, location(latitude, longitude, description)")
            .eq("trip_id", trip_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Trip not found")
        return {"status": "success", "data": response.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Alerts Endpoints ---

@app.get("/alerts/{trip_id}")
def get_trip_alerts(trip_id: int):
    """Retrieve all alerts associated with a specific trip"""
    try:
        response = (
            supabase.table("alert")
            .select("*")
            .eq("trip_id", trip_id)
            .execute()
        )
        return {"status": "success", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Emergency / SOS Endpoints ---

@app.post("/trips/emergency")
def create_emergency(emergency: EmergencyCreate):
    """Handle SOS emergency request and save location coordinates"""
    try:
        loc_data = {
            "latitude": emergency.latitude,
            "longitude": emergency.longitude,
            "description": emergency.description,
        }
        loc_response = supabase.table("location").insert(loc_data).execute()

        if not loc_response.data:
            raise HTTPException(
                status_code=500, detail="Failed to save emergency location"
            )

        location_id = loc_response.data[0]["location_id"]

        em_data = {
            "user_id": emergency.user_id,
            "location_id": location_id,
            "status": "Pending",
            "date_time": datetime.now().isoformat(),
        }
        em_response = supabase.table("emergency").insert(em_data).execute()

        return {
            "status": "success",
            "message": "Emergency alert sent successfully, tracking in progress",
            "data": em_response.data,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Password Management Endpoints ---

@app.post("/forgot-password")
def forgot_password(body: ForgotPassword):
    try:
        response = supabase.auth.reset_password_for_email(
            body.email,
            options={"redirect_to": "https://your-frontend-app.com/update-password"}
        )
        return {
            "status": "success",
            "message": "Password reset instructions sent to email successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/reset-password")
def reset_password(body: ResetPassword):
    try:
        response = (
            supabase.table("users")
            .update({"password": body.new_password})
            .eq("email", body.email)
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="Email not found")

        return {
            "status": "success",
            "message": "Password updated successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
