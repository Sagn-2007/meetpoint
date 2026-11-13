"""Geometric models and validation primitives."""

from __future__ import annotations
from typing import Sequence
from pydantic import BaseModel, Field, model_validator


class Coordinate(BaseModel):
    """Geographic coordinate representing a point on Earth (WGS84)."""

    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Latitude in decimal degrees [-90.0, 90.0]",
        examples=[22.5726],
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Longitude in decimal degrees [-180.0, 180.0]",
        examples=[88.3639],
    )


class BoundingBox(BaseModel):
    """Geographic bounding box for road network extraction."""

    min_lat: float = Field(..., ge=-90.0, le=90.0, description="Southernmost latitude boundary")
    min_lon: float = Field(..., ge=-180.0, le=180.0, description="Westernmost longitude boundary")
    max_lat: float = Field(..., ge=-90.0, le=90.0, description="Northernmost latitude boundary")
    max_lon: float = Field(..., ge=-180.0, le=180.0, description="Easternmost longitude boundary")

    @model_validator(mode="after")
    def validate_bounds(self) -> BoundingBox:
        """Validate that min bounds are strictly less than max bounds."""
        if self.min_lat >= self.max_lat:
            raise ValueError(
                f"min_lat ({self.min_lat}) must be strictly less than max_lat ({self.max_lat})"
            )
        if self.min_lon >= self.max_lon:
            raise ValueError(
                f"min_lon ({self.min_lon}) must be strictly less than max_lon ({self.max_lon})"
            )
        return self

    def to_osmnx_bbox(self) -> tuple[float, float, float, float]:
        """Return OSMnx 2.x bbox format: (left, bottom, right, top) = (min_lon, min_lat, max_lon, max_lat)."""
        return (self.min_lon, self.min_lat, self.max_lon, self.max_lat)

    @classmethod
    def from_coordinates(
        cls,
        coordinates: Sequence[Coordinate],
        padding_ratio: float = 0.20,
        min_padding_deg: float = 0.015,
    ) -> BoundingBox:
        """Construct a padded bounding box enclosing all provided coordinates."""
        if not coordinates:
            raise ValueError("Cannot compute bounding box from an empty list of coordinates")

        min_lat = min(c.latitude for c in coordinates)
        max_lat = max(c.latitude for c in coordinates)
        min_lon = min(c.longitude for c in coordinates)
        max_lon = max(c.longitude for c in coordinates)

        lat_span = max_lat - min_lat
        lon_span = max_lon - min_lon

        lat_pad = max(lat_span * padding_ratio, min_padding_deg)
        lon_pad = max(lon_span * padding_ratio, min_padding_deg)

        return cls(
            min_lat=max(-90.0, min_lat - lat_pad),
            min_lon=max(-180.0, min_lon - lon_pad),
            max_lat=min(90.0, max_lat + lat_pad),
            max_lon=min(180.0, max_lon + lon_pad),
        )
