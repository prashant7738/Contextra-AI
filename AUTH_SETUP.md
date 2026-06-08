# Authentication System Setup

This document explains the complete authentication system implemented for the Contextra AI project.

## Overview

The authentication system uses JWT (JSON Web Tokens) with access and refresh tokens. Users can register, login, and maintain authenticated sessions using tokens stored in localStorage on the frontend.

## Backend Setup

### 1. Dependencies Added

The following packages have been added to `pyproject.toml`:
- `python-jose[cryptography]>=3.3.0` - JWT token creation and verification
- `bcrypt>=4.1.2` - Password hashing

### 2. Database Changes

The `User` model has been updated with:
- `email` - User email (unique, indexed)
- `password_hash` - Hashed password using bcrypt

### 3. Environment Variables

Add these to your `.env` file:

```env
# JWT Configuration (optional, defaults are provided)
SECRET_KEY=your-very-secure-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 4. API Endpoints

#### Register User
- **URL:** `POST /auth/register`
- **Body:**
  ```json
  {
    "name": "John Doe",
    "email": "john@example.com",
    "password": "securepassword123"
  }
  ```
- **Response:**
  ```json
  {
    "access_token": "eyJhbGc...",
    "refresh_token": "eyJhbGc...",
    "token_type": "bearer"
  }
  ```

#### Login
- **URL:** `POST /auth/login`
- **Body:**
  ```json
  {
    "email": "john@example.com",
    "password": "securepassword123"
  }
  ```
- **Response:** Same as register

#### Refresh Token
- **URL:** `POST /auth/refresh`
- **Body:**
  ```json
  {
    "refresh_token": "eyJhbGc..."
  }
  ```
- **Response:** Same as register (new tokens)

#### Get Current User
- **URL:** `GET /auth/me`
- **Headers:** `Authorization: Bearer <access_token>`
- **Response:**
  ```json
  {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com"
  }
  ```

## Frontend Setup

### 1. Dependencies Added

New packages added to `package.json`:
- `react@^18.3.1` - React library
- `react-dom@^18.3.1` - React DOM
- `react-router-dom@^6.22.0` - Routing (if needed for SPA features)

### 2. Auth Utilities

#### `src/utils/auth.ts`

Provides the `AuthService` object with methods for:
- `getAccessToken()` - Get stored access token
- `getRefreshToken()` - Get stored refresh token
- `setTokens(tokens)` - Store tokens in localStorage
- `clearTokens()` - Remove tokens from localStorage
- `getCurrentUser()` - Get cached user info
- `setCurrentUser(user)` - Cache user info
- `isAuthenticated()` - Check if user is logged in
- `getAuthHeader()` - Get authorization header for requests

#### `src/utils/api.ts`

Provides the `apiClient` object with methods:
- `register(name, email, password)` - Register new user
- `login(email, password)` - Login user
- `refreshToken(refreshToken)` - Refresh access token
- `getMe()` - Get current user
- `getUsers(skip, limit)` - Get users list
- `get(endpoint)` - Generic GET request
- `post(endpoint, body)` - Generic POST request
- `put(endpoint, body)` - Generic PUT request
- `delete(endpoint)` - Generic DELETE request

### 3. Pages

#### `/login` - Login Page
- Email and password fields
- Error handling
- Redirects to `/dashboard` on successful login
- Link to register page

#### `/register` - Register Page
- Name, email, and password fields
- Password confirmation
- Error handling
- Redirects to `/dashboard` on successful registration
- Link to login page

#### `/dashboard` - Main App
- Protected page (redirects to login if not authenticated)
- Displays current user info
- Logout button
- Main app functionality

### 4. Components

#### `LoginPage.jsx`
React component for user login with form validation and error handling.

#### `RegisterPage.jsx`
React component for user registration with password confirmation.

#### `AuthWrapper.jsx`
React component to protect routes - redirects to login if not authenticated.

#### `ProtectedRoute.jsx`
React Router component for protected routes (optional, for SPA setups).

## Usage Flow

### Registration
1. User navigates to `/register`
2. Enters name, email, and password
3. Confirms password
4. System sends registration request to backend
5. Backend validates and creates user, returns tokens
6. Frontend stores tokens and user info in localStorage
7. User redirected to `/dashboard`

### Login
1. User navigates to `/login`
2. Enters email and password
3. System sends login request to backend
4. Backend validates credentials, returns tokens
5. Frontend stores tokens and user info in localStorage
6. User redirected to `/dashboard`

### Authenticated Requests
1. All API requests automatically include `Authorization: Bearer <token>` header
2. Backend validates token and processes request
3. If token expired, frontend should refresh using refresh token
4. If refresh token expired, user redirected to login

### Logout
1. User clicks logout button
2. Tokens cleared from localStorage
3. User redirected to login page

## Token Structure

### Access Token
- Type: Bearer JWT
- Expires: 30 minutes (configurable)
- Contains: user ID (`sub` claim) and token type
- Used for: Authenticating API requests

### Refresh Token
- Type: Bearer JWT
- Expires: 7 days (configurable)
- Contains: user ID (`sub` claim) and token type
- Used for: Obtaining new access tokens

## Security Considerations

1. **Passwords**: Hashed using bcrypt, never stored in plaintext
2. **Tokens**: Stored in localStorage (consider httpOnly cookies for production)
3. **Secret Key**: Must be changed in production (set via `SECRET_KEY` env var)
4. **HTTPS**: Use HTTPS in production to protect tokens in transit
5. **CORS**: Configured to allow credentials

## Database Migration

After deploying the changes, you need to:

1. Update the existing users table to add the password_hash column:
   ```sql
   ALTER TABLE users ADD COLUMN password_hash VARCHAR;
   ```

2. Or run migrations if using Alembic:
   ```bash
   alembic revision --autogenerate -m "add password_hash to users"
   alembic upgrade head
   ```

## Testing the System

### Using cURL

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "password": "testpassword123"
  }'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123"
  }'

# Get current user
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer <access_token>"

# Refresh token
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "<refresh_token>"
  }'
```

## Next Steps

1. **Database Migration**: Create and run migration to add password_hash column
2. **Install Dependencies**: Run `pip install -r requirements.txt` in backend and `npm install` in frontend
3. **Environment Setup**: Create `.env` file with required variables
4. **Testing**: Test registration, login, and protected endpoints
5. **Production**: Update secret key and consider using httpOnly cookies

## Troubleshooting

### 401 Unauthorized Error
- Check if token is being sent correctly in Authorization header
- Verify token hasn't expired
- Try refreshing the token using refresh_token endpoint

### Token Invalid Error
- Ensure SECRET_KEY is the same on backend
- Check token format is `Bearer <token>`
- Verify token isn't corrupted or partially copied

### CORS Errors
- Ensure frontend URL is in CORS_ORIGINS environment variable
- Check that `allow_credentials` is set to True in CORS middleware

### Password Hash Errors
- Make sure bcrypt is installed: `pip install bcrypt`
- Check password_hash column exists in users table
