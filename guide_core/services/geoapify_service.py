"""
Geoapify Service
Provides clean, typed, and normalized access to Geoapify REST endpoints:
- Geocoding (search & reverse)
- Places search (POIs, sights, museums, restaurants, etc.)
- Routing (walking, driving, bicycle itineraries)
- Place details
All spatial data is normalized into strict RFC 7946 GeoJSON FeatureCollections.
"""

import logging
from typing import Any, Dict, List, Optional
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class GeoapifyService:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or getattr(settings, 'GEOAPIFY_API_KEY', '')
        self.base_url = (base_url or getattr(settings, 'GEOAPIFY_BASE_URL', 'https://api.geoapify.com')).rstrip('/')
        self.timeout = 15.0

    def _get_headers(self) -> Dict[str, str]:
        return {
            'Accept': 'application/json',
            'User-Agent': 'SmartTourGuideAI/1.0',
        }

    # --------------------------------------------------------------------------
    # GEOCODING
    # --------------------------------------------------------------------------
    def geocode(self, text: str, limit: int = 5, lang: str = 'fr') -> Dict[str, Any]:
        """
        Geocodes a search string into coordinates and standardized address.
        Returns a GeoJSON FeatureCollection.
        """
        if not text or not self.api_key:
            return {"type": "FeatureCollection", "features": []}

        endpoint = f"{self.base_url}/v1/geocode/search"
        params = {
            'text': text,
            'limit': limit,
            'lang': lang,
            'format': 'geojson',
            'apiKey': self.api_key,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(endpoint, params=params, headers=self._get_headers())
                response.raise_for_status()
                data = response.json()
                return self._normalize_geojson(data, default_category='search_result')
        except Exception as e:
            logger.error(f"Geoapify geocode error for '{text}': {e}")
            return {"type": "FeatureCollection", "features": [], "error": str(e)}

    def reverse_geocode(self, lat: float, lon: float, lang: str = 'fr') -> Dict[str, Any]:
        """
        Reverse geocodes coordinates (lat, lon) into address information.
        """
        if not self.api_key:
            return {"type": "FeatureCollection", "features": []}

        endpoint = f"{self.base_url}/v1/geocode/reverse"
        params = {
            'lat': lat,
            'lon': lon,
            'lang': lang,
            'format': 'geojson',
            'apiKey': self.api_key,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(endpoint, params=params, headers=self._get_headers())
                response.raise_for_status()
                data = response.json()
                return self._normalize_geojson(data, default_category='location')
        except Exception as e:
            logger.error(f"Geoapify reverse geocode error for {lat},{lon}: {e}")
            return {"type": "FeatureCollection", "features": [], "error": str(e)}

    # --------------------------------------------------------------------------
    # PLACES / POIS SEARCH
    # --------------------------------------------------------------------------
    def search_places(
        self,
        categories: Optional[List[str]] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius_meters: int = 3000,
        text: Optional[str] = None,
        limit: int = 20,
        lang: str = 'fr',
    ) -> Dict[str, Any]:
        """
        Searches points of interest (sights, museums, restaurants, etc.).
        Categories example: ['tourism.sights', 'entertainment.culture', 'catering.restaurant']
        """
        if not self.api_key:
            return {"type": "FeatureCollection", "features": []}

        if not categories:
            categories = [
                'tourism.sights',
                'tourism.attraction',
                'entertainment.culture',
                'heritage',
                'leisure.park',
            ]

        CATEGORY_MAP = {
            'catering.bakery': 'commercial.food_and_drink.bakery',
            'catering.patisserie': 'commercial.food_and_drink.bakery',
            'catering.pastry': 'commercial.food_and_drink.bakery',
            'tourism.museum': 'entertainment.museum',
            'tourism.monument': 'heritage.monument',
            'tourism.monuments': 'heritage.monument',
            'tourism.sight': 'tourism.sights',
            'tourism.attractions': 'tourism.attraction',
            'food': 'catering.restaurant,catering.cafe',
            'restaurant': 'catering.restaurant',
            'monument': 'tourism.sights,heritage',
            'culture': 'entertainment.culture,entertainment.museum',
            'shopping': 'commercial.shopping_mall,commercial.clothing',
            'park': 'leisure.park',
        }

        sanitized_cats = []
        for cat in categories:
            cat_clean = cat.strip()
            mapped = CATEGORY_MAP.get(cat_clean, cat_clean)
            for m in mapped.split(','):
                if m and m not in sanitized_cats:
                    sanitized_cats.append(m)

        if not sanitized_cats:
            sanitized_cats = ['tourism.sights', 'entertainment.culture', 'catering.restaurant']

        endpoint = f"{self.base_url}/v2/places"
        cat_str = ",".join(sanitized_cats)

        params: Dict[str, Any] = {
            'categories': cat_str,
            'limit': min(limit, 50),
            'lang': lang,
            'apiKey': self.api_key,
        }

        # Spatial filter
        if lat is not None and lon is not None:
            params['filter'] = f"circle:{lon},{lat},{radius_meters}"
            params['bias'] = f"proximity:{lon},{lat}"
        elif text:
            # First geocode to get center if coordinates not provided
            geo = self.geocode(text, limit=1, lang=lang)
            if geo.get('features'):
                center_coords = geo['features'][0]['geometry']['coordinates']
                c_lon, c_lat = center_coords[0], center_coords[1]
                params['filter'] = f"circle:{c_lon},{c_lat},{radius_meters}"
                params['bias'] = f"proximity:{c_lon},{c_lat}"
            else:
                return {"type": "FeatureCollection", "features": [], "warning": f"Location '{text}' not found"}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(endpoint, params=params, headers=self._get_headers())
                response.raise_for_status()
                data = response.json()
                return self._normalize_geojson(data, default_category='poi')
        except Exception as e:
            logger.error(f"Geoapify places search error: {e}")
            return {"type": "FeatureCollection", "features": [], "error": str(e)}

    # --------------------------------------------------------------------------
    # ROUTING
    # --------------------------------------------------------------------------
    def calculate_route(
        self,
        waypoints: List[Dict[str, float]],
        mode: str = 'walk',
        lang: str = 'fr',
    ) -> Dict[str, Any]:
        """
        Calculates a route between a list of waypoints [{'lat': y, 'lon': x}, ...].
        Supported modes: 'walk', 'bicycle', 'drive', 'transit'.
        Returns a GeoJSON Feature containing the route LineString with distance and time.
        """
        if len(waypoints) < 2 or not self.api_key:
            return {"type": "FeatureCollection", "features": [], "error": "At least 2 waypoints required"}

        # Format waypoints: lat,lon|lat,lon
        wp_str = "|".join([f"{wp['lat']:.6f},{wp['lon']:.6f}" for wp in waypoints])

        endpoint = f"{self.base_url}/v1/routing"
        params = {
            'waypoints': wp_str,
            'mode': mode,
            'lang': lang,
            'format': 'geojson',
            'apiKey': self.api_key,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(endpoint, params=params, headers=self._get_headers())
                response.raise_for_status()
                data = response.json()
                return self._normalize_route_geojson(data, mode, waypoints)
        except Exception as e:
            logger.error(f"Geoapify routing error: {e}")
            return {"type": "FeatureCollection", "features": [], "error": str(e)}

    # --------------------------------------------------------------------------
    # PLACE DETAILS
    # --------------------------------------------------------------------------
    def get_place_details(self, place_id: str, lang: str = 'fr') -> Dict[str, Any]:
        """
        Retrieves in-depth details for a given place ID.
        """
        if not place_id or not self.api_key or len(place_id) < 8 or place_id.isdigit():
            return {"warning": f"Place ID '{place_id}' non valide pour Geoapify"}

        endpoint = f"{self.base_url}/v2/place-details"
        params = {
            'id': place_id,
            'lang': lang,
            'apiKey': self.api_key,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(endpoint, params=params, headers=self._get_headers())
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Geoapify place details error for {place_id}: {e}")
            return {"error": str(e)}

    # --------------------------------------------------------------------------
    # GEOJSON NORMALIZATION
    # --------------------------------------------------------------------------
    def _normalize_geojson(self, data: Dict[str, Any], default_category: str) -> Dict[str, Any]:
        """
        Normalizes any Geoapify spatial response into a standardized GeoJSON FeatureCollection.
        Each feature includes uniform properties for seamless Leaflet marker rendering.
        """
        features: List[Dict[str, Any]] = []
        raw_features = data.get('features', [])

        for idx, item in enumerate(raw_features):
            geom = item.get('geometry', {})
            props = item.get('properties', {})

            lon = props.get('lon') or (geom.get('coordinates', [None, None])[0] if geom.get('coordinates') else None)
            lat = props.get('lat') or (geom.get('coordinates', [None, None])[1] if geom.get('coordinates') else None)

            if lon is None or lat is None:
                continue

            # Determine human-friendly name
            name = (
                props.get('name')
                or props.get('address_line1')
                or props.get('street')
                or props.get('city')
                or f"Lieu #{idx + 1}"
            )

            # Categorization & Icon determination
            cats = props.get('categories', [])
            cat_label = self._classify_category(cats, default_category)

            # Rich attributes
            contact = props.get('contact', {})
            opening_hours = props.get('opening_hours', '')
            website = props.get('website') or contact.get('website', '')
            phone = props.get('phone') or contact.get('phone', '')
            wiki = props.get('wikipedia', '')

            feature = {
                "type": "Feature",
                "id": props.get('place_id') or f"poi_{idx}_{lat}_{lon}",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(lon), float(lat)]
                },
                "properties": {
                    "name": name,
                    "category": cat_label,
                    "categories": cats,
                    "formatted": props.get('formatted', ''),
                    "city": props.get('city', ''),
                    "country": props.get('country', ''),
                    "lat": float(lat),
                    "lon": float(lon),
                    "website": website,
                    "phone": phone,
                    "opening_hours": opening_hours,
                    "wikipedia": wiki,
                    "place_id": props.get('place_id', ''),
                    "distance": props.get('distance', None),
                }
            }
            features.append(feature)

        return {
            "type": "FeatureCollection",
            "features": features
        }

    def _normalize_route_geojson(self, data: Dict[str, Any], mode: str, waypoints: List[Dict[str, float]]) -> Dict[str, Any]:
        """
        Normalizes Geoapify routing response into a GeoJSON Feature containing the LineString
        route and metadata (distance, time, steps).
        """
        features = data.get('features', [])
        if not features:
            return {"type": "FeatureCollection", "features": [], "warning": "No route found"}

        route_feature = features[0]
        geom = route_feature.get('geometry', {})
        props = route_feature.get('properties', {})

        distance_meters = props.get('distance', 0)
        time_seconds = props.get('time', 0)
        legs = props.get('legs', [])

        # Format turn-by-turn steps
        all_steps = []
        for leg in legs:
            for step in leg.get('steps', []):
                instruction = step.get('instruction', {}).get('text', '')
                if instruction:
                    all_steps.append({
                        "instruction": instruction,
                        "distance_m": step.get('distance', 0),
                        "time_s": step.get('time', 0),
                    })

        normalized_feature = {
            "type": "Feature",
            "geometry": geom,
            "properties": {
                "is_route": True,
                "mode": mode,
                "distance_meters": distance_meters,
                "distance_km": round(distance_meters / 1000.0, 2),
                "time_seconds": time_seconds,
                "time_minutes": round(time_seconds / 60.0, 1),
                "waypoints": waypoints,
                "steps": all_steps,
            }
        }

        return {
            "type": "FeatureCollection",
            "features": [normalized_feature]
        }

    @staticmethod
    def _classify_category(cats: List[str], default: str) -> str:
        """Assigns an intuitive visual category key for map icons."""
        joined = " ".join(cats).lower()
        if any(k in joined for k in ['museum', 'gallery', 'historic', 'heritage', 'monument', 'sights', 'castle', 'ruins', 'memorial']):
            return 'monument'
        if any(k in joined for k in ['restaurant', 'cafe', 'food', 'catering', 'bar', 'bakery']):
            return 'food'
        if any(k in joined for k in ['park', 'garden', 'nature', 'natural', 'viewpoint', 'beach']):
            return 'nature'
        if any(k in joined for k in ['entertainment', 'theatre', 'cinema', 'music']):
            return 'entertainment'
        if any(k in joined for k in ['shopping', 'commercial', 'market']):
            return 'shopping'
        return default
