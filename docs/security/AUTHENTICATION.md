# Authentication

**JWT Tokens, API Keys, and Validation**

---

## 🔐 Overview

Omni2 uses **JWT (JSON Web Tokens)** for user authentication and **API keys** for service-to-service communication.

---

## JWT Authentication

### Token Structure

```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "123",
    "email": "user@company.com",
    "role": "admin",
    "iat": 1706284800,
    "exp": 1706288400
  }
}
```

### Token Lifecycle

1. **Login** → Generate JWT (1 hour expiration)
2. **Storage** → Frontend stores in localStorage
3. **Validation** → Traefik validates every request
4. **Expiration** → User must re-login after 1 hour

---

## API Key Authentication

### Format
```
ak_1234567890abcdef1234567890abcdef
```

### Use Cases
- Server-to-server communication
- CLI tools
- Long-lived access

---

## Security Best Practices

- ✅ Short-lived tokens (1 hour)
- ✅ Strong SECRET_KEY (32+ characters)
- ✅ HTTPS only in production
- ✅ httpOnly cookies (recommended)

**[Back to Security Overview](./SECURITY_OVERVIEW)**
