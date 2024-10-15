#!/bin/bash

if [ "$SERVICE_TYPE" = "service" ]; then
    python service.py
elif [ "$SERVICE_TYPE" = "client" ]; then
    streamlit run client.py
else
    echo "Unknown service type"
    exit 1
fi