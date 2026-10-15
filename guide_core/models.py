import uuid
from django.db import models


class TourSession(models.Model):
    """Represents a conversation session for exploring destinations and tours."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, default="Exploration culturelle")
    destination = models.CharField(max_length=255, blank=True, default="")
    center_lat = models.FloatField(null=True, blank=True)
    center_lon = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} ({self.destination or 'Sans destination'})"


class ChatMessage(models.Model):
    """Stores user queries, AI responses, and associated GeoJSON/itinerary data."""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
        ('tool', 'Tool'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(TourSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    # metadata stores GeoJSON features, recommended POIs, route geometries, audio narration, and tool logs
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"[{self.role}] {self.content[:40]}..."


class SavedItinerary(models.Model):
    """Structured travel itinerary with ordered waypoints, route geometry, and timing."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(TourSession, on_delete=models.CASCADE, related_name='itineraries', null=True, blank=True)
    title = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    duration_type = models.CharField(max_length=50, default="1_day")
    stops_data = models.JSONField(default=list)  # list of stops with name, lat, lon, time, notes
    route_geojson = models.JSONField(default=dict)  # GeoJSON FeatureCollection or Feature (LineString)
    total_distance_meters = models.FloatField(default=0.0)
    total_time_seconds = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.destination}"


class SavedPlace(models.Model):
    """Points of interest bookmarked by the user."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(TourSession, on_delete=models.CASCADE, related_name='saved_places', null=True, blank=True)
    place_id = models.CharField(max_length=255, blank=True, default="")
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True, default="tourism")
    address = models.TextField(blank=True, default="")
    lat = models.FloatField()
    lon = models.FloatField()
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.category})"
