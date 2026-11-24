# -*- coding: utf-8 -*-
"""What the favorites manager dialog asks of FavoritesService for global favorites and duplicates."""
import pytest

from core.domain.favorites_manager import FavoritesManager
from core.services.favorites_service import FavoritesService

pytestmark = pytest.mark.unit


@pytest.fixture
def service(tmp_path):
    svc = FavoritesService(FavoritesManager())
    svc.set_database(str(tmp_path / "favorites.sqlite"), "11111111-2222-3333-4444-555555555555")
    svc._favorites_manager.set_current_user("alice")
    return svc


def test_the_service_tells_who_owns_new_favorites(service):
    assert service.get_current_user() == "alice"


def test_a_global_favorite_is_removed_through_the_service(service):
    fav_id = service.add_favorite("Roads", "TRUE")
    global_id = service.copy_to_global(fav_id)
    assert [f.id for f in service.get_global_favorites()] == [global_id]

    assert service.remove_global_favorite(global_id) is True

    assert service.get_global_favorites() == []
    assert service.get_favorite(fav_id) is not None


def test_a_duplicate_keeps_the_layer_id(service):
    fav_id = service.add_favorite("Roads", "TRUE", layer_name="roads", layer_id="roads_123")
    copy_id = service.add_favorite("Roads (copy)", "TRUE", layer_name="roads", layer_id="roads_123")
    assert service.get_favorite(copy_id).layer_id == service.get_favorite(fav_id).layer_id == "roads_123"
