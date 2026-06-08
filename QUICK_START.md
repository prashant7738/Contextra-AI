# Quick Start Guide - Authentication System

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Node.js 18+ (for frontend)
- Python 3.12+ (for backend)
- pip or another Python package manager

---

## Backend Setup

### 1. Install Dependencies

```bash
cd backend
pip install -e .
```

This will install:
- `python-jose[cryptography]` - JWT token handling
- `bcrypt` - Password hashing
- All other dependencies from `pyproject.toml`

### 2. Set Environment Variables

Create or update `.env` file in the `backend` directory:

```env
# Database (if not already set)
DATABASE_URL=postgresql://user:password@localhost/dbname

# JWT Configuration (use strong secret key in production!)
SECRET_KEY=dev-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# API CORS settings
CORS_ORIGINS=http://localhost:4321,http://127.0.0.1:4321,http://localhost:3000
```

### 3. Database Migration

```bash
# Generate migration
alembic revision --autogenerate -m "add_password_hash_to_users"

# Apply migration
alembic upgrade head
```

If using SQLite for development, you can skip migrations and let FastAPI create the tables.

### 4. Run Backend Server

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ Backend running at: `http://localhost:8000`
📚 API docs at: `http://localhost:8000/docs`

---

## Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Set Environment Variables (Optional)

Create or update `.env.local` file in the `frontend` directory:

```env
PUBLIC_API_BASE_URL=http://localhost:8000
```

### 3. Run Development Server

```bash
npm run dev
```

✅ Frontend running at: `http://localhost:4321`

---

## Test the Authentication System

### Option 1: Using the Web UI

1. Open `http://localhost:4321` in your browser
2. You'll be redirected to `/login`
3. Click "Register here" to create a new account
4. Fill in the registration form:
   - Name: `Test User`
   - Email: `test@example.com`
   - Password: `testpass123`
   - Confirm Password: `testpass123`
5. Click "Register"
6. You'll be redirected to `/dashboard`
7. Click "Logout" to test logout

### Option 2: Using cURL

```bash
# 1. Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "password": "testpass123"
  }'

# 2. Save the returned tokens
# Response will look like:
# {
#   "access_token": "eyJhbGc...",
#   "refresh_token": "eyJhbGc...",
#   "token_type": "bearer"
# }

# 3. Get current user (use access_token from above)
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer <access_token_here>"

# 4. Refresh token
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "<refresh_token_here>"
  }'

# 5. Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

---

## Common Tasks

### Create a Test User Programmatically

```python
from app.repositories.user_repository import create_user
from app.database import SessionLocal

db = SessionLocal()
user = create_user(db, name="John Doe", email="john@example.com", password="secure123")
print(f"User created: {user.email}")
```

### View API Documentation

Open `http://localhost:8000/docs` in your browser to see:
- All available endpoints
- Request/response schemas
- Try-it-out interface for testing

### Check User in Database

```bash
# If using SQLite
sqlite3 my_vector_db/chroma.sqlite3 "SELECT id, name, email FROM users;"

# If using PostgreSQL
psql -d your_database -c "SELECT id, name, email FROM users;"
```

### Clear User Tokens (on Frontend)

Open browser console and run:
```javascript
localStorage.removeItem('access_token');
localStorage.removeItem('refresh_token');
localStorage.removeItem('current_user');
window.location.href = '/login';
```

---

## What Gets Stored Where

### Backend
- User data (name, email) → PostgreSQL/SQLite `users` table
- Password → Hashed and stored in `password_hash` column
- JWT Secret → Environment variable `SECRET_KEY`

### Frontend (localStorage)
- `access_token` - JWT for API requests
- `refresh_token` - JWT for refreshing access token
- `current_user` - Cached user info (name, email, id)

---

## Key URLs

| URL | Purpose | Requires Auth |
|-----|---------|---|
| `/` | Redirect page | No |
| `/login` | Login page | No |
| `/register` | Registration page | No |
| `/dashboard` | Main app | Yes |

## API Endpoints

| Method | Path | Description | Requires Auth |
|--------|------|-------------|---|
| POST | `/auth/register` | Register new user | No |
| POST | `/auth/login` | Login user | No |
| POST | `/auth/refresh` | Get new access token | No |
| GET | `/auth/me` | Get current user info | Yes |
| GET | `/users` | List all users | No |
| GET | `/users/{id}` | Get user by ID | No |
| DELETE | `/users/{id}` | Delete user | No |

---

## Troubleshooting

### "Module not found" Error
```bash
# Backend
pip install -e .

# Frontend
npm install
```

### CORS Errors
- Check `CORS_ORIGINS` env var includes frontend URL
- Restart backend server after changing env vars

### Token Errors
- Check `SECRET_KEY` is set and consistent
- Verify token format: `Authorization: Bearer <token>`
- Tokens expire - use refresh endpoint for new access token

### Database Errors
```bash
# Check/create database
alembic upgrade head

# Or check PostgreSQL connection
psql postgresql://user:password@localhost/dbname
```

### Port Already in Use
```bash
# Change backend port
python -m uvicorn app.main:app --reload --port 8001

# Change frontend port
npm run dev -- --port 4322
```

---

## Next Steps

1. ✅ Test registration and login
2. ✅ Verify tokens are stored in localStorage
3. ✅ Test API endpoints with Swagger docs
4. 📝 Update `.env` with production values when deploying
5. 🔒 Implement password reset functionality
6. 📧 Add email verification
7. 🛡️ Add rate limiting to auth endpoints
8. 📊 Set up logging and monitoring

---

## Production Checklist

Before deploying to production:

- [ ] Change `SECRET_KEY` to a strong, random value
- [ ] Set `ACCESS_TOKEN_EXPIRE_MINUTES` to appropriate value (15-30 min recommended)
- [ ] Enable HTTPS/SSL
- [ ] Consider using httpOnly cookies instead of localStorage
- [ ] Implement password requirements validation
- [ ] Add email verification
- [ ] Set up rate limiting
- [ ] Enable logging and monitoring
- [ ] Regular security audits
- [ ] Use environment-specific configurations

---

## Support

For detailed information:
- See `AUTH_SETUP.md` for complete authentication documentation
- See `IMPLEMENTATION_SUMMARY.md` for full implementation details
- Check backend API docs at `http://localhost:8000/docs`

Happy coding! 🎉
