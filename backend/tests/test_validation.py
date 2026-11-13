"""Tests for coordinate and bounding box validation."""

import pytest
from pydantic import ValidationError

from app.models.geometry import BoundingBox, Coordinate
from app.models.schemas import OptimizeMeetingRequest, Participant


def test_valid_coordinate():
    """Valid latitude and longitude should succeed."""
    coord = Coordinate(latitude=22.5726, longitude=88.3639)
    assert coord.latitude == 22.5726
    assert coord.longitude == 88.3639


def test_invalid_latitude():
    """Latitude outside [-90, 90] must raise ValidationError."""
    with pytest.raises(ValidationError) as exc:
        Coordinate(latitude=90.0001, longitude=88.0)
    assert "latitude" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        Coordinate(latitude=-90.1, longitude=88.0)
    assert "latitude" in str(exc.value)


def test_invalid_longitude():
    """Longitude outside [-180, 180] must raise ValidationError."""
    with pytest.raises(ValidationError) as exc:
        Coordinate(latitude=22.0, longitude=180.05)
    assert "longitude" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        Coordinate(latitude=22.0, longitude=-180.1)
    assert "longitude" in str(exc.value)


def test_valid_bounding_box():
    """Valid bounding box should succeed and export correct OSMnx 2.x bbox."""
    bbox = BoundingBox(min_lat=22.0, min_lon=88.0, max_lat=23.0, max_lon=89.0)
    assert bbox.min_lat == 22.0
    assert bbox.max_lat == 23.0
    assert bbox.to_osmnx_bbox() == (88.0, 22.0, 89.0, 23.0)


def test_invalid_bounding_box_lat_order():
    """min_lat >= max_lat must raise ValidationError."""
    with pytest.raises(ValidationError) as exc:
        BoundingBox(min_lat=23.0, min_lon=88.0, max_lat=22.0, max_lon=89.0)
    assert "min_lat" in str(exc.value)


def test_invalid_bounding_box_lon_order():
    """min_lon >= max_lon must raise ValidationError."""
    with pytest.raises(ValidationError) as exc:
        BoundingBox(min_lat=22.0, min_lon=89.0, max_lat=23.0, max_lon=88.0)
    assert "min_lon" in str(exc.value)


def test_bounding_box_from_coordinates():
    """BoundingBox.from_coordinates must enclose all points with configured padding."""
    coords = [
        Coordinate(latitude=22.50, longitude=88.30),
        Coordinate(latitude=22.60, longitude=88.40),
    ]
    bbox = BoundingBox.from_coordinates(coords, padding_ratio=0.10, min_padding_deg=0.01)

    assert bbox.min_lat < 22.50
    assert bbox.max_lat > 22.60
    assert bbox.min_lon < 88.30
    assert bbox.max_lon > 88.40


def test_bounding_box_from_empty_coordinates():
    """Empty list of coordinates should raise ValueError."""
    with pytest.raises(ValueError):
        BoundingBox.from_coordinates([])


def test_optimize_request_fewer_than_two_participants():
    """Request with fewer than 2 participants must fail validation."""
    with pytest.raises(ValidationError) as exc:
        OptimizeMeetingRequest(
            participants=[
                Participant(latitude=22.57, longitude=88.36, label="Solo"),
            ]
        )
    assert "participants" in str(exc.value)


def test_optimize_request_valid():
    """Request with at least 2 participants must succeed."""
    req = OptimizeMeetingRequest(
        participants=[
            Participant(id="p1", latitude=22.57, longitude=88.36),
            Participant(id="p2", latitude=22.58, longitude=88.37),
        ]
    )
    assert len(req.participants) == 2
    assert req.network_type == "walk"
