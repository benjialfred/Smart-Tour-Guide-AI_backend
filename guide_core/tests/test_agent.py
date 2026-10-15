"""
Unit tests for the Tour Guide Agent logic, memory, and spatial extraction.
"""

from django.test import TestCase
from guide_core.models import ChatMessage, TourSession
from guide_core.services.agent_service import TourGuideAgent


class TourGuideAgentTest(TestCase):
    def setUp(self):
        self.session = TourSession.objects.create(title="Séjour à Venise", destination="Venise")
        self.agent = TourGuideAgent()

    def test_audio_narration_cleaning(self):
        raw_markdown = "### 🏛️ Visite du **Palais des Doges**\nC'est un *chef-d'œuvre* d'art gothique vénitien [lien](http://example.com)."
        cleaned = self.agent._generate_audio_narration(raw_markdown)
        self.assertNotIn("###", cleaned)
        self.assertNotIn("**", cleaned)
        self.assertNotIn("*", cleaned)
        self.assertIn("Palais des Doges", cleaned)
        self.assertIn("chef-d'œuvre", cleaned)

    def test_extract_itinerary(self):
        features = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [12.338, 45.434]},
                "properties": {"name": "Place Saint-Marc", "category": "monument", "formatted": "Piazza San Marco"}
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [12.335, 45.437]},
                "properties": {"name": "Pont du Rialto", "category": "monument", "formatted": "Ponte di Rialto"}
            }
        ]
        stops = self.agent._extract_itinerary(features, "Visite à Venise")
        self.assertEqual(len(stops), 2)
        self.assertEqual(stops[0]['name'], "Place Saint-Marc")
        self.assertEqual(stops[1]['name'], "Pont du Rialto")
        self.assertEqual(stops[0]['step'], 1)
        self.assertEqual(stops[1]['step'], 2)

    def test_conversation_memory_loading(self):
        ChatMessage.objects.create(session=self.session, role='user', content='Bonjour guide')
        ChatMessage.objects.create(session=self.session, role='assistant', content='Bienvenue à Venise !')
        ChatMessage.objects.create(session=self.session, role='user', content='Quels musées voir ?')

        history = self.agent._load_conversation_history(self.session, limit=2)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['content'], 'Bienvenue à Venise !')
        self.assertEqual(history[1]['content'], 'Quels musées voir ?')
