# MeetPoint v0.4.0 — Collaborative Geospatial Meeting Point Engine

MeetPoint is an end-to-end geospatial and real-time collaborative application that calculates optimal meeting locations for groups using actual traversable road and pedestrian networks.

MeetPoint supports real-time multi-user rooms without requiring user accounts or registration. A host creates a session and shares an invitation link, participants join independently and submit their GPS coordinates with explicit consent, and the server computes and broadcasts the mathematically optimal meeting location in real time.

---

## 1. System Architecture

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          MeetPoint Frontend (React 18 + Vite)                          │
│  Landing Page • Create / Join Modals • Collaborative Room (Leaflet Map + Sidebar)     │
│  Role-Aware Controls (Host / Participant) • Stale Result Banner • Solo Demo Sandbox   │
└─────────────────────────────┬────────────────────────────┬─────────────────────────────┘
                              │ REST (Fetch)               │ WebSockets (Bidirectional)
                              ▼                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Backend (Port 8000)                                  │
│                                                                                        │
│  [REST API: /api/v1/sessions] ─────────┐                                               │
│  [WebSocket: /sessions/{id}/ws] ───────┼───► [ConnectionManager] (In-memory pub/sub)   │
│                                        │                                               │
│  [SessionService] ─────────────────────┼───► [OptimizationService]                     │
│    • Host / Participant Token Security │        • 3D KDTree Coordinate Snapping         │
│    • Expiration & Staleness Engine     │        • NetworkX Dijkstra Shortest Paths     │
│    • Explicit Location Sharing Policy  │        • 1-Median & 1-Center Solvers           │
│                                        │        • Reconstructed Route Polylines        │
│                                        │        • OSMnx Walk & Drive Networks          │
│                                        │                                               │
│  [SQLAlchemy 2.x Async Engine] ────────┘                                               │
└───────────────────┬──────────────────────────────────────────────┬─────────────────────┘
                    │ PostgreSQL 15+ (Alembic Migrations)          │ Overpass API
                    ▼                                              ▼
          ┌───────────────────┐                         ┌──────────────────────┐
          │  PostgreSQL DB    │                         │    OpenStreetMap     │
          │ • meeting_sessions│                         │ (Pedestrian & Roads) │
          │ • participants    │                         └──────────────────────┘
          │ • optimizations   │
          └───────────────────┘
```

---

## 2. Collaborative Multi-User Workflow

1. **Host Session Creation**:
   - Host configures title, optional description, network mode (`walk` or `drive`), optimization objective (`median`, `center`, or `compare`), and top-$k$ alternatives.
   - Server generates a unique 8-character invitation code and secret host management token.
   - Host enters room directly.

2. **Participant Joining**:
   - Participants open shareable URL (`#/join/ABC123XY`) or enter the code.
   - Participant enters display name and reviews privacy notice.
   - Server generates a unique participant ID and management token.

3. **Privacy-Conscious Location Submission**:
   - **No background tracking**: GPS coordinates are captured only upon explicit user action ("Share My Current GPS").
   - **Map picking**: Participants can click anywhere on the map to set their location manually.
   - **Withdrawal**: Participants can withdraw their location coordinates at any time.

4. **Real-Time WebSocket Synchronization**:
   - `/api/v1/sessions/{session_id}/ws?token={token}`
   - Automatically synchronizes participant joins, leaves, online presence, location changes, setting updates, optimization calculations, and session closure.

5. **Host-Controlled Optimization**:
   - When $\ge 2$ participants have submitted locations, host triggers calculation.
   - Optimization engine runs asynchronously in a thread pool to preserve real-time responsiveness.
   - Optimal meeting point, reconstructed routes, and ranked candidates are broadcast to all room members simultaneously.

6. **Automatic Staleness Detection**:
   - If any participant modifies or withdraws their location after calculation, the room is immediately flagged as stale (`result_is_stale: true`).
   - A warning banner prompts the host to recalculate.

---

## 3. Technology Stack

### Backend
- **Python 3.12+**
- **FastAPI**: Asynchronous web framework & WebSockets
- **SQLAlchemy 2.x & asyncpg**: Async ORM & database driver
- **Alembic**: Database migrations
- **PostgreSQL 15+**: Relational database persistence
- **OSMnx**: OpenStreetMap pedestrian (`walk`) and vehicle (`drive`) network topology
- **NetworkX**: Directed graph modeling and Dijkstra shortest path solver
- **GeoPandas & Shapely**: Spatial geometries and distance calculations
- **SciPy & NumPy**: Spatial $k$-d tree indexing and vectorized haversine computations
- **Pydantic v2**: Request/response schemas and validation
- **Pytest**: 68 comprehensive unit and integration tests

### Frontend
- **React 18**
- **Vite 5**
- **TypeScript**
- **Tailwind CSS**
- **Leaflet & React Leaflet**
- **Lucide React Icons**

---

## 4. Database Setup & Migrations

PostgreSQL is required for collaborative multi-user sessions.

### Start PostgreSQL with Docker
```bash
docker run -d \
  --name meetpoint-db \
  -p 5432:5432 \
  -e POSTGRES_USER=meetpoint \
  -e POSTGRES_PASSWORD=meetpoint \
  -e POSTGRES_DB=meetpoint \
  postgres:15-alpine
```

### Apply Alembic Migrations
```bash
cd backend
../.venv/bin/alembic upgrade head
```

---

## 5. Running the Application

### Backend Setup
```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Install requirements
uv pip install -r backend/requirements.txt

# 3. Start FastAPI server
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Documentation (Swagger): `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### Frontend Setup
```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
```
- Web Application: `http://localhost:5173`

---

## 6. REST API & WebSocket Reference

### Collaborative Sessions API (`/api/v1/sessions`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/sessions` | Create a new collaborative meeting session | None |
| `GET` | `/api/v1/sessions/{code}` | Get session details by invitation code | None |
| `POST` | `/api/v1/sessions/{code}/join` | Join session with display name & optional coordinates | None |
| `POST` | `/api/v1/sessions/{id}/location` | Explicitly submit or update coordinates | Participant Token |
| `DELETE` | `/api/v1/sessions/{id}/location` | Explicitly withdraw shared coordinates | Participant Token |
| `POST` | `/api/v1/sessions/{id}/optimize` | Trigger meeting point optimization | Host Token |
| `GET` | `/api/v1/sessions/{id}/results` | Get latest calculation results & staleness status | Host / Participant |
| `PATCH` | `/api/v1/sessions/{id}/settings` | Update title, objective, mode, or top-$k$ | Host Token |
| `DELETE` | `/api/v1/sessions/{id}/participants/{p_id}` | Remove a participant from the meeting | Host Token |
| `POST` | `/api/v1/sessions/{id}/leave` | Participant voluntarily leaves meeting | Participant Token |
| `POST` | `/api/v1/sessions/{id}/close` | Permanently close the session | Host Token |

### WebSocket Endpoint (`/api/v1/sessions/{session_id}/ws`)

Connect with query parameter: `ws://localhost:8000/api/v1/sessions/{session_id}/ws?token={token}`

**Synchronized Event Types**:
- `session_snapshot`: Initial state delivered upon connection (session, participants, latest result, user role).
- `participant_joined`: Emitted when a new participant enters the room.
- `participant_updated`: Emitted when coordinates, display name, or online status changes.
- `participant_left` / `participant_removed`: Emitted when a participant leaves or is removed.
- `settings_updated`: Emitted when host changes session parameters.
- `optimization_started`: Emitted when optimization begins.
- `optimization_completed`: Emitted with full route results and candidate recommendations.
- `optimization_failed`: Emitted if graph calculation fails.
- `result_stale`: Emitted when coordinates change after calculation, warning the room that results are outdated.
- `session_closed`: Emitted when host terminates the meeting.

---

## 7. Running the Automated Tests

The test suite includes 68 automated unit, integration, and WebSocket tests:

```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests -v
```

### Coverage:
- **Phase 1 (Core Geospatial)**: Dijkstra correctness, one-way roads, graph connectivity, 1-Median solver.
- **Phase 2 (Advanced Optimization)**: Pedestrian networks, 1-Center solver, minimax tie-breaking, route reconstruction.
- **Phase 3 (Frontend & API)**: API validation, bounding box calculations, candidate rankings.
- **Phase 4 (Collaboration)**: Session lifecycle, cryptographic token hashing, host/participant permissions, location privacy, staleness triggers, WebSocket authentication, and event broadcasting.

---

## 8. Directory Structure

```text
meetpoint/
├── backend/
│   ├── alembic/                       # Database migration versions & env.py
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py                    # FastAPI app, lifespan, CORS, routers
│   │   ├── api/
│   │   │   ├── routes.py              # Phase 1-3 single-user optimization routes
│   │   │   ├── session_routes.py      # Phase 4 collaborative session REST routes
│   │   │   └── websocket.py           # Phase 4 real-time WebSocket endpoint
│   │   ├── core/
│   │   │   ├── config.py              # Pydantic Settings & environment variables
│   │   │   ├── exceptions.py          # Domain exceptions
│   │   │   ├── logging.py             # Structured logger
│   │   │   └── security.py            # Token generation, SHA-256 hashing & verification
│   │   ├── db/
│   │   │   ├── base.py                # SQLAlchemy 2.x DeclarativeBase
│   │   │   ├── session.py             # Async engine & get_db dependency
│   │   │   └── models/
│   │   │       └── session_models.py  # MeetingSession, SessionParticipant, SessionOptimization
│   │   ├── models/
│   │   │   ├── geometry.py            # Coordinate and BoundingBox
│   │   │   ├── schemas.py             # Optimization request/response schemas
│   │   │   └── session_schemas.py     # Collaborative session Pydantic schemas
│   │   ├── services/
│   │   │   ├── connection_manager.py  # In-memory WebSocket room manager
│   │   │   ├── session_service.py     # Collaborative session domain & persistence logic
│   │   │   ├── network_service.py     # OSMnx graph downloading & GraphML caching
│   │   │   ├── snapping_service.py    # 3D KDTree spatial snapping
│   │   │   └── optimization_service.py# Multi-objective Dijkstra route engine
│   │   └── algorithms/
│   │       ├── dijkstra.py            # NetworkX shortest paths & node sequence
│   │       ├── one_median.py          # Network 1-Median optimizer
│   │       └── one_center.py          # Network 1-Center optimizer
│   ├── tests/
│   │   ├── test_sessions.py           # Collaborative session lifecycle & auth tests
│   │   ├── test_websocket.py          # WebSocket sync & event broadcast tests
│   │   ├── test_api.py                # Core API tests
│   │   ├── test_dijkstra.py           # Dijkstra tests
│   │   ├── test_one_median.py         # 1-Median ground truth tests
│   │   ├── test_one_center.py         # 1-Center ground truth tests
│   │   ├── test_route_reconstruction.py
│   │   └── ...
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── collaborative/
│   │   │   │   ├── LandingPage.tsx           # Multi-user landing view
│   │   │   │   ├── CreateMeetingModal.tsx    # Host meeting creation modal
│   │   │   │   ├── JoinMeetingModal.tsx      # Participant join & privacy consent modal
│   │   │   │   ├── CollaborativeRoom.tsx     # Live collaborative room container
│   │   │   │   ├── SessionHeader.tsx         # Header with code copy & live badge
│   │   │   │   ├── SessionParticipantList.tsx# Participant presence & location status
│   │   │   │   ├── HostControls.tsx          # Calculate, recalculate, close actions
│   │   │   │   ├── ParticipantControls.tsx   # GPS share, map pick, withdraw actions
│   │   │   │   └── SessionSettingsModal.tsx  # Host runtime settings modal
│   │   │   ├── layout/Navbar.tsx
│   │   │   ├── map/MapView.tsx               # React Leaflet map with live pins & routes
│   │   │   ├── optimization/OptimizationControls.tsx
│   │   │   ├── participants/ParticipantList.tsx
│   │   │   └── results/ResultsPanel.tsx      # Optimal card, routes list, candidates
│   │   ├── hooks/
│   │   │   └── useSessionWebSocket.ts        # Auto-reconnecting WebSocket hook
│   │   ├── services/
│   │   │   ├── api.ts                        # Core optimization API client
│   │   │   └── sessionApi.ts                 # Session REST API client
│   │   ├── types/
│   │   │   ├── index.ts                      # Core geometry & optimization types
│   │   │   └── session.ts                    # Collaborative session & WebSocket types
│   │   ├── utils/colors.ts                   # Color palettes & Leaflet DivIcons
│   │   ├── App.tsx                           # Master view coordinator (Landing/Room/Sandbox)
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── pytest.ini
└── README.md
```
