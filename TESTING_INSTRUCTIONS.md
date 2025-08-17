# EduStream Testing Instructions

## Prerequisites
- Docker and Docker Compose installed
- Postman or any API testing tool
- Web browser for Swagger UI

## 1. Setting Up the Environment

### Step 1: Clone and Navigate
```bash
cd /path/to/edustream_backend
```

### Step 2: Start Docker Services
```bash
docker-compose up -d
```

This will start:
- Django application on http://localhost:8001
- PostgreSQL database on localhost:5433
- Redis on localhost:6380

### Step 3: Create Superuser
```bash
docker-compose exec web python manage.py createsuperuser
```

Follow the prompts to create an admin user with email and password.

### Step 4: Access Admin Panel
Visit http://localhost:8001/admin/ and login with superuser credentials.

## 2. API Testing Workflow

### Access API Documentation
1. Swagger UI: http://localhost:8001/swagger/
2. ReDoc: http://localhost:8001/redoc/

### Testing User Registration and Authentication

#### 1. Register a Student
```http
POST /api/auth/register/
Content-Type: application/json

{
    "username": "student1",
    "email": "student1@example.com",
    "password": "SecurePass123",
    "password_confirm": "SecurePass123",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+919876543210"
}
```

Expected Response:
```json
{
    "user": {
        "id": 1,
        "username": "student1",
        "email": "student1@example.com",
        "role": "student",
        ...
    },
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### 2. Login
```http
POST /api/auth/login/
Content-Type: application/json

{
    "email": "student1@example.com",
    "password": "SecurePass123"
}
```

Save the `access` token for authenticated requests.

#### 3. Create Teacher Account (Admin Only)
First, login as admin, then:

```http
POST /api/auth/admin/create-teacher/
Authorization: Bearer <admin_access_token>
Content-Type: application/json

{
    "username": "teacher1",
    "email": "teacher1@example.com",
    "password": "TeacherPass123",
    "first_name": "Jane",
    "last_name": "Smith",
    "phone_number": "+919876543211"
}
```

### Testing Course Management

#### 1. Create a Course (Teacher)
Login as teacher first, then:

```http
POST /api/courses/create/
Authorization: Bearer <teacher_access_token>
Content-Type: application/json

{
    "name": "Introduction to VR Development",
    "description": "Learn the basics of VR development using Unity and WebXR",
    "price": 4999.00,
    "category": "Technology",
    "duration_weeks": 8
}
```

#### 2. List All Courses (Public)
```http
GET /api/courses/
```

Query parameters:
- `?search=VR` - Search in name, description, category
- `?category=Technology` - Filter by category
- `?teacher=1` - Filter by teacher ID

#### 3. Get Course Details
```http
GET /api/courses/<course-slug>/
```

### Testing Enrollment and Payment

#### 1. Create Payment Order (Student)
```http
POST /api/payments/create-order/
Authorization: Bearer <student_access_token>
Content-Type: application/json

{
    "course_id": 1
}
```

Response:
```json
{
    "order_id": "order_xxx",
    "amount": 499900,
    "currency": "INR",
    "key": "rzp_test_xxx"
}
```

#### 2. Verify Payment (Student)
After completing payment on frontend:

```http
POST /api/payments/verify/
Authorization: Bearer <student_access_token>
Content-Type: application/json

{
    "razorpay_order_id": "order_xxx",
    "razorpay_payment_id": "pay_xxx",
    "razorpay_signature": "signature_xxx"
}
```

### Testing WebSocket Connection

#### Test WebRTC Signaling
Use a WebSocket client to connect:

```
ws://localhost:8001/ws/signal/room_test123/
```

Send authentication with JWT token in connection parameters.

Sample messages:
```json
// Offer
{
    "type": "offer",
    "offer": {
        "type": "offer",
        "sdp": "..."
    },
    "target_id": "user_id"
}

// Answer
{
    "type": "answer",
    "answer": {
        "type": "answer",
        "sdp": "..."
    },
    "target_id": "user_id"
}

// ICE Candidate
{
    "type": "ice-candidate",
    "candidate": {
        "candidate": "...",
        "sdpMLineIndex": 0,
        "sdpMid": "..."
    }
}
```

## 3. Common Test Scenarios

### Scenario 1: Complete Student Journey
1. Register as student
2. Browse courses
3. Select a course
4. Create payment order
5. Complete payment (simulate)
6. Verify payment
7. Check enrollment status

### Scenario 2: Teacher Course Management
1. Admin creates teacher account
2. Teacher logs in
3. Teacher creates a course
4. Teacher updates course details
5. Teacher views enrolled students

### Scenario 3: Live Class Flow
1. Teacher schedules a class
2. Students receive notification (when implemented)
3. Teacher starts WebRTC session
4. Students join the session
5. WebRTC signaling exchange

## 4. Database Verification

### Check Database Records
```bash
docker-compose exec db psql -U edustream_user -d edustream_db

# List all users
SELECT id, email, role FROM users;

# List all courses
SELECT id, name, teacher_id, price FROM courses;

# List enrollments
SELECT * FROM enrollments WHERE payment_status = 'completed';
```

## 5. Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure all Docker containers are running: `docker-compose ps`
   - Check logs: `docker-compose logs -f web`

2. **Authentication Errors**
   - Verify JWT token is included in headers
   - Check token expiration (1 hour by default)
   - Refresh token if needed

3. **WebSocket Connection Failed**
   - Ensure Redis is running
   - Check Django Channels configuration
   - Verify user has access to the room

### Viewing Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f db
docker-compose logs -f redis
```

### Resetting Database
```bash
docker-compose down -v
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

## 6. Performance Testing

### Load Testing with Locust
Create a `locustfile.py`:
```python
from locust import HttpUser, task, between

class EduStreamUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def list_courses(self):
        self.client.get("/api/courses/")
    
    @task
    def view_course(self):
        self.client.get("/api/courses/introduction-to-vr-development/")
```

Run: `locust -f locustfile.py --host=http://localhost:8001`

## 7. Security Testing

### Test Authorization
1. Try accessing teacher endpoints as student
2. Try accessing admin endpoints as teacher
3. Verify course update only works for course owner
4. Test payment verification with invalid signature

### Input Validation
1. Test with invalid email formats
2. Test with short passwords
3. Test with missing required fields
4. Test with invalid course IDs

## Notes for Razorpay Testing
- Use Razorpay test mode credentials
- Test card: 4111 1111 1111 1111
- Any future date for expiry
- Any 3-digit CVV

For production testing, update Razorpay credentials in environment variables.