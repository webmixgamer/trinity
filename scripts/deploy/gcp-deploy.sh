#!/bin/bash
# GCP Deployment Script for Trinity Agent Platform
#
# Prerequisites:
#   1. Copy deploy.config.example to deploy.config
#   2. Fill in your GCP project, zone, instance, and domain
#   3. Run: ./scripts/deploy/gcp-deploy.sh
#
# Usage:
#   ./scripts/deploy/gcp-deploy.sh          # Full deployment
#   ./scripts/deploy/gcp-deploy.sh sync     # Sync files only
#   ./scripts/deploy/gcp-deploy.sh restart  # Restart services only

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONFIG_FILE="${PROJECT_ROOT}/deploy.config"

# Check for config file
if [ ! -f "${CONFIG_FILE}" ]; then
    echo "Error: deploy.config not found!"
    echo ""
    echo "To set up deployment:"
    echo "  1. cp deploy.config.example deploy.config"
    echo "  2. Edit deploy.config with your GCP settings"
    echo "  3. Run this script again"
    exit 1
fi

# Load configuration
source "${CONFIG_FILE}"

# Validate required variables
if [ -z "${GCP_PROJECT}" ] || [ "${GCP_PROJECT}" = "your-gcp-project-id" ]; then
    echo "Error: GCP_PROJECT not configured in deploy.config"
    exit 1
fi

if [ -z "${GCP_INSTANCE}" ] || [ "${GCP_INSTANCE}" = "your-vm-name" ]; then
    echo "Error: GCP_INSTANCE not configured in deploy.config"
    exit 1
fi

if [ -z "${GCP_ZONE}" ]; then
    echo "Error: GCP_ZONE not configured in deploy.config"
    exit 1
fi

echo "====================================="
echo "Trinity Platform - GCP Deployment"
echo "====================================="
echo ""
echo "Project:  ${GCP_PROJECT}"
echo "Instance: ${GCP_INSTANCE}"
echo "Zone:     ${GCP_ZONE}"
echo "Domain:   ${DOMAIN:-not set}"
echo ""

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -n1 > /dev/null; then
    echo "Error: Not authenticated with gcloud. Run 'gcloud auth login' first."
    exit 1
fi

# Set project
gcloud config set project "${GCP_PROJECT}" 2>/dev/null

# Function to sync files
sync_files() {
    echo "Syncing files to ${GCP_INSTANCE}..."

    # Create remote directory if it doesn't exist
    gcloud compute ssh "${GCP_INSTANCE}" \
        --zone="${GCP_ZONE}" \
        --command="mkdir -p ${REMOTE_DIR}"

    # Sync project files (excluding local dev files)
    gcloud compute scp --recurse \
        --zone="${GCP_ZONE}" \
        --compress \
        "${PROJECT_ROOT}/src" \
        "${PROJECT_ROOT}/docker" \
        "${PROJECT_ROOT}/docker-compose.prod.yml" \
        "${PROJECT_ROOT}/config" \
        "${GCP_INSTANCE}:${REMOTE_DIR}/"

    echo "Files synced."
}

# Function to create .env file on remote
create_remote_env() {
    echo "Creating .env file on remote..."

    # Build env file content
    ENV_CONTENT="# Trinity Production Environment
SECRET_KEY=${SECRET_KEY:-$(openssl rand -hex 32)}
ADMIN_PASSWORD=${ADMIN_PASSWORD:-changeme}
DEV_MODE_ENABLED=false
BACKEND_URL=${BACKEND_URL:-https://${DOMAIN}/api}
VITE_API_URL=${BACKEND_URL:-https://${DOMAIN}/api}

# OAuth (optional)
GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID:-}
GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET:-}
SLACK_CLIENT_ID=${SLACK_CLIENT_ID:-}
SLACK_CLIENT_SECRET=${SLACK_CLIENT_SECRET:-}
GITHUB_CLIENT_ID=${GITHUB_CLIENT_ID:-}
GITHUB_CLIENT_SECRET=${GITHUB_CLIENT_SECRET:-}

# Ports
BACKEND_PORT=${BACKEND_PORT:-8005}
FRONTEND_PORT=${FRONTEND_PORT:-3005}
"

    # Write to remote
    echo "${ENV_CONTENT}" | gcloud compute ssh "${GCP_INSTANCE}" \
        --zone="${GCP_ZONE}" \
        --command="cat > ${REMOTE_DIR}/.env"

    echo ".env file created."
}

# Function to restart services
restart_services() {
    echo "Restarting services on ${GCP_INSTANCE}..."

    gcloud compute ssh "${GCP_INSTANCE}" \
        --zone="${GCP_ZONE}" \
        --command="cd ${REMOTE_DIR} && sudo docker compose -f docker-compose.prod.yml down && sudo docker compose -f docker-compose.prod.yml up -d --build"

    echo "Services restarted."
}

# Function to show status
show_status() {
    echo ""
    echo "Checking service status..."

    gcloud compute ssh "${GCP_INSTANCE}" \
        --zone="${GCP_ZONE}" \
        --command="cd ${REMOTE_DIR} && sudo docker compose -f docker-compose.prod.yml ps"
}

# Main deployment logic
case "${1:-full}" in
    sync)
        sync_files
        ;;
    restart)
        restart_services
        show_status
        ;;
    env)
        create_remote_env
        ;;
    status)
        show_status
        ;;
    full|*)
        sync_files
        create_remote_env
        restart_services
        show_status

        echo ""
        echo "====================================="
        echo "Deployment Complete!"
        echo "====================================="
        echo ""
        if [ -n "${DOMAIN}" ] && [ "${DOMAIN}" != "your-domain.com" ]; then
            echo "Access your deployment at:"
            echo "  Web UI:  https://${DOMAIN}"
            echo "  API:     https://${DOMAIN}/api/docs"
        else
            # Get external IP
            EXTERNAL_IP=$(gcloud compute instances describe "${GCP_INSTANCE}" \
                --zone="${GCP_ZONE}" \
                --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
            echo "Access your deployment at:"
            echo "  Web UI:  http://${EXTERNAL_IP}:${FRONTEND_PORT:-3005}"
            echo "  API:     http://${EXTERNAL_IP}:${BACKEND_PORT:-8005}/docs"
        fi
        ;;
esac
