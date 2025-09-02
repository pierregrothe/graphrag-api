#!/bin/bash
# scripts/deploy-cloudrun.sh
# Google Cloud Run deployment script
# Author: Pierre Grothé
# Creation Date: 2025-09-02

set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-"your-project-id"}
REGION=${REGION:-"us-central1"}
SERVICE_NAME=${SERVICE_NAME:-"graphrag-api"}
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}GraphRAG API - Google Cloud Run Deployment${NC}"
echo "============================================"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${YELLOW}Not logged in to Google Cloud. Please authenticate:${NC}"
    gcloud auth login
fi

# Set project
echo -e "${YELLOW}Setting project to: $PROJECT_ID${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}Enabling required APIs...${NC}"
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    secretmanager.googleapis.com

# Create secrets if they don't exist
echo -e "${YELLOW}Creating secrets...${NC}"

# Check if GOOGLE_API_KEY secret exists
if ! gcloud secrets describe graphrag-api-key --project=$PROJECT_ID &>/dev/null; then
    echo -e "${YELLOW}Creating GOOGLE_API_KEY secret...${NC}"
    echo -n "Enter your Google API Key: "
    read -s GOOGLE_API_KEY
    echo
    echo -n "$GOOGLE_API_KEY" | gcloud secrets create graphrag-api-key \
        --data-file=- \
        --replication-policy="automatic"
else
    echo -e "${GREEN}Secret graphrag-api-key already exists${NC}"
fi

# Check if JWT_SECRET_KEY secret exists
if ! gcloud secrets describe graphrag-jwt-secret --project=$PROJECT_ID &>/dev/null; then
    echo -e "${YELLOW}Creating JWT_SECRET_KEY secret...${NC}"
    JWT_SECRET=$(openssl rand -hex 32)
    echo -n "$JWT_SECRET" | gcloud secrets create graphrag-jwt-secret \
        --data-file=- \
        --replication-policy="automatic"
    echo -e "${GREEN}Generated JWT secret${NC}"
else
    echo -e "${GREEN}Secret graphrag-jwt-secret already exists${NC}"
fi

# Create service account if it doesn't exist
SERVICE_ACCOUNT="graphrag-api@$PROJECT_ID.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe $SERVICE_ACCOUNT --project=$PROJECT_ID &>/dev/null; then
    echo -e "${YELLOW}Creating service account...${NC}"
    gcloud iam service-accounts create graphrag-api \
        --display-name="GraphRAG API Service Account"

    # Grant necessary permissions
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/secretmanager.secretAccessor"
else
    echo -e "${GREEN}Service account already exists${NC}"
fi

# Build and deploy using Cloud Build
echo -e "${YELLOW}Starting Cloud Build deployment...${NC}"
gcloud builds submit \
    --config=cloudbuild.yaml \
    --substitutions=_DEPLOY_REGION=$REGION

# Get the service URL
echo -e "${GREEN}Deployment complete!${NC}"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --format="value(status.url)")

echo -e "${GREEN}Service deployed at: $SERVICE_URL${NC}"
echo ""
echo "Next steps:"
echo "1. Test the API: curl $SERVICE_URL/health"
echo "2. View logs: gcloud run services logs read $SERVICE_NAME --region=$REGION"
echo "3. Update environment variables if needed:"
echo "   gcloud run services update $SERVICE_NAME --region=$REGION --update-env-vars=KEY=VALUE"
