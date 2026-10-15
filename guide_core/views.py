"""
API Views for Smart Tour Guide AI
Endpoints for chat orchestration, session management, Geoapify spatial operations,
itinerary saving, and MCP tool discovery.
"""

import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from .models import ChatMessage, SavedItinerary, SavedPlace, TourSession
from .serializers import (
    ChatMessageSerializer,
    ChatRequestSerializer,
    RouteRequestSerializer,
    SavedItinerarySerializer,
    SavedPlaceSerializer,
    TourSessionSerializer,
)
from .services.agent_service import TourGuideAgent
from .services.geoapify_mcp import GeoapifyMCPClient
from .services.geoapify_service import GeoapifyService

logger = logging.getLogger(__name__)


class HealthCheckAPIView(APIView):
    """Healthcheck endpoint for backend readiness and configuration check."""
    def get(self, request):
        groq_configured = bool(getattr(settings, 'GROQ_API_KEY', ''))
        geo_configured = bool(getattr(settings, 'GEOAPIFY_API_KEY', ''))
        return Response({
            "status": "healthy",
            "service": "Smart Tour Guide AI Backend",
            "version": "1.0.0",
            "groq_configured": groq_configured,
            "geoapify_configured": geo_configured,
            "model": getattr(settings, 'GROQ_MODEL', 'qwen/qwen3.8-27b'),
        }, status=status.HTTP_200_OK)


class ChatAPIView(APIView):
    """
    Primary conversational endpoint.
    Orchestrates the Grok/Groq AI agent, Geoapify MCP tool calling,
    session memory, and GeoJSON synthesis.
    """
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        session_id = data.get('session_id')
        message = data.get('message')
        user_location = data.get('user_location')
        destination = data.get('destination')

        # Retrieve or create session
        session = None
        if session_id:
            try:
                session = TourSession.objects.get(id=session_id)
            except TourSession.DoesNotExist:
                session = None

        if not session:
            title = f"Visite de {destination}" if destination else "Nouvelle visite"
            session = TourSession.objects.create(title=title, destination=destination or "")

        agent = TourGuideAgent()
        result = agent.process_message(
            session=session,
            user_message=message,
            user_location=user_location,
            destination=destination
        )

        return Response(result, status=status.HTTP_200_OK)


class SessionListCreateView(APIView):
    """Lists conversation sessions or creates a new tour session."""
    def get(self, request):
        sessions = TourSession.objects.all().order_by('-updated_at')
        serializer = TourSessionSerializer(sessions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = TourSessionSerializer(data=request.data)
        if serializer.is_valid():
            session = serializer.save()
            return Response(TourSessionSerializer(session).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SessionDetailView(APIView):
    """Retrieves session details with full message history, or deletes session."""
    def get(self, request, pk):
        try:
            session = TourSession.objects.get(pk=pk)
        except TourSession.DoesNotExist:
            return Response({"error": "Session introuvable"}, status=status.HTTP_404_NOT_FOUND)

        session_data = TourSessionSerializer(session).data
        messages = session.messages.all().order_by('timestamp')
        session_data['messages'] = ChatMessageSerializer(messages, many=True).data
        return Response(session_data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        try:
            session = TourSession.objects.get(pk=pk)
            session.delete()
            return Response({"message": "Session supprimée avec succès"}, status=status.HTTP_204_NO_CONTENT)
        except TourSession.DoesNotExist:
            return Response({"error": "Session introuvable"}, status=status.HTTP_404_NOT_FOUND)


class GeoCodeAPIView(APIView):
    """Direct geocoding endpoint returning normalized GeoJSON FeatureCollection."""
    def get(self, request):
        text = request.query_params.get('text', '').strip()
        if not text:
            return Response({"type": "FeatureCollection", "features": []}, status=status.HTTP_200_OK)

        limit = int(request.query_params.get('limit', 5))
        lang = request.query_params.get('lang', 'fr')

        geo_service = GeoapifyService()
        geojson = geo_service.geocode(text=text, limit=limit, lang=lang)
        return Response(geojson, status=status.HTTP_200_OK)


class GeoPlacesAPIView(APIView):
    """Direct POIs search by category, coordinates, radius, or city."""
    def get(self, request):
        text = request.query_params.get('text')
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        categories_param = request.query_params.get('categories')
        radius = int(request.query_params.get('radius', 3000))
        limit = int(request.query_params.get('limit', 20))
        lang = request.query_params.get('lang', 'fr')

        categories = categories_param.split(',') if categories_param else None
        lat_f = float(lat) if lat is not None else None
        lon_f = float(lon) if lon is not None else None

        geo_service = GeoapifyService()
        geojson = geo_service.search_places(
            categories=categories,
            lat=lat_f,
            lon=lon_f,
            radius_meters=radius,
            text=text,
            limit=limit,
            lang=lang,
        )
        return Response(geojson, status=status.HTTP_200_OK)


class GeoRouteAPIView(APIView):
    """Calculates route between waypoints with turn-by-turn steps."""
    def post(self, request):
        serializer = RouteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        waypoints = serializer.validated_data['waypoints']
        mode = serializer.validated_data.get('mode', 'walk')

        geo_service = GeoapifyService()
        route_geojson = geo_service.calculate_route(waypoints=waypoints, mode=mode)
        return Response(route_geojson, status=status.HTTP_200_OK)


class ItineraryListCreateView(APIView):
    """Lists or saves generated travel itineraries."""
    def get(self, request):
        itineraries = SavedItinerary.objects.all().order_by('-created_at')
        serializer = SavedItinerarySerializer(itineraries, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SavedItinerarySerializer(data=request.data)
        if serializer.is_valid():
            itinerary = serializer.save()
            return Response(SavedItinerarySerializer(itinerary).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SavedPlaceListCreateView(APIView):
    """Lists or bookmarks individual POIs."""
    def get(self, request):
        places = SavedPlace.objects.all().order_by('-created_at')
        serializer = SavedPlaceSerializer(places, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SavedPlaceSerializer(data=request.data)
        if serializer.is_valid():
            place = serializer.save()
            return Response(SavedPlaceSerializer(place).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MCPManifestAPIView(APIView):
    """Provides standard MCP tool manifest for inspection or external clients."""
    def get(self, request):
        mcp_client = GeoapifyMCPClient()
        manifest = mcp_client.get_tools_manifest()
        return Response({
            "protocol": "Model Context Protocol",
            "version": "2024-11-05",
            "server": "geoapify-mcp-server",
            "tools": manifest
        }, status=status.HTTP_200_OK)
