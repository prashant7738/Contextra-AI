# Authentication API Reference

Complete reference for all authentication endpoints and usage examples.

## Base URL
```
http://localhost:8000
```

## Authentication Header Format
```
Authorization: Bearer <access_token>
```

---

## Endpoints

### 1. Register User

**Register a new user account**

```http
POST /auth/register
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response (201 Created):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors:**
- `400 Bad Request` - Email already registered
- `422 Unprocessable Entity` - Invalid input

**cURL Example:**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "password": "securepassword123"
  }'
```

---

### 2. Login User

**Authenticate with email and password**

```http
POST /auth/login
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors:**
- `401 Unauthorized` - Invalid email or password

**cURL Example:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "securepassword123"
  }'
```

---

### 3. Refresh Token

**Get a new access token using refresh token**

```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors:**
- `401 Unauthorized` - Invalid or expired refresh token

**cURL Example:**
```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

---

### 4. Get Current User

**Get information about the authenticated user**

```http
GET /auth/me
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com"
}
```

**Errors:**
- `401 Unauthorized` - Missing or invalid token

**cURL Example:**
```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## Token Details

### Access Token
- **Purpose**: Used to authenticate API requests
- **Expiration**: 30 minutes (configurable)
- **Type**: Bearer JWT
- **Claims**: 
  - `sub`: User ID
  - `type`: "access"
  - `exp`: Expiration timestamp

### Refresh Token
- **Purpose**: Used to obtain new access tokens
- **Expiration**: 7 days (configurable)
- **Type**: Bearer JWT
- **Claims**:
  - `sub`: User ID
  - `type`: "refresh"
  - `exp`: Expiration timestamp

---

## Common Workflows

### Complete Login Flow

```bash
# 1. Register new user
REGISTER=$(curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "password": "securepassword123"
  }')

# Extract access token
ACCESS_TOKEN=$(echo $REGISTER | jq -r '.access_token')

# 2. Use access token to get user info
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 3. When token expires, refresh it
REFRESH_TOKEN=$(echo $REGISTER | jq -r '.refresh_token')

NEW_TOKENS=$(curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}")

NEW_ACCESS=$(echo $NEW_TOKENS | jq -r '.access_token')
```

### Login and Use API

```bash
# 1. Login
LOGIN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "securepassword123"
  }')

ACCESS_TOKEN=$(echo $LOGIN | jq -r '.access_token')

# 2. Make authenticated requests
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 3. Get user list (no auth needed)
curl -X GET http://localhost:8000/users/
```

---

## Frontend Usage Examples

### Using AuthService

```typescript
import { AuthService } from '@/utils/auth';

// Store tokens
AuthService.setTokens({
  access_token: 'eyJh...',
  refresh_token: 'eyJh...',
  token_type: 'bearer'
});

// Get tokens
const token = AuthService.getAccessToken();
const refreshToken = AuthService.getRefreshToken();

// Store user info
AuthService.setCurrentUser({
  id: 1,
  name: 'John',
  email: 'john@example.com'
});

// Get user info
const user = AuthService.getCurrentUser();

// Check if authenticated
if (AuthService.isAuthenticated()) {
  // User is logged in
}

// Get auth header for requests
const headers = AuthService.getAuthHeader();
// Returns: { Authorization: 'Bearer <token>' }

// Logout
AuthService.clearTokens();
```

### Using API Client

```typescript
import { apiClient } from '@/utils/api';

// Register
const registerResponse = await apiClient.register(
  'John Doe',
  'john@example.com',
  'securepassword123'
);

// Login
const loginResponse = await apiClient.login(
  'john@example.com',
  'securepassword123'
);

// Refresh token
const refreshResponse = await apiClient.refreshToken(refreshToken);

// Get current user
const meResponse = await apiClient.getMe();

// Generic requests (auth header auto-injected)
const response = await apiClient.get('/users');
```

---

## Error Handling

### Common Error Responses

#### 401 Unauthorized
```json
{
  "detail": "Invalid email or password"
}
```
**Causes**: Wrong credentials, expired token, missing token

#### 400 Bad Request
```json
{
  "detail": "Email already registered"
}
```
**Causes**: Duplicate email, invalid input

#### 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```
**Causes**: Missing or invalid fields

---

## Security Best Practices

1. **Never expose tokens in logs or URLs**
   ```bash
   # Bad: Log with token visible
   echo "Token: $ACCESS_TOKEN"
   
   # Good: Use masked token
   echo "Token: ${ACCESS_TOKEN:0:10}..."
   ```

2. **Always use HTTPS in production**
   ```
   https://api.example.com/auth/login
   ```

3. **Store tokens securely on frontend**
   - Current: localStorage (good for development)
   - Better: httpOnly cookies
   - Best: httpOnly cookies + CSRF protection

4. **Set strong SECRET_KEY**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

5. **Rotate refresh tokens**
   - Consider invalidating old refresh tokens after issue
   - Store token version in database

6. **Implement rate limiting**
   - Limit /auth/register and /auth/login endpoints
   - Prevent brute force attacks

---

## Testing with Swagger UI

1. Open `http://localhost:8000/docs`
2. Authorize by filling in token field
3. Try endpoints directly from browser
4. See live documentation

---

## Integration Examples

### With Python Requests

```python
import requests

# Register
response = requests.post(
    'http://localhost:8000/auth/register',
    json={
        'name': 'John Doe',
        'email': 'john@example.com',
        'password': 'securepassword123'
    }
)
data = response.json()
access_token = data['access_token']

# Make authenticated request
headers = {'Authorization': f'Bearer {access_token}'}
response = requests.get(
    'http://localhost:8000/auth/me',
    headers=headers
)
print(response.json())
```

### With JavaScript/Node.js

```javascript
// Register
const registerRes = await fetch('http://localhost:8000/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'John Doe',
    email: 'john@example.com',
    password: 'securepassword123'
  })
});

const data = await registerRes.json();
const accessToken = data.access_token;

// Make authenticated request
const meRes = await fetch('http://localhost:8000/auth/me', {
  headers: { 'Authorization': `Bearer ${accessToken}` }
});
console.log(await meRes.json());
```

---

## Troubleshooting

### Issue: "Invalid Token"
- Token format must be: `Bearer <token>`
- Check token hasn't expired
- Verify token was copied completely (no extra spaces)

### Issue: "Email Already Registered"
- User already exists
- Use login endpoint instead
- Or use different email for testing

### Issue: "Missing Authorization Header"
- Add header: `Authorization: Bearer <token>`
- Check header name is exactly "Authorization"

### Issue: Token Expires During Request
- Implement token refresh before expiry
- Or catch 401 and refresh automatically
- See client implementation in frontend code

---

## API Statistics

| Endpoint | Method | Auth | Rate |
|----------|--------|------|------|
| /auth/register | POST | No | No limit |
| /auth/login | POST | No | No limit |
| /auth/refresh | POST | No | No limit |
| /auth/me | GET | Yes | No limit |

---

## Support

For issues or questions:
- Check `AUTH_SETUP.md` for detailed setup
- Check `QUICK_START.md` for quick reference
- Review source code comments
- Open backend at `/docs` for interactive testing
