# GUARDIAN

For dev:
    backend:
        docker compose -f docker-compose.dev.yml up --build
    frontend:
        cd frontend\app
        npm install
        npm run dev -- --host (to deploy on local network - will show address in terminal)