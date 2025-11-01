#!/bin/bash
# Script to retry creating GCP GPU instance when capacity becomes available
# Usage: ./scripts/gcp_create_instance_retry.sh [zone]

set -e

PROJECT_ID="langchain-demo-476911"
INSTANCE_NAME="langchain-gpu-instance"
ZONE="${1:-europe-west1-b}"  # Default to europe-west1-b, can override
MACHINE_TYPE="n1-standard-4"
GPU_TYPE="nvidia-tesla-t4"
GPU_COUNT=1

echo "Attempting to create GPU instance..."
echo "Project: $PROJECT_ID"
echo "Zone: $ZONE"
echo "Instance: $INSTANCE_NAME"
echo "Machine Type: $MACHINE_TYPE"
echo "GPU: $GPU_TYPE x $GPU_COUNT"
echo ""

# Try to create the instance
gcloud compute instances create $INSTANCE_NAME \
  --project=$PROJECT_ID \
  --zone=$ZONE \
  --machine-type=$MACHINE_TYPE \
  --accelerator=type=$GPU_TYPE,count=$GPU_COUNT \
  --maintenance-policy=TERMINATE \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=100GB \
  --boot-disk-type=pd-ssd \
  --scopes=https://www.googleapis.com/auth/cloud-platform

if [ $? -eq 0 ]; then
  echo ""
  echo "✓ Success! Instance created: $INSTANCE_NAME"
  echo ""
  echo "Next steps:"
  echo "1. SSH into instance: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
  echo "2. Install NVIDIA drivers (see docs/SERVER_SETUP_GCP.md)"
  echo "3. Follow server setup guide"
  exit 0
else
  echo ""
  echo "✗ Failed - likely capacity issue. Try again later or different zone."
  exit 1
fi

