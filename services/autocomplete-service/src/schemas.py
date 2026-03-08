"""
Pydantic request/response schemas for the autocomplete service API.
"""

from typing import Optional, List

from pydantic import BaseModel, Field


# ── Response schemas ──

class AutocompleteItem(BaseModel):
    """Single autocomplete suggestion."""
    text: str
    category: str
    metadata: Optional[dict] = None


class AutocompleteResponse(BaseModel):
    """GET /autocomplete — autocomplete suggestions."""
    query: str
    suggestions: List[AutocompleteItem]
    count: int


class PlaceAutocompleteItem(BaseModel):
    """Single place autocomplete suggestion."""
    place_id: str
    name: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class PlaceAutocompleteResponse(BaseModel):
    """GET /autocomplete/places — place suggestions."""
    query: str
    places: List[PlaceAutocompleteItem]
    count: int


class AddressAutocompleteItem(BaseModel):
    """Single address autocomplete suggestion."""
    address: str
    city: str
    state: str
    zip_code: Optional[str] = None


class AddressAutocompleteResponse(BaseModel):
    """GET /autocomplete/addresses — address suggestions."""
    query: str
    addresses: List[AddressAutocompleteItem]
    count: int
