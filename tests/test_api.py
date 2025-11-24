"""API endpoint tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test root endpoint returns API info."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Build-Report API"
    assert data["version"] == "2.0.0"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


# ============ Categories Tests ============

@pytest.mark.asyncio
async def test_get_categories_empty(client: AsyncClient):
    """Test getting categories when empty."""
    response = await client.get("/api/categories")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_category(client: AsyncClient, sample_category_data):
    """Test creating a category."""
    response = await client.post("/api/categories", json=sample_category_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == sample_category_data["name"]
    assert "id" in data


@pytest.mark.asyncio
async def test_create_duplicate_category(client: AsyncClient, sample_category_data):
    """Test creating duplicate category fails."""
    await client.post("/api/categories", json=sample_category_data)
    response = await client.post("/api/categories", json=sample_category_data)
    assert response.status_code == 400


# ============ Works Tests ============

@pytest.mark.asyncio
async def test_get_works_empty(client: AsyncClient):
    """Test getting works when empty."""
    response = await client.get("/api/works")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_work(client: AsyncClient, sample_work_data):
    """Test creating a work."""
    response = await client.post("/api/works", json=sample_work_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == sample_work_data["name"]
    assert data["category"] == sample_work_data["category"]
    assert data["balance"] == sample_work_data["balance"]
    assert "id" in data
    # Check VAT calculation
    assert "unit_cost_with_vat" in data
    assert data["unit_cost_with_vat"] == round(sample_work_data["unit_cost_without_vat"] * 1.2, 2)


@pytest.mark.asyncio
async def test_get_work_by_id(client: AsyncClient, sample_work_data):
    """Test getting a specific work."""
    # Create first
    create_response = await client.post("/api/works", json=sample_work_data)
    work_id = create_response.json()["id"]

    # Get by ID
    response = await client.get(f"/api/works/{work_id}")
    assert response.status_code == 200
    assert response.json()["id"] == work_id


@pytest.mark.asyncio
async def test_update_work(client: AsyncClient, sample_work_data):
    """Test updating a work."""
    # Create first
    create_response = await client.post("/api/works", json=sample_work_data)
    work_id = create_response.json()["id"]

    # Update
    update_data = {"name": "Updated Work Name", "balance": 200.0}
    response = await client.put(f"/api/works/{work_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Work Name"
    assert data["balance"] == 200.0


@pytest.mark.asyncio
async def test_add_balance_to_work(client: AsyncClient, sample_work_data):
    """Test adding balance to a work."""
    # Create first
    create_response = await client.post("/api/works", json=sample_work_data)
    work_id = create_response.json()["id"]
    initial_balance = create_response.json()["balance"]

    # Add balance
    response = await client.put(f"/api/works/{work_id}/add-balance", json={"amount": 50.0})
    assert response.status_code == 200
    assert response.json()["balance"] == initial_balance + 50.0


@pytest.mark.asyncio
async def test_delete_work(client: AsyncClient, sample_work_data):
    """Test deleting a work."""
    # Create first
    create_response = await client.post("/api/works", json=sample_work_data)
    work_id = create_response.json()["id"]

    # Delete
    response = await client.delete(f"/api/works/{work_id}")
    assert response.status_code == 200

    # Verify deleted
    get_response = await client.get(f"/api/works/{work_id}")
    assert get_response.status_code == 404


# ============ Materials Tests ============

@pytest.mark.asyncio
async def test_get_materials_empty(client: AsyncClient):
    """Test getting materials when empty."""
    response = await client.get("/api/materials")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_material(client: AsyncClient, sample_material_data):
    """Test creating a material."""
    response = await client.post("/api/materials", json=sample_material_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == sample_material_data["name"]
    assert data["quantity"] == sample_material_data["quantity"]


@pytest.mark.asyncio
async def test_add_quantity_to_material(client: AsyncClient, sample_material_data):
    """Test adding quantity to material."""
    # Create first
    create_response = await client.post("/api/materials", json=sample_material_data)
    material_id = create_response.json()["id"]
    initial_quantity = create_response.json()["quantity"]

    # Add quantity
    response = await client.put(
        f"/api/materials/{material_id}/add-quantity",
        json={"amount": 25.0, "performed_by": "Test User", "description": "Test addition"}
    )
    assert response.status_code == 200
    assert response.json()["quantity"] == initial_quantity + 25.0


# ============ Foremen Tests ============

@pytest.mark.asyncio
async def test_get_foremen_empty(client: AsyncClient):
    """Test getting foremen when empty."""
    response = await client.get("/api/foremen")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_foreman(client: AsyncClient, sample_foreman_data):
    """Test creating a foreman."""
    response = await client.post("/api/foremen", json=sample_foreman_data)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == sample_foreman_data["full_name"]
    assert data["position"] == sample_foreman_data["position"]


@pytest.mark.asyncio
async def test_update_foreman(client: AsyncClient, sample_foreman_data):
    """Test updating a foreman."""
    # Create first
    create_response = await client.post("/api/foremen", json=sample_foreman_data)
    foreman_id = create_response.json()["id"]

    # Update
    update_data = {"full_name": "Петр Петров", "is_active": False}
    response = await client.put(f"/api/foremen/{foreman_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Петр Петров"
    assert data["is_active"] == False


# ============ Reports Tests ============

@pytest.mark.asyncio
async def test_get_reports_empty(client: AsyncClient):
    """Test getting reports when empty."""
    response = await client.get("/api/reports/2024-01-01")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_accumulative_statement_empty(client: AsyncClient):
    """Test getting accumulative statement when empty."""
    response = await client.get("/api/accumulative-statement")
    assert response.status_code == 200
    assert response.json() == []


# ============ Auth Tests ============

@pytest.mark.asyncio
async def test_login_invalid_user(client: AsyncClient):
    """Test login with invalid credentials."""
    response = await client.post(
        "/api/site-login",
        json={"username": "nonexistent", "password": "wrong"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == False
