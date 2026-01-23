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
	@pip install -r requirements.txt
	@cd ui && npm install

backend:
	@uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

frontend:
	@cd ui && npm run dev

dev:
	@echo "Start development servers:"
	@echo "  Terminal 1: make backend"
	@echo "  Terminal 2: make frontend"
	@echo "  Then open: http://localhost:5173"

test:
	@python -m pytest tests/ -v

clean:
	@rmdir /s /q ui\dist 2>nul || echo ""
	@rmdir /s /q ui\node_modules\.vite 2>nul || echo ""
	@for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"