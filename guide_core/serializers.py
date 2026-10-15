"""
Serializers for Smart Tour Guide AI backend models and API requests.
"""

from rest_framework import serializers
from .models import ChatMessage, SavedItinerary, SavedPlace, TourSession


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'session', 'role', 'content', 'metadata', 'timestamp']
        read_only_fields = ['id', 'timestamp']


class TourSessionSerializer(serializers.ModelSerializer):
    messages_count = serializers.IntegerField(source='messages.count', read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = TourSession
        fields = [
            'id', 'title', 'destination', 'center_lat', 'center_lon',
            'created_at', 'updated_at', 'messages_count', 'last_message'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_last_message(self, obj):
        last = obj.messages.order_by('-timestamp').first()
        if last:
            return {
                "role": last.role,
                "content": last.content[:100],
                "timestamp": last.timestamp
            }
        return None


class SavedItinerarySerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedItinerary
        fields = [
            'id', 'session', 'title', 'destination', 'duration_type',
            'stops_data', 'route_geojson', 'total_distance_meters',
            'total_time_seconds', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SavedPlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedPlace
        fields = [
            'id', 'session', 'place_id', 'name', 'category',
            'address', 'lat', 'lon', 'details', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ChatRequestSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(required=False, allow_null=True)
    message = serializers.CharField(required=True)
    user_location = serializers.DictField(required=False, allow_null=True)
    destination = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class RouteRequestSerializer(serializers.Serializer):
    waypoints = serializers.ListField(
        child=serializers.DictField(),
        min_length=2,
        required=True
    )
    mode = serializers.ChoiceField(
        choices=['walk', 'bicycle', 'drive'],
        default='walk',
        required=False
    )
