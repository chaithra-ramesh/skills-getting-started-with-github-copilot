"""
Tests for the Mergington High School Activities API
"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state
    for name, details in original_activities.items():
        activities[name]["participants"] = details["participants"]


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_200(self, client):
        """Test that GET /activities returns status 200"""
        response = client.get("/activities")
        assert response.status_code == 200
    
    def test_get_activities_returns_json(self, client):
        """Test that GET /activities returns JSON"""
        response = client.get("/activities")
        data = response.json()
        assert isinstance(data, dict)
    
    def test_get_activities_contains_all_activities(self, client):
        """Test that all activities are returned"""
        response = client.get("/activities")
        data = response.json()
        
        # Should have the expected activities
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Basketball Team" in data
    
    def test_activity_structure(self, client):
        """Test that each activity has the required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client, reset_activities):
        """Test successful signup"""
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
    
    def test_signup_adds_participant(self, client, reset_activities):
        """Test that signup actually adds participant to the activity"""
        email = "newstudent@mergington.edu"
        initial_count = len(activities["Chess Club"]["participants"])
        
        client.post(
            "/activities/Chess%20Club/signup",
            params={"email": email}
        )
        
        assert len(activities["Chess Club"]["participants"]) == initial_count + 1
        assert email in activities["Chess Club"]["participants"]
    
    def test_signup_duplicate_student_fails(self, client, reset_activities):
        """Test that duplicate signup returns error"""
        email = "michael@mergington.edu"  # Already in Chess Club
        
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": email}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Fake%20Activity/signup",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_signup_multiple_different_activities(self, client, reset_activities):
        """Test that a student can sign up for multiple different activities"""
        email = "multistudent@mergington.edu"
        
        # Sign up for Chess Club
        response1 = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Sign up for Programming Class
        response2 = client.post(
            "/activities/Programming%20Class/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify both signups were successful
        assert email in activities["Chess Club"]["participants"]
        assert email in activities["Programming Class"]["participants"]


class TestUnregister:
    """Tests for POST /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregister"""
        email = "michael@mergington.edu"  # Already in Chess Club
        
        response = client.post(
            "/activities/Chess%20Club/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
    
    def test_unregister_removes_participant(self, client, reset_activities):
        """Test that unregister actually removes participant"""
        email = "michael@mergington.edu"
        initial_count = len(activities["Chess Club"]["participants"])
        
        client.post(
            "/activities/Chess%20Club/unregister",
            params={"email": email}
        )
        
        assert len(activities["Chess Club"]["participants"]) == initial_count - 1
        assert email not in activities["Chess Club"]["participants"]
    
    def test_unregister_nonexistent_student(self, client, reset_activities):
        """Test unregister for student not in activity"""
        response = client.post(
            "/activities/Chess%20Club/unregister",
            params={"email": "notamember@mergington.edu"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"].lower()
    
    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregister from non-existent activity"""
        response = client.post(
            "/activities/Fake%20Activity/unregister",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_signup_then_unregister(self, client, reset_activities):
        """Test full cycle: signup then unregister"""
        email = "cycletest@mergington.edu"
        activity = "Basketball Team"
        
        # Sign up
        response1 = client.post(
            f"/activities/{activity.replace(' ', '%20')}/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        assert email in activities[activity]["participants"]
        
        # Unregister
        response2 = client.post(
            f"/activities/{activity.replace(' ', '%20')}/unregister",
            params={"email": email}
        )
        assert response2.status_code == 200
        assert email not in activities[activity]["participants"]


class TestRoot:
    """Tests for root endpoint"""
    
    def test_root_redirects(self, client):
        """Test that root endpoint redirects to static index"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]
