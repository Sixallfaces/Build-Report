"""Tests for Pydantic models validation."""
import pytest
from pydantic import ValidationError

from apps.models.work import WorkCreate, WorkUpdate, WorkAddBalance
from apps.models.material import MaterialCreate, MaterialAddQuantity
from apps.models.category import CategoryCreate, CategoryUpdate
from apps.models.foreman import ForemanCreate, ForemanUpdate
from apps.models.auth import LoginRequest


class TestWorkModels:
    """Tests for Work models."""

    def test_work_create_valid(self):
        """Test valid WorkCreate."""
        work = WorkCreate(
            name="Test Work",
            category="Test Category",
            unit="шт",
            balance=100.0,
            project_total=500.0,
        )
        assert work.name == "Test Work"
        assert work.balance == 100.0
        assert work.is_active == True  # default

    def test_work_create_empty_name_fails(self):
        """Test WorkCreate with empty name fails."""
        with pytest.raises(ValidationError):
            WorkCreate(
                name="",
                category="Test",
                unit="шт",
            )

    def test_work_create_negative_balance_fails(self):
        """Test WorkCreate with negative balance fails."""
        with pytest.raises(ValidationError):
            WorkCreate(
                name="Test",
                category="Test",
                unit="шт",
                balance=-10.0,
            )

    def test_work_update_partial(self):
        """Test WorkUpdate with partial data."""
        update = WorkUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.category is None
        assert update.balance is None

    def test_work_add_balance(self):
        """Test WorkAddBalance model."""
        data = WorkAddBalance(amount=50.5)
        assert data.amount == 50.5


class TestMaterialModels:
    """Tests for Material models."""

    def test_material_create_valid(self):
        """Test valid MaterialCreate."""
        material = MaterialCreate(
            name="Test Material",
            category="Test Category",
            unit="кг",
            quantity=100.0,
        )
        assert material.name == "Test Material"
        assert material.is_active == True

    def test_material_add_quantity(self):
        """Test MaterialAddQuantity model."""
        data = MaterialAddQuantity(
            amount=25.0,
            performed_by="Test User",
            description="Test addition"
        )
        assert data.amount == 25.0
        assert data.performed_by == "Test User"


class TestCategoryModels:
    """Tests for Category models."""

    def test_category_create_valid(self):
        """Test valid CategoryCreate."""
        category = CategoryCreate(name="Test Category")
        assert category.name == "Test Category"

    def test_category_create_empty_fails(self):
        """Test CategoryCreate with empty name fails."""
        with pytest.raises(ValidationError):
            CategoryCreate(name="")

    def test_category_update(self):
        """Test CategoryUpdate model."""
        update = CategoryUpdate(name="New Name")
        assert update.name == "New Name"


class TestForemanModels:
    """Tests for Foreman models."""

    def test_foreman_create_valid(self):
        """Test valid ForemanCreate."""
        foreman = ForemanCreate(
            full_name="Иван Иванов",
            position="Бригадир",
        )
        assert foreman.full_name == "Иван Иванов"
        assert foreman.is_active == True

    def test_foreman_create_short_name_fails(self):
        """Test ForemanCreate with short name fails."""
        with pytest.raises(ValidationError):
            ForemanCreate(
                full_name="И",
                position="Бригадир",
            )

    def test_foreman_update_partial(self):
        """Test ForemanUpdate with partial data."""
        update = ForemanUpdate(is_active=False)
        assert update.full_name is None
        assert update.is_active == False


class TestAuthModels:
    """Tests for Auth models."""

    def test_login_request_valid(self):
        """Test valid LoginRequest."""
        login = LoginRequest(
            username="admin",
            password="password123"
        )
        assert login.username == "admin"
        assert login.password == "password123"

    def test_login_request_empty_username_fails(self):
        """Test LoginRequest with empty username fails."""
        with pytest.raises(ValidationError):
            LoginRequest(
                username="",
                password="password"
            )
