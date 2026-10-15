"""
Unit and integration tests for Geoapify Service and MCP client.
"""

from django.test import TestCase
from guide_core.services.geoapify_service import GeoapifyService
from guide_core.services.geoapify_mcp import GeoapifyMCPClient


class GeoapifyServiceTest(TestCase):
    def setUp(self):
        self.service = GeoapifyService()
        self.mcp_client = GeoapifyMCPClient(service=self.service)

    def test_category_classification(self):
        self.assertEqual(self.service._classify_category(['tourism.sights.castle'], 'poi'), 'monument')
        self.assertEqual(self.service._classify_category(['catering.restaurant.italian'], 'poi'), 'food')
        self.assertEqual(self.service._classify_category(['leisure.park'], 'poi'), 'nature')
        self.assertEqual(self.service._classify_category(['commercial.shopping_mall'], 'poi'), 'shopping')
        self.assertEqual(self.service._classify_category(['unknown.category'], 'custom'), 'custom')

    def test_normalize_geojson_structure(self):
        raw_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [2.2945, 48.8584]
                    },
                    "properties": {
                        "name": "Tour Eiffel",
                        "categories": ["tourism.sights", "heritage"],
                        "formatted": "Champ de Mars, 5 Av. Anatole France, 75007 Paris",
                        "place_id": "poi_123"
                    }
                }
            ]
        }
        normalized = self.service._normalize_geojson(raw_data, default_category='poi')
        self.assertEqual(normalized['type'], 'FeatureCollection')
        self.assertEqual(len(normalized['features']), 1)
        feat = normalized['features'][0]
        self.assertEqual(feat['properties']['name'], 'Tour Eiffel')
        self.assertEqual(feat['properties']['category'], 'monument')
        self.assertEqual(feat['properties']['lat'], 48.8584)
        self.assertEqual(feat['properties']['lon'], 2.2945)

    def test_normalize_route_geojson(self):
        raw_route = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[2.2945, 48.8584], [2.2950, 48.8590]]
                    },
                    "properties": {
                        "distance": 1250,
                        "time": 900,
                        "legs": [
                            {
                                "steps": [
                                    {"instruction": {"text": "Prenez l'avenue Anatole France"}, "distance": 200, "time": 150}
                                ]
                            }
                        ]
                    }
                }
            ]
        }
        waypoints = [{'lat': 48.8584, 'lon': 2.2945}, {'lat': 48.8590, 'lon': 2.2950}]
        route_res = self.service._normalize_route_geojson(raw_route, mode='walk', waypoints=waypoints)
        self.assertEqual(len(route_res['features']), 1)
        props = route_res['features'][0]['properties']
        self.assertTrue(props['is_route'])
        self.assertEqual(props['distance_meters'], 1250)
        self.assertEqual(props['distance_km'], 1.25)
        self.assertEqual(props['time_minutes'], 15.0)
        self.assertEqual(len(props['steps']), 1)

    def test_mcp_manifest_definition(self):
        tools = self.mcp_client.get_tools_manifest()
        tool_names = [t['name'] for t in tools]
        self.assertIn('geoapify_geocode', tool_names)
        self.assertIn('geoapify_places_search', tool_names)
        self.assertIn('geoapify_routing', tool_names)
        self.assertIn('geoapify_place_details', tool_names)

        # Verify LLM translation format
        llm_tools = self.mcp_client.to_llm_tools()
        self.assertEqual(len(llm_tools), len(tools))
        self.assertEqual(llm_tools[0]['type'], 'function')
        self.assertTrue('name' in llm_tools[0]['function'])

    def test_live_geoapify_geocode_if_key_present(self):
        """Live verification using provided Geoapify API key."""
        if self.service.api_key:
            res = self.service.geocode(text="Colosseum Rome", limit=1)
            self.assertEqual(res['type'], 'FeatureCollection')
            if res.get('features'):
                feat = res['features'][0]
                self.assertIn('coordinates', feat['geometry'])
                self.assertTrue(len(feat['geometry']['coordinates']) == 2)
