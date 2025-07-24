#!/bin/bash

# Set folder names for ScalerEval and frontend
ScalerEval_DIR="ScalerEval"
FRONTEND_DIR="K8sDashboard"

# Enter ScalerEval directory and perform build and run
echo "Entering ScalerEval directory: $ScalerEval_DIR"
cd "$ScalerEval_DIR" || { echo "Failed to enter ScalerEval directory: $ScalerEval_DIR"; exit 1; }

# Build ScalerEval Docker image
echo "Building ScalerEval image..."
docker build -t scalereval .

# Go back to parent directory
cd ..

# Enter frontend directory and perform build and run
echo "Entering frontend directory: $FRONTEND_DIR"
cd "$FRONTEND_DIR" || { echo "Failed to enter frontend directory: $FRONTEND_DIR"; exit 1; }

# Build frontend Docker image
echo "Building frontend image..."
docker build -t frontend-app .

# Run frontend container
echo "Running frontend container..."
docker run -d -p 10000:10000 --name frontend frontend-app

# Run ScalerEval container
echo "Running ScalerEval container..."
docker run -d -p 10001:10001 --name scalereval scalereval

# Go back to parent directory
cd ..

echo "All operations completed. You can open http://localhost:10000"