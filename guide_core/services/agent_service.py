"""
Agent Service
Orchestrates the Grok / Groq LLM agent, MCP Geoapify tools, conversation memory,
and spatial GeoJSON synthesis for the Smart Tour Guide AI.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from django.conf import settings
from groq import Groq
from guide_core.models import ChatMessage, TourSession
from .geoapify_mcp import GeoapifyMCPClient
from .geoapify_service import GeoapifyService

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es 'Smart Tour Guide AI', un guide touristique d'élite, passionné d'histoire, d'architecture, de gastronomie et de secrets locaux.

Tes missions :
1. Guider les voyageurs à travers les villes du monde entier en leur offrant des récits passionnants, des anecdotes captivantes et des conseils d'initié (meilleures heures de visite, plats typiques incontournables, ruelles secrètes).
2. Utiliser obligatoirement tes outils géographiques MCP connectés à Geoapify (geoapify_geocode, geoapify_places_search, geoapify_routing, geoapify_place_details) pour obtenir des lieux et coordonnées réels dès que l'utilisateur te demande un itinéraire, des monuments, des restaurants ou des idées de visite.
3. Quand tu organises un circuit ou une journée de visite, appelle `geoapify_routing` pour calculer le trajet à pied réaliste et donner les temps de marche exacts.
4. Structure toujours ta réponse avec élégance :
   - Un titre accrocheur et une brève introduction immersive.
   - Les étapes ordonnées avec émojis adaptés (🏛️ pour monument, ☕/🍷 pour gastronomie, 🌿 pour parc, 🎭 pour culture).
   - Les conseils pratiques (durée recommandée, astuces coupe-file, budget estimé).
5. Rédige avec un ton chaleureux, cultivé et dynamique. Réponds dans la langue de l'utilisateur (français par défaut).
"""


class TourGuideAgent:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        geo_service: Optional[GeoapifyService] = None,
    ):
        self.api_key = api_key or getattr(settings, 'GROQ_API_KEY', '')
        self.model = model or getattr(settings, 'GROQ_MODEL', 'qwen/qwen3.8-27b')
        self.geo_service = geo_service or GeoapifyService()
        self.mcp_client = GeoapifyMCPClient(service=self.geo_service)
        self.groq_client = Groq(api_key=self.api_key) if self.api_key else None

    def process_message(
        self,
        session: TourSession,
        user_message: str,
        user_location: Optional[Dict[str, float]] = None,
        destination: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Processes a user message, conducts tool orchestration with Geoapify MCP,
        updates session history, and returns a rich response object.
        """
        # Save user message
        ChatMessage.objects.create(
            session=session,
            role='user',
            content=user_message,
            metadata={'user_location': user_location, 'destination': destination}
        )

        if destination and not session.destination:
            session.destination = destination
            session.title = f"Visite de {destination}"
            session.save(update_fields=['destination', 'title', 'updated_at'])

        # Build conversation context from DB
        history = self._load_conversation_history(session)

        # Prepare tools
        llm_tools = self.mcp_client.to_llm_tools()

        # Collector for accumulated GeoJSON features from tool executions
        collected_features: List[Dict[str, Any]] = []
        route_geojson: Optional[Dict[str, Any]] = None
        tool_call_logs: List[Dict[str, Any]] = []

        if not self.groq_client:
            # Fallback if no LLM key configured
            reply_text = (
                "Bienvenue sur Smart Tour Guide AI ! Je suis prêt à vous guider. "
                "Cependant, la clé API de l'agent n'est pas encore configurée dans le fichier d'environnement."
            )
            return {
                "reply": reply_text,
                "geojson": {"type": "FeatureCollection", "features": []},
                "itinerary": [],
                "audio_script": reply_text,
                "session_id": str(session.id)
            }

        # Multi-turn tool execution loop
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

        max_iterations = 4
        final_content = ""

        try:
            for iteration in range(max_iterations):
                logger.info(f"Agent iteration {iteration + 1} with model {self.model}")
                response = self.groq_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=llm_tools,
                    tool_choice="auto",
                    temperature=0.7,
                    max_tokens=750,
                )

                choice = response.choices[0]
                message = choice.message

                # Check if the model wants to call tools
                if message.tool_calls:
                    # Append assistant tool calls to message history
                    assistant_msg = {
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                }
                            }
                            for tc in message.tool_calls
                        ]
                    }
                    messages.append(assistant_msg)

                    for tc in message.tool_calls:
                        tool_name = tc.function.name
                        try:
                            args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                        except Exception:
                            args = {}

                        tool_res = self.mcp_client.execute_tool(tool_name, args)
                        tool_call_logs.append({
                            "tool": tool_name,
                            "arguments": args,
                            "result": tool_res.get("content", [{}])[0].get("text", "")[:200]
                        })

                        # Extract any spatial GeoJSON data
                        if "geojson" in tool_res and tool_res["geojson"].get("features"):
                            for f in tool_res["geojson"]["features"]:
                                if f.get("properties", {}).get("is_route"):
                                    route_geojson = f
                                else:
                                    collected_features.append(f)

                        tool_text = tool_res.get("content", [{}])[0].get("text", "Succès")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": tool_text
                        })

                    # Next iteration will send tool results back to LLM
                    continue
                else:
                    final_content = message.content or ""
                    break

            if not final_content and iteration == max_iterations - 1:
                final_content = "Voici les meilleures recommandations trouvées pour votre visite !"

        except Exception as e:
            logger.error(f"Error calling Groq LLM agent: {e}", exc_info=True)
            # Automatic fallback: if user mentioned places/city, perform direct search
            fallback_features = self._fallback_spatial_search(user_message, destination)
            collected_features.extend(fallback_features)
            final_content = self._generate_fallback_response(user_message, destination, fallback_features)

        # Synthesize final GeoJSON FeatureCollection
        all_features = self._deduplicate_features(collected_features)
        if route_geojson:
            all_features.append(route_geojson)

        geojson_result = {
            "type": "FeatureCollection",
            "features": all_features
        }

        # Update session center if we discovered coordinates
        if all_features and (not session.center_lat or not session.center_lon):
            for f in all_features:
                if f.get("geometry", {}).get("type") == "Point":
                    c = f["geometry"]["coordinates"]
                    session.center_lon, session.center_lat = c[0], c[1]
                    session.save(update_fields=['center_lat', 'center_lon', 'updated_at'])
                    break

        # Extract structured itinerary stops
        itinerary = self._extract_itinerary(all_features, final_content)

        # Generate audio-ready narration script
        audio_script = self._generate_audio_narration(final_content)

        # Save assistant message in database
        metadata = {
            "geojson": geojson_result,
            "itinerary": itinerary,
            "audio_script": audio_script,
            "tool_calls": tool_call_logs,
        }
        ChatMessage.objects.create(
            session=session,
            role='assistant',
            content=final_content,
            metadata=metadata
        )

        return {
            "reply": final_content,
            "geojson": geojson_result,
            "itinerary": itinerary,
            "audio_script": audio_script,
            "session_id": str(session.id)
        }

    def _load_conversation_history(self, session: TourSession, limit: int = 8) -> List[Dict[str, str]]:
        """Loads recent conversation messages for prompt memory."""
        messages_qs = session.messages.filter(role__in=['user', 'assistant']).order_by('-timestamp')[:limit]
        history = []
        for msg in reversed(list(messages_qs)):
            history.append({
                "role": msg.role,
                "content": msg.content
            })
        return history

    def _fallback_spatial_search(self, user_message: str, destination: Optional[str]) -> List[Dict[str, Any]]:
        """Executes direct search when the model doesn't trigger tool calls or encounters limits."""
        query = destination or user_message
        search_res = self.geo_service.search_places(
            text=query,
            categories=['tourism.sights', 'entertainment.culture', 'catering.restaurant'],
            limit=8
        )
        return search_res.get('features', [])

    def _generate_fallback_response(self, user_message: str, destination: Optional[str], features: List[Dict[str, Any]]) -> str:
        dest_label = destination or "cette destination"
        if not features:
            return (
                f"Je prépare votre découverte pour {dest_label}. "
                "Indiquez-moi vos centres d'intérêt spécifiques (histoire, musées, gastronomie, parcs) "
                "pour concevoir l'itinéraire idéal !"
            )

        places_text = "\n".join([
            f"- **{f['properties']['name']}** ({f['properties'].get('category', 'Lieu')}): {f['properties'].get('formatted', '')}"
            for f in features[:6]
        ])
        return (
            f"### 🌟 Découverte culturelle de {dest_label}\n\n"
            f"Voici les points d'intérêt incontournables repérés pour vous sur la carte interactive :\n\n"
            f"{places_text}\n\n"
            "💡 *Conseil du guide :* Cliquez sur chaque repère sur la carte pour voir sa position exacte et lancer la navigation à pied !"
        )

    def _deduplicate_features(self, features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Removes duplicates based on place_id or name."""
        seen = set()
        unique = []
        for f in features:
            props = f.get('properties', {})
            key = props.get('place_id') or props.get('name') or str(f.get('geometry', {}).get('coordinates'))
            if key not in seen:
                seen.add(key)
                unique.append(f)
        return unique

    def _extract_itinerary(self, features: List[Dict[str, Any]], content: str) -> List[Dict[str, Any]]:
        """Creates an ordered list of itinerary stops from points of interest."""
        stops = []
        point_idx = 1
        for f in features:
            if f.get('geometry', {}).get('type') == 'Point':
                p = f.get('properties', {})
                coords = f['geometry']['coordinates']
                stops.append({
                    "step": point_idx,
                    "name": p.get('name', f"Étape {point_idx}"),
                    "category": p.get('category', 'poi'),
                    "formatted": p.get('formatted', ''),
                    "lat": coords[1],
                    "lon": coords[0],
                    "place_id": p.get('place_id', ''),
                    "suggested_duration": "45 min" if p.get('category') == 'monument' else "30 min",
                    "notes": f"Visite recommandée : {p.get('name')}"
                })
                point_idx += 1
                if point_idx > 8:
                    break
        return stops

    def _generate_audio_narration(self, markdown_text: str) -> str:
        """Strips markdown and formats a clean speech-ready audio script."""
        text = re.sub(r'#+\s*', '', markdown_text)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        text = re.sub(r'[\r\n]+', ' ', text)
        # Limit audio narration to first 250 words for comfortable voice playback
        words = text.split()
        return " ".join(words[:180])
