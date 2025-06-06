from pydantic import BaseModel, field_validator, Field
from typing import Optional
import re

class ProductCreateCommand(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0)
    description: str = Field(..., min_length=10, max_length=2000)
    stock_quantity: int = Field(..., ge=0)
    image_url: Optional[str] = None
    
    @field_validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Product name cannot be empty")
        if len(v) > 100:
            raise ValueError("Product name too long (max 100 chars)")
        return v.strip()
    
    @field_validator('price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError("Price must be positive")
        if v > 1000000:
            raise ValueError("Price too high")
        return round(v, 2)
    
    @field_validator('description')
    def validate_description(cls, v):
        if len(v) < 10:
            raise ValueError("Description too short (min 10 chars)")
        if len(v) > 2000:
            raise ValueError("Description too long (max 2000 chars)")
        return v
    
    @field_validator('stock_quantity')
    def validate_stock(cls, v):
        if v < 0:
            raise ValueError("Stock cannot be negative")
        if v > 100000:
            raise ValueError("Stock quantity too high")
        return v
class OrderCreateCommand(BaseModel):
    product_id: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    total_price: float = Field(..., gt=0)

    @field_validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError("Quantity must be positive")
        if v > 1000:
            raise ValueError("Quantity too high")
        return v

    @field_validator('total_price')
    def validate_total_price(cls, v):
        if v <= 0:
            raise ValueError("Total price must be positive")
        if v > 1000000:
            raise ValueError("Total price too high")
        return round(v, 2)