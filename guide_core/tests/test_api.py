"""
Integration tests for Django REST API endpoints.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from guide_core.models import ChatMessage, TourSession


class APIRoutesTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.session = TourSession.objects.create(title="Visite Florence", destination="Florence")

    def test_health_check(self):
        url = reverse('api-health')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('status'), 'healthy')
        self.assertTrue(response.data.get('geoapify_configured'))

    def test_mcp_manifest(self):
        url = reverse('api-mcp-manifest')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tools', response.data)
        self.assertGreaterEqual(len(response.data['tools']), 3)

    def test_sessions_crud(self):
        # List sessions
        list_url = reverse('api-sessions-list')
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        # Create session
        create_response = self.client.post(list_url, {"title": "Barcelone Express", "destination": "Barcelone"})
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        new_id = create_response.data['id']

        # Get detail
        detail_url = reverse('api-session-detail', kwargs={'pk': new_id})
        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data['destination'], "Barcelone")

        # Delete session
        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_geocode_endpoint(self):
        url = reverse('api-geo-geocode') + '?text=Paris'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('type'), 'FeatureCollection')

    def test_places_endpoint(self):
        url = reverse('api-geo-places') + '?text=Nice&categories=tourism.sights'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('type'), 'FeatureCollection')
