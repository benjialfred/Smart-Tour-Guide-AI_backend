"""
Geoapify Model Context Protocol (MCP) Client & Tool Definitions
Provides Model Context Protocol (MCP) compatible tools and execution engine
for Geoapify integration.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from .geoapify_service import GeoapifyService

logger = logging.getLogger(__name__)


class GeoapifyMCPClient:
    """
    Implements the MCP (Model Context Protocol) tool provider for Geoapify.
    Exposes discovery of tools and execution of tool requests.
    """

    def __init__(self, service: Optional[GeoapifyService] = None):
        self.service = service or GeoapifyService()

    def get_tools_manifest(self) -> List[Dict[str, Any]]:
        """
        Returns MCP standard tool descriptions with JSON Schema parameter definitions.
        """
        return [
            {
                "name": "geoapify_geocode",
                "description": (
                    "Géocode une adresse, une ville ou un monument pour obtenir ses coordonnées GPS "
                    "précises et son adresse normalisée."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Nom du lieu, de la ville ou adresse (ex: 'Colisée Rome', 'Tour Eiffel Paris')"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Nombre maximum de résultats (défaut 5)",
                            "default": 5
                        }
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "geoapify_places_search",
                "description": (
                    "Recherche des points d'intérêt (monuments, musées, restaurants, parcs, etc.) "
                    "autour de coordonnées ou dans une ville donnée avec des catégories sélectionnées."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "categories": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Liste de catégories Geoapify, ex: ['tourism.sights', 'entertainment.culture', "
                                "'catering.restaurant', 'heritage', 'leisure.park']"
                            ),
                            "default": ["tourism.sights", "entertainment.culture", "heritage"]
                        },
                        "text": {
                            "type": "string",
                            "description": "Nom de la ville ou zone géographique (ex: 'Florence, Italie')",
                        },
                        "lat": {
                            "type": "number",
                            "description": "Latitude du centre de recherche (optionnel si text fourni)"
                        },
                        "lon": {
                            "type": "number",
                            "description": "Longitude du centre de recherche (optionnel si text fourni)"
                        },
                        "radius_meters": {
                            "type": "integer",
                            "description": "Rayon de recherche en mètres (ex: 2000 pour 2km, défaut 3000)",
                            "default": 3000
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Nombre de résultats maximum (défaut 15)",
                            "default": 15
                        }
                    }
                }
            },
            {
                "name": "geoapify_routing",
                "description": (
                    "Calcule un itinéraire optimal (à pied, à vélo ou en voiture) reliant une liste "
                    "ordonnée de points d'intérêt avec distance, durée et géométrie cartographique."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "waypoints": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "lat": {"type": "number", "description": "Latitude"},
                                    "lon": {"type": "number", "description": "Longitude"},
                                    "name": {"type": "string", "description": "Nom du point d'étape"}
                                },
                                "required": ["lat", "lon"]
                            },
                            "description": "Liste ordonnée d'au moins 2 waypoints"
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["walk", "bicycle", "drive"],
                            "description": "Mode de déplacement (recommandé 'walk' pour les visites de ville)",
                            "default": "walk"
                        }
                    },
                    "required": ["waypoints"]
                }
            },
            {
                "name": "geoapify_place_details",
                "description": (
                    "Récupère les détails enrichis d'un lieu spécifique grâce à son identifiant Geoapify "
                    "(horaires, contact, site web, description)."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "place_id": {
                            "type": "string",
                            "description": "Identifiant unique Geoapify du lieu"
                        }
                    },
                    "required": ["place_id"]
                }
            }
        ]

    def to_llm_tools(self) -> List[Dict[str, Any]]:
        """
        Adapts MCP tool definitions to Groq/OpenAI compatible tool schema format.
        """
        tools = []
        for mcp_tool in self.get_tools_manifest():
            tools.append({
                "type": "function",
                "function": {
                    "name": mcp_tool["name"],
                    "description": mcp_tool["description"],
                    "parameters": mcp_tool["input_schema"]
                }
            })
        return tools

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a named MCP tool with given arguments.
        Returns a dict containing 'content' (human/LLM readable) and raw 'geojson' or data.
        """
        logger.info(f"Executing MCP Tool '{tool_name}' with arguments: {arguments}")

        try:
            if tool_name == "geoapify_geocode":
                text = arguments.get("text", "")
                limit = int(arguments.get("limit", 5))
                result = self.service.geocode(text=text, limit=limit)
                features = result.get("features", [])
                summary = []
                for f in features:
                    p = f["properties"]
                    coords = f["geometry"]["coordinates"]
                    summary.append(f"- {p.get('name')}: {p.get('formatted')} (lat: {coords[1]}, lon: {coords[0]})")
                text_content = f"Résultats de géocodage pour '{text}':\n" + ("\n".join(summary) if summary else "Aucun résultat trouvé.")
                return {
                    "is_error": False,
                    "content": [{"type": "text", "text": text_content}],
                    "geojson": result,
                    "raw": result
                }

            elif tool_name == "geoapify_places_search":
                categories = arguments.get("categories")
                text = arguments.get("text")
                lat = arguments.get("lat")
                lon = arguments.get("lon")
                radius = int(arguments.get("radius_meters", 3000))
                limit = int(arguments.get("limit", 15))

                result = self.service.search_places(
                    categories=categories,
                    lat=lat,
                    lon=lon,
                    radius_meters=radius,
                    text=text,
                    limit=limit,
                )
                features = result.get("features", [])
                summary = []
                for idx, f in enumerate(features[:12], 1):
                    p = f["properties"]
                    c = f["geometry"]["coordinates"]
                    summary.append(
                        f"{idx}. {p.get('name')} [{p.get('category')}] - {p.get('formatted', '')} "
                        f"(GPS: {c[1]:.5f}, {c[0]:.5f})"
                    )
                text_content = (
                    f"Points d'intérêt trouvés ({len(features)} résultats):\n" +
                    ("\n".join(summary) if summary else "Aucun point d'intérêt trouvé pour ces critères.")
                )
                return {
                    "is_error": False,
                    "content": [{"type": "text", "text": text_content}],
                    "geojson": result,
                    "raw": result
                }

            elif tool_name == "geoapify_routing":
                waypoints = arguments.get("waypoints", [])
                mode = arguments.get("mode", "walk")
                result = self.service.calculate_route(waypoints=waypoints, mode=mode)
                features = result.get("features", [])
                if features:
                    props = features[0].get("properties", {})
                    dist_km = props.get("distance_km", 0)
                    time_min = props.get("time_minutes", 0)
                    text_content = (
                        f"Itinéraire calculé avec succès ({mode}):\n"
                        f"- Distance totale: {dist_km} km\n"
                        f"- Durée estimée: {time_min} minutes\n"
                        f"- Nombre d'étapes: {len(props.get('steps', []))}"
                    )
                else:
                    text_content = "Impossible de calculer un itinéraire entre ces points."
                return {
                    "is_error": False,
                    "content": [{"type": "text", "text": text_content}],
                    "geojson": result,
                    "raw": result
                }

            elif tool_name == "geoapify_place_details":
                place_id = arguments.get("place_id", "")
                details = self.service.get_place_details(place_id=place_id)
                text_content = f"Détails pour {place_id}: {json.dumps(details, ensure_ascii=False)[:500]}"
                return {
                    "is_error": False,
                    "content": [{"type": "text", "text": text_content}],
                    "raw": details
                }

            else:
                return {
                    "is_error": True,
                    "content": [{"type": "text", "text": f"Outil inconnu '{tool_name}'."}]
                }

        except Exception as e:
            logger.error(f"Error during MCP execution of '{tool_name}': {e}", exc_info=True)
            return {
                "is_error": True,
                "content": [{"type": "text", "text": f"Erreur d'exécution de l'outil {tool_name}: {str(e)}"}],
                "error": str(e)
            }
