"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal

# Example schemas (you can keep these for reference or remove later)
class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Video generation app schemas
class VideoRequest(BaseModel):
    """
    Stores user requests to generate a video
    Collection name: "videorequest"
    """
    prompt: str = Field(..., description="Creative prompt describing the scene")
    model: Literal["sora2", "veo3"] = Field(..., description="Target generator model")
    duration_seconds: int = Field(5, ge=1, le=60, description="Desired duration in seconds")
    aspect_ratio: str = Field("16:9", description="Aspect ratio, e.g., 16:9, 9:16, 1:1")
    status: Literal["queued", "processing", "completed", "failed"] = Field(
        "queued", description="Generation status"
    )
    generated_url: Optional[str] = Field(None, description="URL to the generated video if available")
    thumbnail_url: Optional[str] = Field(None, description="Preview image URL")
    error: Optional[str] = Field(None, description="Error message if failed")
