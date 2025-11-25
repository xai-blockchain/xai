# Local Development Setup

This guide will help you set up a local development environment for the blockchain project.

## Prerequisites

Before you begin, ensure you have the following installed:

### Required Software

- **Python**: 3.10 or higher
- **Node.js**: 16.x or higher (for frontend tools)
- **Git**: Latest version
- **Database**: PostgreSQL 14+ or MongoDB 5.0+

### Optional Tools

- **Docker**: For containerized development
- **Redis**: For caching (recommended)
- **Nginx**: For reverse proxy testing

## System Requirements

### Minimum Requirements

- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 50GB free space
- **OS**: Windows 10+, macOS 10.15+, or Linux (Ubuntu 20.04+)

### Recommended Requirements

- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Storage**: 100GB+ SSD
- **OS**: Linux (Ubuntu 22.04)

## Installation

### Step 1: Clone the Repository

```bash
# Clone the repository
git clone https://github.com/your-org/blockchain-project.git
cd blockchain-project

# Checkout the development branch
git checkout develop
```

### Step 2: Set Up Python Environment

#### Using venv (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

#### Using conda (Alternative)

```bash
# Create conda environment
conda create -n blockchain python=3.11
conda activate blockchain

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Install Development Dependencies

```bash
# Install development tools
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### Step 4: Database Setup

#### PostgreSQL Setup

```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start PostgreSQL service
sudo systemctl start postgresql

# Create database and user
sudo -u postgres psql
```

```sql
CREATE DATABASE blockchain_dev;
CREATE USER blockchain_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE blockchain_dev TO blockchain_user;
\q
```

#### MongoDB Setup (Alternative)

```bash
# Install MongoDB (Ubuntu/Debian)
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt update
sudo apt install -y mongodb-org

# Start MongoDB
sudo systemctl start mongod
```

### Step 5: Configuration

#### Create Configuration File

```bash
# Copy example configuration
cp config.example.yaml config.yaml

# Edit configuration
nano config.yaml
```

#### Sample Configuration (config.yaml)

```yaml
# Development Configuration
environment: development

# Database Configuration
database:
  type: postgresql  # or mongodb
  host: localhost
  port: 5432
  name: blockchain_dev
  user: blockchain_user
  password: your_secure_password

# Network Configuration
network:
  host: 0.0.0.0
  port: 5000
  p2p_port: 8333

# Blockchain Configuration
blockchain:
  difficulty: 4
  block_time: 10
  reward: 50
  halving_interval: 210000

# Consensus Configuration
consensus:
  type: pow  # or pos, dpos
  min_validators: 1

# Logging Configuration
logging:
  level: DEBUG
  file: logs/blockchain.log
  max_size: 100MB
  backup_count: 5

# Cache Configuration
cache:
  enabled: true
  type: redis
  host: localhost
  port: 6379
  ttl: 3600

# API Configuration
api:
  enabled: true
  cors_enabled: true
  rate_limit: 100
  api_key_required: false

# Security
security:
  secret_key: your_secret_key_here_change_in_production
  jwt_expiry: 3600
```

### Step 6: Initialize Blockchain

```bash
# Run database migrations
python scripts/migrate.py

# Initialize genesis block
python scripts/init_genesis.py

# Create initial wallets (optional)
python scripts/create_wallets.py
```

### Step 7: Start Development Server

```bash
# Start the blockchain node
python src/node.py

# In another terminal, start the API server
python src/api_server.py

# In another terminal, start the block explorer (optional)
cd explorer
npm install
npm start
```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_blockchain.py

# Run with verbose output
pytest -v

# Run integration tests only
pytest tests/integration/
```

### Code Quality Checks

```bash
# Run linter
flake8 src/

# Run type checker
mypy src/

# Run formatter
black src/

# Run all pre-commit hooks
pre-commit run --all-files
```

### Database Management

```bash
# Create migration
python scripts/create_migration.py "migration_name"

# Run migrations
python scripts/migrate.py

# Rollback migration
python scripts/migrate.py --rollback

# Reset database (WARNING: destroys data)
python scripts/reset_db.py
```

### Blockchain Operations

```bash
# Mine a new block
python scripts/mine_block.py

# Send a transaction
python scripts/send_transaction.py --from ADDR1 --to ADDR2 --amount 10

# Check wallet balance
python scripts/check_balance.py --address ADDR

# Validate blockchain integrity
python scripts/validate_chain.py

# Export blockchain data
python scripts/export_chain.py --output data/export.json
```

## Docker Development

### Using Docker Compose

```bash
# Build containers
docker-compose build

# Start all services
docker-compose up

# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Reset everything (WARNING: destroys data)
docker-compose down -v
```

### Sample docker-compose.yml

```yaml
version: '3.8'

services:
  node:
    build: .
    ports:
      - "5000:5000"
      - "8333:8333"
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=postgresql://user:pass@db:5432/blockchain
    depends_on:
      - db
      - redis
    volumes:
      - ./src:/app/src
      - blockchain_data:/data

  db:
    image: postgres:14
    environment:
      POSTGRES_DB: blockchain_dev
      POSTGRES_USER: blockchain_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  explorer:
    build: ./explorer
    ports:
      - "3000:3000"
    depends_on:
      - node

volumes:
  blockchain_data:
  postgres_data:
  redis_data:
```

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Find process using port 5000
lsof -i :5000

# Kill the process
kill -9 <PID>
```

#### Database Connection Issues

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Restart PostgreSQL
sudo systemctl restart postgresql

# Check connection
psql -U blockchain_user -d blockchain_dev -h localhost
```

#### Python Dependencies Issues

```bash
# Clear pip cache
pip cache purge

# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Check for conflicts
pip check
```

#### Blockchain Sync Issues

```bash
# Delete blockchain data and resync
rm -rf data/blocks/*
python scripts/init_genesis.py

# Reset peer connections
python scripts/reset_peers.py
```

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Set environment variable
export DEBUG=1

# Or in config.yaml
logging:
  level: DEBUG
```

### Performance Profiling

```bash
# Run with profiler
python -m cProfile -o profile.stats src/node.py

# Analyze profile
python -m pstats profile.stats
```

## IDE Setup

### VSCode Configuration

Create `.vscode/settings.json`:

```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "editor.formatOnSave": true,
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true
  }
}
```

### PyCharm Configuration

1. Open project in PyCharm
2. Set Python interpreter to venv
3. Enable pytest as test runner
4. Configure Black as code formatter
5. Enable type checking (mypy)

## Environment Variables

Create `.env` file for environment-specific settings:

```bash
# Application
ENVIRONMENT=development
DEBUG=1

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/blockchain_dev

# Network
API_HOST=0.0.0.0
API_PORT=5000
P2P_PORT=8333

# Security
SECRET_KEY=your_secret_key_change_in_production
JWT_SECRET=your_jwt_secret_change_in_production

# External Services
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=DEBUG
LOG_FILE=logs/blockchain.log
```

Load environment variables:

```bash
# Install python-dotenv
pip install python-dotenv

# In your Python code
from dotenv import load_dotenv
load_dotenv()
```

## Next Steps

- [Run Tests](../testing/running-tests.md)
- [API Documentation](../api/rest-api.md)
- [Contributing Guidelines](../../CONTRIBUTING.md)
- [Architecture Overview](../architecture/overview.md)

## Getting Help

- Check [FAQ](../user-guides/faq.md)
- Join [Discord community](#)
- Open [GitHub issue](https://github.com/your-org/blockchain-project/issues)
- Email: dev-support@blockchain-project.io

---

*Last updated: 2025-11-12*
