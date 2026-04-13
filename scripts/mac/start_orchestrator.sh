#!/bin/bash
# Mac - 启动Orchestrator服务

export DEVICE=mac
source venv/bin/activate
uvicorn src.services.orchestrator.main:app --host 0.0.0.0 --port 8002
