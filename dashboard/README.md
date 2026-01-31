# Omni2 Internal Dashboard

**Modern, real-time dashboard for monitoring and managing Omni2 MCP Hub**

---

## 🎯 Overview

Internal dashboard for Omni2 administrators to:
- Monitor system health and performance
- Manage MCP servers
- Track user activity and usage
- Analyze costs and trends

**Access**: Internal only via Traefik at `http://localhost:8090/dashboard`

---

## 🏗️ Architecture

```
Dashboard Backend (FastAPI) → Omni2 API → MCPs
      :8100                      :8000      :8300+
         ↓
   Omni2 Database
   (omni2 schema)
```

**Key Principles**:
1. Dashboard NEVER calls MCPs directly
2. All data flows through Omni2 API
3. Reads from omni2 schema directly for stats
4. Uses same JWT auth as Omni2 (via Traefik)

---

## 📁 Project Structure

```
dashboard/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── routers/      # API endpoints
│   │   ├── services/     # Business logic
│   │   ├── schemas/      # Pydantic models
│   │   └── main.py       # FastAPI app
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/             # Next.js 14 frontend
│   ├── src/
│   │   ├── app/          # App router pages
│   │   ├── components/   # React components
│   │   └── lib/          # Utilities
│   ├── Dockerfile.dev
│   └── package.json
│
├── progress/             # Phase tracking
│   ├── PHASE_1.md        # Foundation
│   ├── PHASE_2.md        # MCP Management
│   ├── PHASE_3.md        # User Management
│   └── PHASE_4.md        # Polish
│
├── docker-compose.yml    # Dashboard services
├── .env                  # Configuration
├── PROGRESS.md           # Overall progress
└── README.md             # This file
```

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Omni2 stack running
- Traefik gateway running
- Access to omni2 database

### Setup

1. **Navigate to dashboard folder**:
```bash
cd omni2/dashboard
```

2. **Create `.env` file**:
```bash
# Copy from example
cp .env.example .env

# Edit configuration
nano .env
```

3. **Start services**:
```bash
docker-compose up -d
```

4. **Access dashboard**:
```
http://localhost:8090/dashboard
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Backend
DASHBOARD_PORT=8100
OMNI2_API_URL=http://omni2:8000
DATABASE_URL=postgresql://omni:omni@omni_pg_db:5432/omni

# Frontend
NEXT_PUBLIC_API_URL=/dashboard/api
```

### Traefik Labels

```yaml
# Backend API
- "traefik.http.routers.dashboard-api.rule=PathPrefix(`/dashboard/api`)"
- "traefik.http.routers.dashboard-api.middlewares=auth-forward,dashboard-strip"

# Frontend
- "traefik.http.routers.dashboard-web.rule=PathPrefix(`/dashboard`)"
- "traefik.http.routers.dashboard-web.middlewares=auth-forward"
```

---

## 📊 Features

### Phase 1: Foundation ✅
- Hero stats cards (MCPs, Users, Queries, Cost)
- Real-time activity feed
- Performance charts (queries, cost, response times, errors)
- ChatWidget integration

### Phase 2: MCP Management 🔄
- MCP server grid with health status
- MCP detail pages
- Tool usage statistics
- Real-time logs

### Phase 3: User Management ⏳
- User list with search/filter
- User detail pages
- Activity timeline
- Permission management

### Phase 4: Polish ⏳
- Glassmorphism design
- Smooth animations
- Performance optimization
- Testing & documentation

---

## 🎨 Design System

### Colors

```css
--bg-primary: #0F172A;      /* Dark background */
--bg-secondary: #1E293B;    /* Card background */
--accent-purple: #8B5CF6;   /* Primary accent */
--accent-blue: #3B82F6;     /* Info */
--accent-green: #10B981;    /* Success */
--accent-orange: #F59E0B;   /* Warning */
--accent-red: #EF4444;      /* Error */
```

### Typography

- **Font**: Inter (system font fallback)
- **Headings**: 600 weight
- **Body**: 400 weight
- **Code**: JetBrains Mono

### Components

- **Cards**: Glassmorphic with backdrop blur
- **Buttons**: Gradient on hover
- **Badges**: Rounded with status colors
- **Charts**: Recharts with custom theme

---

## 🔗 API Endpoints

### Dashboard Stats

```
GET /api/v1/dashboard/stats
GET /api/v1/dashboard/activity
GET /api/v1/dashboard/charts/queries
GET /api/v1/dashboard/charts/cost
GET /api/v1/dashboard/charts/response-times
GET /api/v1/dashboard/charts/errors
```

### MCP Management

```
GET /api/v1/mcps
GET /api/v1/mcps/{id}
GET /api/v1/mcps/{id}/tools
GET /api/v1/mcps/{id}/logs
GET /api/v1/mcps/{id}/config
GET /api/v1/mcps/{id}/analytics
POST /api/v1/mcps/{id}/health
```

### User Management

```
GET /api/v1/users
GET /api/v1/users/{id}
GET /api/v1/users/{id}/stats
GET /api/v1/users/{id}/activity
GET /api/v1/users/{id}/permissions
```

---

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest tests/
```

### Frontend Tests

```bash
cd frontend
npm test
```

### E2E Tests

```bash
cd frontend
npm run test:e2e
```

---

## 📈 Monitoring

### Health Checks

```bash
# Backend health
curl http://localhost:8100/health

# Frontend health
curl http://localhost:3000/api/health
```

### Logs

```bash
# Backend logs
docker logs dashboard-backend

# Frontend logs
docker logs dashboard-frontend
```

---

## 🐛 Troubleshooting

### Dashboard not accessible

1. Check Traefik is running
2. Verify Traefik labels are correct
3. Check network connectivity

### Data not loading

1. Verify Omni2 API is running
2. Check database connection
3. Review backend logs

### Charts not rendering

1. Check browser console for errors
2. Verify data format matches schema
3. Clear browser cache

---

## 📝 Development

### Backend Development

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8100
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

---

## 🚢 Deployment

### Production Checklist

- [ ] Update `.env` with production values
- [ ] Enable HTTPS in Traefik
- [ ] Configure rate limiting
- [ ] Setup monitoring
- [ ] Enable caching (Redis)
- [ ] Run security audit
- [ ] Test all features

---

## 📚 Documentation

- **Progress Tracking**: See `PROGRESS.md`
- **Phase Details**: See `progress/PHASE_*.md`
- **API Docs**: Available at `/dashboard/api/docs`
- **Architecture**: See main `README.md` in project root

---

## 🤝 Contributing

1. Check `PROGRESS.md` for current phase
2. Pick a task from phase markdown
3. Create feature branch
4. Implement feature
5. Update progress markdown
6. Test thoroughly
7. Submit for review

---

## 📄 License

Internal use only - Shift4 Corporation

---

**Last Updated**: January 26, 2026  
**Version**: 0.1.0  
**Status**: In Development
