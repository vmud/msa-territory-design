#!/bin/bash
#
# Simple rsync Deployment Script (No sudo required)
# Syncs files from workstation to remote dev server
#
# Usage: ./deploy/rsync-deploy-simple.sh user@dev-server-ip [destination-path]
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

# Parse arguments
if [ $# -lt 1 ]; then
    echo -e "${RED}Error: Missing required argument${NC}"
    echo "Usage: $0 user@dev-server-ip [destination-path]"
    echo ""
    echo "Examples:"
    echo "  $0 ubuntu@192.168.1.100"
    echo "  $0 ubuntu@192.168.1.100 ~/retail-store-scraper"
    exit 1
fi

REMOTE_HOST="$1"
REMOTE_PATH="${2:-~/retail-store-scraper}"

# Expand tilde in remote path
if [[ "$REMOTE_PATH" == "~/"* ]]; then
    REMOTE_PATH_EXPANDED=$(ssh "$REMOTE_HOST" "echo $REMOTE_PATH")
else
    REMOTE_PATH_EXPANDED="$REMOTE_PATH"
fi

echo "=========================================="
echo "Simple rsync Deployment (No sudo)"
echo "=========================================="
echo ""
echo "Source:      $REPO_DIR"
echo "Destination: $REMOTE_HOST:$REMOTE_PATH"
echo ""

# Confirm before proceeding
read -p "Continue with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# Test SSH connection
echo -e "${YELLOW}Testing SSH connection...${NC}"
if ssh -o ConnectTimeout=5 "$REMOTE_HOST" "echo 'SSH connection successful'" 2>/dev/null; then
    echo -e "${GREEN}✓ SSH connection OK${NC}"
else
    echo -e "${RED}✗ SSH connection failed${NC}"
    echo "Please check:"
    echo "  - SSH server is running on $REMOTE_HOST"
    echo "  - Your SSH credentials are correct"
    echo "  - Network connectivity to the server"
    exit 1
fi

# Create remote directory (no sudo)
echo -e "${YELLOW}Creating remote directory...${NC}"
if ssh "$REMOTE_HOST" "mkdir -p $REMOTE_PATH"; then
    echo -e "${GREEN}✓ Remote directory ready${NC}"
else
    echo -e "${RED}✗ Failed to create remote directory${NC}"
    echo ""
    echo "Error: Cannot create $REMOTE_PATH"
    echo "Please ensure you have write permissions to the parent directory."
    exit 1
fi

# Sync files
echo -e "${YELLOW}Syncing files...${NC}"
rsync -avz --progress \
    --exclude 'venv/' \
    --exclude 'data/' \
    --exclude 'logs/' \
    --exclude '.git/' \
    --exclude 'node_modules/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache/' \
    --exclude '.coverage' \
    --exclude 'htmlcov/' \
    --exclude '.env' \
    --exclude '.DS_Store' \
    --exclude '*.log' \
    --exclude 'dist/' \
    --exclude 'build/' \
    --exclude '*.egg-info/' \
    "$REPO_DIR/" \
    "$REMOTE_HOST:$REMOTE_PATH/" || {
    echo -e "${RED}✗ rsync failed${NC}"
    exit 1
}

echo -e "${GREEN}✓ Files synced successfully${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. SSH into the server:"
echo "   ssh $REMOTE_HOST"
echo ""
echo "2. Navigate to deployment directory:"
echo "   cd $REMOTE_PATH"
echo ""
echo "3. Configure environment:"
echo "   cp .env.example .env"
echo "   nano .env  # Add your credentials"
echo ""
echo "4. Deploy using Docker:"
echo "   docker compose build"
echo "   docker compose up -d"
echo ""
echo "5. Or deploy using Python:"
echo "   python3.11 -m venv venv"
echo "   source venv/bin/activate"
echo "   pip install -r requirements.txt"
echo "   python run.py --all --test"
echo ""
echo "6. Access dashboard:"
echo "   http://$REMOTE_HOST:5001"
echo "   (Or use SSH tunnel: ssh -L 5001:localhost:5001 $REMOTE_HOST)"
echo ""
