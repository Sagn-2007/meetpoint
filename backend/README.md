# MeetPoint — Core Geospatial Engine & Interactive Frontend

MeetPoint is an end-to-end geospatial application that computes optimal meeting locations for $N$ participants based on actual traversable road and pedestrian networks.

---

## 1. Overview & System Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   MeetPoint Frontend (React + Vite)                    │
│   Map-centric UI (React Leaflet) • Participant Drag & Click Pinning   │
│   1-Median / 1-Center / Compare Controls • Top-K Alternatives Cards    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / JSON
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend Engine (Port 8000)                   │
│                                                                        │
│  [Coordinate Snapping]  ◄── 3D KDTree Spherical Index                  │
│  [Network Acquisition]  ◄── OSMnx 2.x Pedestrian ('walk') & Drive      │
│  [Disk & Memory Cache]  ◄── GraphML Persistent Cache                   │
│  [Shortest Paths]       ◄── NetworkX Single-Source Dijkstra           │
│  [Route Reconstruction] ◄── Node Sequence, Distances & Segments        │
│  [Optimization Solvers] ◄── Network 1-Median & 1-Center + Minimax      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
                        OpenStreetMap / Overpass API
```

---

## 2. Directory Structure

```text
meetpoint/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI entrypoint, middleware & health
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py              # API v1 routes (/meeting/optimize, /network/info)
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py              # Settings (default network_type: walk)
│   │   │   ├── exceptions.py          # Domain-specific exceptions
│   │   │   └── logging.py             # Structured logging
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── geometry.py            # Coordinate and BoundingBox models
│   │   │   └── schemas.py             # Request, Response, Route & Comparison schemas
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── network_service.py     # OSMnx graph downloading, sanitization & caching
│   │   │   ├── snapping_service.py    # 3D KDTree spatial snapping
│   │   │   └── optimization_service.py# Multi-objective optimization & route builder
│   │   └── algorithms/
│   │       ├── __init__.py
│   │       ├── dijkstra.py            # Single-source Dijkstra & route reconstruction
│   │       ├── one_median.py          # Network 1-Median optimizer with Top-K ranking
│   │       └── one_center.py          # Network 1-Center optimizer with Top-K ranking
│   ├── cache/
│   │   └── osm_graphs/                # GraphML cached road & pedestrian networks
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                # Synthetic graphs and TestClient fixtures
│   │   ├── test_validation.py         # Coordinate and bounding box tests
│   │   ├── test_graph.py              # Graph construction, snapping & caching
│   │   ├── test_dijkstra.py           # Dijkstra correctness & one-way restrictions
│   │   ├── test_one_median.py         # 1-Median optimality, disconnected & tie-breaking
│   │   ├── test_one_center.py         # 1-Center ground truth, tie-breaking & top-K
│   │   ├── test_route_reconstruction.py # Reconstructed coordinates, segments & parallel edges
│   │   ├── test_comparison_and_api_phase2.py # Comparative objective & Top-K API tests
│   │   └── test_api.py                # End-to-end API integration tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   └── Navbar.tsx         # App branding, health status & demo triggers
│   │   │   ├── map/
│   │   │   │   └── MapView.tsx        # React Leaflet map, draggable markers, routes & beacon
│   │   │   ├── participants/
│   │   │   │   └── ParticipantList.tsx# Participant manager, click-to-add & manual inputs
│   │   │   ├── optimization/
│   │   │   │   └── OptimizationControls.tsx # Objective, network mode, Top-K & calculate
│   │   │   └── results/
│   │   │       ├── ResultsPanel.tsx   # Results container with route & candidate tabs
│   │   │       ├── OptimalMeetingCard.tsx # Highlighted meeting point & aggregate metrics
│   │   │       ├── ComparisonView.tsx # Side-by-side comparison for compare mode
│   │   │       ├── CandidateList.tsx  # Ranked alternative candidates list
│   │   │       └── RouteList.tsx      # Individual journeys, segments & visibility toggles
│   │   ├── services/
│   │   │   └── api.ts                 # Type-safe API client with structured error handling
│   │   ├── types/
│   │   │   └── index.ts               # TypeScript domain interfaces
│   │   ├── utils/
│   │   │   ├── colors.ts              # Vibrant marker palettes & Leaflet DivIcons
│   │   │   └── formatters.ts          # Distance, duration and coordinate formatting
│   │   ├── App.tsx                    # Main app state coordinator
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
├── pytest.ini
└── README.md
```

---

## 3. Technology Stack

### Backend
- **Python 3.12+**
- **FastAPI**: Asynchronous REST framework
- **OSMnx**: OpenStreetMap road & pedestrian topology modeling
- **NetworkX**: Directed graph data structures, Dijkstra shortest-path calculations
- **GeoPandas & Shapely**: Geospatial geometry processing
- **SciPy & NumPy**: Spatial $k$-d tree indexing and vectorized haversine computations
- **Pydantic v2**: Strict schema validation and serialization
- **Pytest**: Deterministic test suite with synthetic networks (51 passing tests)

### Frontend
- **React 18**
- **Vite 5**
- **TypeScript**
- **Tailwind CSS**
- **Leaflet & React Leaflet**
- **Lucide React Icons**

---

## 4. Setup and Installation

### Backend Setup

```bash
# 1. Create Python 3.12 virtual environment
uv venv .venv --python 3.12
source .venv/bin/activate

# 2. Install backend dependencies
uv pip install -r backend/requirements.txt
```

### Frontend Setup

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install
```

---

## 5. Running the Application

### Option A: Run Backend & Frontend in separate terminals

**Terminal 1 (Backend):**
```bash
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Base: `http://localhost:8000`
- Swagger UI Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```
- Web Application: `http://localhost:5173`

---

## 6. Running the Backend Tests

All 51 automated unit and integration tests execute with zero external network dependencies using synthetic graphs:

```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests -v
```

Test coverage includes:
- Coordinate bounds and bounding box geometries.
- Dijkstra shortest-path distances and actual route coordinate sequences.
- Strict enforcement of one-way road restrictions and directed semantics.
- Network 1-Median and Network 1-Center mathematical ground truth.
- Divergence scenarios where 1-Median and 1-Center select different locations.
- Two-level tie-breaking for both objectives.
- Parallel multiedge resolution (selecting minimum distance edge).
- Top-K candidate ranking and geographical deduplication.
- API validation and backward compatibility.

---

## 7. Interactive Frontend Features

1. **Map-Centric Interface**: Map occupies 65–70% of the viewport with responsive stacking on mobile.
2. **Interactive Participant Pinning**: Click anywhere on the map to place pins, or enter coordinates manually.
3. **Draggable Markers**: Drag any participant marker to adjust their location; underlying state and routes recalculate live.
4. **Optimal Meeting Beacon**: Glowing beacon marker identifying the recommended meeting spot with detailed popups.
5. **Alternative Candidate Markers**: Badged markers (`#2`, `#3`, ...) displaying alternative options; click to highlight and inspect.
6. **Reconstructed Routes**: Visualized shortest-path polylines matching each participant's assigned color.
7. **Route Visibility Toggles**: Show or hide individual participant route paths with the eye icon.
8. **Three Optimization Strategies**:
   - **1-Median**: Minimizes total travel distance for the entire group.
   - **1-Center**: Minimizes the maximum individual travel distance (minimax equity).
   - **Compare**: Side-by-side comparison with trade-off analysis and explanation.
9. **Preset Demo**: Click **"Sample Demo"** in the top navigation bar to instantly populate sample coordinates in Central London and explore immediate calculations.

---

## 8. OpenStreetMap Pedestrian Data Considerations

When using pedestrian networks (`network_type="walk"`):
1. **Sidewalk Mapping Completeness**: Pedestrian ways depend on OpenStreetMap sidewalk tagging.
2. **Access Restrictions**: Gated communities or private courtyards may restrict thoroughfare.
3. **Overpass Server Rate Limits**: In production, caching or a dedicated local Overpass instance is recommended.
