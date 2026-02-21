# Clean Rebuild Frontend - Manual Steps

## Step 1: Remove .next folder
```bash
cd omni2/dashboard/frontend
rm -rf .next
# or on Windows:
rmdir /s /q .next
```

## Step 2: Stop containers
```bash
cd omni2
docker-compose down
```

## Step 3: Rebuild frontend
```bash
docker-compose build omni2-dashboard-frontend
```

## Step 4: Start all services
```bash
docker-compose up -d
```

## Step 5: Check status
```bash
docker-compose ps
docker-compose logs -f omni2-dashboard-frontend
```

## Quick Commands (run from omni2 directory)

### Windows:
```cmd
cd dashboard\frontend && rmdir /s /q .next && cd ..\.. && docker-compose down && docker-compose build omni2-dashboard-frontend && docker-compose up -d
```

### Linux/Mac:
```bash
rm -rf dashboard/frontend/.next && docker-compose down && docker-compose build omni2-dashboard-frontend && docker-compose up -d
```

## Verify
- Frontend: http://localhost:3000
- Dashboard Backend: http://localhost:8001
- PT Service: http://localhost:8200
