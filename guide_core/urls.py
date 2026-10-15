"""
URL routing for guide_core API endpoints.
"""

from django.urls import path
from .views import (
    ChatAPIView,
    GeoCodeAPIView,
    GeoPlacesAPIView,
    GeoRouteAPIView,
    HealthCheckAPIView,
    ItineraryListCreateView,
    MCPManifestAPIView,
    SavedPlaceListCreateView,
    SessionDetailView,
    SessionListCreateView,
)

urlpatterns = [
    path('health/', HealthCheckAPIView.as_view(), name='api-health'),
    path('chat/', ChatAPIView.as_view(), name='api-chat'),
    path('sessions/', SessionListCreateView.as_view(), name='api-sessions-list'),
    path('sessions/<uuid:pk>/', SessionDetailView.as_view(), name='api-session-detail'),
    path('geo/geocode/', GeoCodeAPIView.as_view(), name='api-geo-geocode'),
    path('geo/places/', GeoPlacesAPIView.as_view(), name='api-geo-places'),
    path('geo/route/', GeoRouteAPIView.as_view(), name='api-geo-route'),
    path('itineraries/', ItineraryListCreateView.as_view(), name='api-itineraries'),
    path('places/', SavedPlaceListCreateView.as_view(), name='api-saved-places'),
    path('mcp/manifest/', MCPManifestAPIView.as_view(), name='api-mcp-manifest'),
]
