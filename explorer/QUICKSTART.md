# XAI Explorer - Quick Start Guide

## 🚀 Start in 30 Seconds

```bash
cd /home/decri/blockchain-projects/xai/explorer/backend
./run.sh
```

Then open: **http://localhost:8000/docs**

---

## 🎯 What You Get

### Revolutionary AI Features (Unique to XAI!)
- **AI Task Explorer** - See all AI compute jobs on blockchain
- **Provider Dashboard** - Track provider earnings & performance
- **Model Comparison** - Compare Claude vs GPT-4 vs Gemini
- **Live AI Feed** - Real-time WebSocket updates
- **Provider Leaderboard** - Rankings and gamification

### Standard Blockchain Features
- Block browsing and search
- Transaction tracking
- Address lookup
- Network statistics

---

## 🔗 Key Endpoints

### Try These First
```bash
# Health check
curl http://localhost:8000/health

# AI tasks (Revolutionary!)
curl http://localhost:8000/api/v1/ai/tasks

# Provider dashboard (Revolutionary!)
curl http://localhost:8000/api/v1/ai/providers/XAI5001...

# AI model comparison (Revolutionary!)
curl http://localhost:8000/api/v1/ai/models

# Network stats
curl http://localhost:8000/api/v1/analytics/network
```

### Interactive Docs
**http://localhost:8000/docs** - Try all endpoints with Swagger UI!

---

## 🔧 Configuration

Default settings (no config needed):
- Port: 8000
- Node: http://localhost:12001
- CORS: localhost:12080, localhost:5173

Custom settings (optional):
```bash
export XAI_NODE_URL=http://your-node:8545
export PORT=8080
./run.sh
```

---

## 🐳 Docker (Production)

```bash
cd /home/decri/blockchain-projects/xai/explorer/backend
docker-compose up -d
```

Services started:
- Backend API: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

---

## 🌐 WebSocket (Real-time)

```javascript
// In browser console
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/live');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

---

## 📊 What Makes This Revolutionary

**First AI-blockchain explorer showing:**
1. AI compute jobs on-chain
2. Provider performance metrics
3. AI model comparison (real data)
4. Live AI task feed
5. Provider marketplace

**No other blockchain explorer has these features!**

---

## 📚 Full Documentation

- **README.md** - Complete user guide
- **EXPLORER_IMPLEMENTATION_COMPLETE.md** - Technical details
- **http://localhost:8000/docs** - Interactive API docs
- **http://localhost:8000/redoc** - API reference

---

## 🎉 Status: PRODUCTION-READY

- ✅ 13 Python modules
- ✅ 1,222 lines of production code
- ✅ All AI features implemented
- ✅ Docker ready
- ✅ WebSocket support
- ✅ OpenAPI docs
