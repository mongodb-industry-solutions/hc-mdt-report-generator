# ClarityGR Makefile
.PHONY: help install setup backend frontend dev clean test

help:
	@echo "ClarityGR Commands:"
	@echo "  setup     - Complete setup (install + db + templates)"
	@echo "  install   - Install dependencies"
	@echo "  backend   - Start backend server"
	@echo "  frontend  - Start frontend server" 
	@echo "  dev       - Development info"
	@echo "  test      - Run tests"
	@echo "  clean     - Clean artifacts"

setup: install
	@echo "Setting up database..."
	@python scripts/setup_mongodb_cluster.py
	@python scripts/add_template_to_mongodb.py --add scripts/templates/new_entities_no_filter_template.json --active
	@echo "✅ Setup complete!"

install:
	@echo "Installing dependencies..."
	@pip install -r backend/requirements.txt
	@cd frontend && npm install

backend:
	@cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

frontend:
	@cd frontend && npm run dev

dev:
	@echo "Start development servers:"
	@echo "  Terminal 1: make backend"
	@echo "  Terminal 2: make frontend"
	@echo "  Then open: http://localhost:5173"

test:
	@python -m pytest tests/ -v

clean:
	@rmdir /s /q frontend\dist 2>nul || echo ""
	@rmdir /s /q frontend\node_modules\.vite 2>nul || echo ""
	@for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"