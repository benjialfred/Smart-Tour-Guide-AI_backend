"""
Script de Rodage, Évaluation et Entraînement de l'IA Smart Tour Guide
Effectue jusqu'à 100 tests automatisés à travers 20 destinations mondiales et 5 thématiques de voyage.
Génère :
1. Un rapport d'évaluation complet (JSON & Markdown)
2. Un dataset d'entraînement pour Fine-Tuning au format standard JSONL
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Configuration Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_guide_backend.settings')

import django
django.setup()

from guide_core.models import ChatMessage, TourSession
from guide_core.services.agent_service import SYSTEM_PROMPT, TourGuideAgent

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# 100 SCÉNARIOS DE TEST RÉPARTIS SUR 20 DESTINATIONS MONDIALES ET 5 THÉMATIQUES
# ------------------------------------------------------------------------------
DESTINATIONS = [
    {
        "city": "Paris",
        "country": "France",
        "tests": [
            "Quels sont les 3 monuments historiques incontournables et leurs anecdotes secrètes ?",
            "Recommande-moi les meilleurs bistrots traditionnels et pâtisseries du quartier Latin.",
            "Crée un itinéraire à pied de 3 heures reliant Notre-Dame, le Louvre et les Tuileries.",
            "Quels sont les passages couverts secrets et insolites à ne pas manquer ?",
            "Comment optimiser une visite culturelle du Marais avec un budget modéré ?"
        ]
    },
    {
        "city": "Rome",
        "country": "Italie",
        "tests": [
            "Fais-moi découvrir l'histoire du Colisée et du Forum Romain avec des détails vivants.",
            "Où déguster les meilleures pâtes cacio e pepe et les glaces artisanales ?",
            "Trace un circuit de visite à pied entre la Fontaine de Trevi, le Panthéon et la Place Navone.",
            "Quels sont les trésors cachés antiques loin de la foule touristique ?",
            "Donne-moi les meilleurs conseils pour visiter le Vatican et ses musées le matin."
        ]
    },
    {
        "city": "Tokyo",
        "country": "Japon",
        "tests": [
            "Présente-moi le temple Senso-ji et le sanctuaire Meiji avec leurs coutumes.",
            "Quels sont les meilleurs spots de street food à Asakusa et les izakayas typiques ?",
            "Organise un parcours à pied reliant le carrefour de Shibuya, Harajuku et le parc Yoyogi.",
            "Quels jardins japonais secrets offrent un havre de paix en plein centre-ville ?",
            "Quels conseils d'étiquette indispensables connaître pour explorer les quartiers traditionnels ?"
        ]
    },
    {
        "city": "Florence",
        "country": "Italie",
        "tests": [
            "Raconte-moi l'histoire de la coupole de Brunelleschi au Duomo et des Médicis.",
            "Où manger la vraie Bistecca alla Fiorentina et goûter aux vins toscans ?",
            "Planifie une balade à pied du Ponte Vecchio à la Piazzale Michelangelo pour le coucher du soleil.",
            "Quels ateliers d'artisans de cuir et galeries secrètes visiter dans l'Oltrarno ?",
            "Conseille-moi sur la meilleure façon de visiter la Galerie des Offices sans perdre de temps."
        ]
    },
    {
        "city": "Barcelone",
        "country": "Espagne",
        "tests": [
            "Fais-moi un exposé captivant sur la Sagrada Família et le génie d'Antoni Gaudí.",
            "Quels bars à tapas authentiques fréquenter dans le quartier d'El Born et de Gràcia ?",
            "Construis un itinéraire de promenade à pied du Passeig de Gràcia jusqu'au Parc Güell.",
            "Quelles sont les pépites modernistes méconnues hors des sentiers battus ?",
            "Quelles sont les meilleures heures pour profiter de la plage et du quartier gothique ?"
        ]
    },
    {
        "city": "New York",
        "country": "États-Unis",
        "tests": [
            "Présente-moi l'histoire architecturale de l'Empire State Building et du Chrysler Building.",
            "Où trouver les meilleurs bagels traditionnels et les speakeasies historiques ?",
            "Trace un parcours pédestre le long de la High Line jusqu'au Meatpacking District et Chelsea Market.",
            "Quels parcs et points de vue secrets sur la skyline méritent le détour ?",
            "Comment organiser une journée culturelle entre Central Park et les musées majeurs ?"
        ]
    },
    {
        "city": "Londres",
        "country": "Royaume-Uni",
        "tests": [
            "Explique-moi l'histoire de la Tour de Londres et des joyaux de la Couronne.",
            "Quels pubs historiques centenaires valent le détour pour un Sunday Roast ?",
            "Élabore un itinéraire à pied longeant la Tamise de Westminster Bridge jusqu'à Tower Bridge.",
            "Quels marchés insolites et ruelles victoriennes secrètes explorer ?",
            "Quels musées gratuits explorer en priorité lors d'un week-end pluvieux ?"
        ]
    },
    {
        "city": "Marrakech",
        "country": "Maroc",
        "tests": [
            "Raconte-moi l'histoire de la place Jemaa el-Fna et de la mosquée Koutoubia.",
            "Où déguster les meilleurs tajines traditionnels et pâtisseries aux amandes dans la médina ?",
            "Organise un parcours à pied à travers les souks d'artisans et le Palais de la Bahia.",
            "Quels riads historiques cachés et jardins d'oasis visiter pour trouver la fraîcheur ?",
            "Quels conseils d'initié pour négocier avec respect et bien vivre l'ambiance des souks ?"
        ]
    },
    {
        "city": "Kyoto",
        "country": "Japon",
        "tests": [
            "Raconte l'histoire du temple Kinkaku-ji (Pavillon d'or) et de la forêt de bambous d'Arashiyama.",
            "Où faire l'expérience d'un repas Kaiseki raffiné et d'une cérémonie du thé authentique ?",
            "Planifie un parcours à pied matinal sur le Chemin de la Philosophie entre les temples zen.",
            "Quelles ruelles traditionnelles préservées de Gion explorer pour ressentir l'époque Edo ?",
            "Quelles règles de respect appliquer pour photographier et visiter les temples sacrés ?"
        ]
    },
    {
        "city": "Berlin",
        "country": "Allemagne",
        "tests": [
            "Décris l'histoire poignante de la Porte de Brandebourg et du Mur de Berlin.",
            "Où goûter la meilleure Currywurst artisanale et profiter des cafés créatifs de Kreuzberg ?",
            "Trace un circuit de marche reliant l'île aux Musées, la cathédrale et Alexanderplatz.",
            "Quels bunkers historiques et galeries de street art alternatives découvrir ?",
            "Comment combiner culture historique et vie de quartier détendue sur un week-end ?"
        ]
    },
    {
        "city": "Amsterdam",
        "country": "Pays-Bas",
        "tests": [
            "Présente-moi l'histoire de la Maison Anne Frank et des canaux du Siècle d'Or.",
            "Quels sont les meilleurs endroits pour goûter aux stroopwafels chauds et fromages fermiers ?",
            "Élabore un circuit de promenade à pied ou à vélo à travers le quartier du Jordaan.",
            "Quelles cours intérieures secrètes (hofjes) méritent le coup d'œil ?",
            "Comment éviter les files d'attente au Rijksmuseum et au musée Van Gogh ?"
        ]
    },
    {
        "city": "Istanbul",
        "country": "Turquie",
        "tests": [
            "Explique-moi les splendeurs et l'histoire de Sainte-Sophie et de la Mosquée Bleue.",
            "Quels délices et thés turcs traditionnels savourer dans les ruelles du Bazar aux Épices ?",
            "Crée un parcours à pied depuis la place Sultanahmet jusqu'au Pont de Galata.",
            "Quels hammams historiques préservés et citernes méconnues valent le détour ?",
            "Quelles sont les meilleures traversées en ferry du Bosphore pour admirer la ville au coucher du soleil ?"
        ]
    },
    {
        "city": "Lisbonne",
        "country": "Portugal",
        "tests": [
            "Raconte l'épopée des explorateurs à la Tour de Belém et au Monastère des Hiéronymites.",
            "Où écouter du vrai Fado traditionnel tout en dégustant des Pastéis de Nata et des petiscos ?",
            "Trace un circuit à pied dans les ruelles pavées de l'Alfama jusqu'au Miradouro de Santa Luzia.",
            "Quels miradouros cachés offrent la plus belle vue sur le Tage sans touristes ?",
            "Comment naviguer efficacement dans la ville aux sept collines avec le tram 28 ?"
        ]
    },
    {
        "city": "Prague",
        "country": "République Tchèque",
        "tests": [
            "Présente-moi les légendes du Pont Charles et de l'Horloge Astronomique de la vieille ville.",
            "Où trouver les tavernes traditionnelles servant les meilleures bières pilsner tchèques ?",
            "Planifie une balade à pied montant jusqu'au Château de Prague et la Ruelle d'Or.",
            "Quels jardins baroques secrets et passages Art Nouveau découvrir à Mala Strana ?",
            "Quels conseils pour profiter du charme mystique de Prague très tôt le matin ?"
        ]
    },
    {
        "city": "Vienne",
        "country": "Autriche",
        "tests": [
            "Décris les fastes du Château de Schönbrunn et l'héritage impérial des Habsbourg.",
            "Quels cafés viennois historiques choisir pour déguster une Sachertorte avec un Melange ?",
            "Trace un itinéraire le long de la Ringstrasse reliant l'Opéra d'État, le Hofburg et le Belvédère.",
            "Quelles cours intérieures secrètes et pavillons Biedermeier explorer en paix ?",
            "Comment assister à un concert classique ou opéra à tarif accessible à Vienne ?"
        ]
    },
    {
        "city": "Athènes",
        "country": "Grèce",
        "tests": [
            "Fais revivre l'époque de Périclès avec le Parthénon et l'Acropole d'Athènes.",
            "Où savourer des souvlakis authentiques et des mezzés grecs dans le quartier de Psiri ?",
            "Élabore un parcours à pied descendant de l'Acropole à travers Plaka et l'Agora antique.",
            "Quelles collines sauvages comme Philopappos offrent le meilleur panorama sur le temple ?",
            "À quelle heure visiter l'Acropole pour éviter les fortes chaleurs et la foule ?"
        ]
    },
    {
        "city": "Venise",
        "country": "Italie",
        "tests": [
            "Raconte les secrets du Palais des Doges et la basilique Saint-Marc.",
            "Quels bacari authentiques fréquenter pour déguster des cicchetti et un Spritz local ?",
            "Trace une promenade à pied sinueuse reliant le pont du Rialto au quartier pittoresque de Cannaregio.",
            "Quels quartiers paisibles et ponts sans touristes préservent la vraie âme vénitienne ?",
            "Quelles îles de la lagune (Burano, Torcello) visiter pour une échappée artisanale ?"
        ]
    },
    {
        "city": "Le Caire",
        "country": "Égypte",
        "tests": [
            "Présente-moi l'histoire des Pyramides de Gizeh, du Sphinx et des pharaons bâtisseurs.",
            "Où boire un café à la cardamome et déguster un Koshari traditionnel au Caire historique ?",
            "Organise un itinéraire à pied à travers le souk Khan el-Khalili et la rue Al-Muizz.",
            "Quelles terrasses panoramiques secrètes permettent d'admirer les minarets au crépuscule ?",
            "Quels conseils pratiques indispensables pour négocier les transports et visites aux pyramides ?"
        ]
    },
    {
        "city": "Montréal",
        "country": "Canada",
        "tests": [
            "Présente-moi la basilique Notre-Dame et l'histoire du Vieux-Montréal.",
            "Où manger la meilleure poutine artisanale et des bagels cuits au feu de bois ?",
            "Trace une promenade pédestre montant au sommet du Mont-Royal pour admirer la vue.",
            "Quelles fresques murales et ruelles vertes du Plateau méritent une exploration ?",
            "Comment profiter au mieux de la ville souterraine en saison fraîche ?"
        ]
    },
    {
        "city": "Sydney",
        "country": "Australie",
        "tests": [
            "Raconte l'histoire de la conception de l'Opéra de Sydney et du Harbour Bridge.",
            "Quels cafés branchés et marchés de poissons fréquenter pour des fruits de mer ultra frais ?",
            "Planifie la célèbre marche côtière à pied de Bondi Beach à Coogee.",
            "Quels jardins botaniques secrets et criques du port explorer loin des foules ?",
            "Quel ferry emprunter pour bénéficier de la plus belle vue sur le port sans payer un tour privé ?"
        ]
    }
]


def run_training_and_benchmark(
    max_tests: int = 100,
    delay_between_calls: float = 2.0,
    output_dir: str = "training_evaluation_output"
):
    """
    Exécute le benchmark et rodage de l'IA sur un panel de 100 requêtes réelles.
    """
    out_path = BASE_DIR / output_dir
    out_path.mkdir(exist_ok=True, parents=True)

    print("=" * 70)
    print("🌍 SMART TOUR GUIDE AI — BENCHMARK & RODAGE SUR 100 TESTS")
    print(f"📊 Objectif : {max_tests} requêtes de visite culturelle")
    print(f"⏱️ Pause anti-rate-limit : {delay_between_calls}s par requête")
    print(f"💾 Dossier de sortie : {out_path}")
    print("=" * 70)

    agent = TourGuideAgent()
    results = []
    fine_tuning_records = []

    total_scenarios = []
    for d in DESTINATIONS:
        for q in d["tests"]:
            total_scenarios.append({
                "destination": d["city"],
                "country": d["country"],
                "query": q
            })

    total_scenarios = total_scenarios[:max_tests]
    successful_count = 0
    total_pois_found = 0
    total_itinerary_stops = 0

    start_time_all = time.time()

    for idx, item in enumerate(total_scenarios, 1):
        dest = item["destination"]
        query = item["query"]

        print(f"\n[{idx:03d}/{len(total_scenarios):03d}] 🏙️ {dest} : « {query[:60]}... »")

        session = TourSession.objects.create(
            title=f"Test #{idx} - {dest}",
            destination=dest
        )

        t0 = time.time()
        max_retries = 3
        test_result = {
            "test_id": idx,
            "destination": dest,
            "country": item["country"],
            "query": query,
            "success": False,
            "error": None,
            "duration_seconds": 0,
            "features_count": 0,
            "itinerary_stops_count": 0,
            "reply_length": 0,
            "audio_script_length": 0,
        }

        for attempt in range(max_retries):
            try:
                res = agent.process_message(
                    session=session,
                    user_message=query,
                    destination=dest
                )

                elapsed = round(time.time() - t0, 2)
                reply = res.get("reply", "")
                geojson = res.get("geojson", {})
                features = geojson.get("features", [])
                itinerary = res.get("itinerary", [])
                audio_script = res.get("audio_script", "")

                test_result.update({
                    "success": True,
                    "duration_seconds": elapsed,
                    "features_count": len(features),
                    "itinerary_stops_count": len(itinerary),
                    "reply_length": len(reply),
                    "audio_script_length": len(audio_script),
                    "sample_reply": reply[:150].replace("\n", " ") + "..."
                })

                successful_count += 1
                total_pois_found += len(features)
                total_itinerary_stops += len(itinerary)

                # Format fine-tuning message
                fine_tuning_records.append({
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": query},
                        {"role": "assistant", "content": reply}
                    ],
                    "metadata": {
                        "destination": dest,
                        "features_count": len(features),
                        "itinerary_count": len(itinerary)
                    }
                })

                print(f"    ✅ Succès ({elapsed}s) | 📍 POIs: {len(features)} | 🚶 Étapes: {len(itinerary)} | 📝 Réponse: {len(reply)} car.")
                break

            except Exception as e:
                err_str = str(e)
                logger.warning(f"Tentative {attempt + 1}/{max_retries} échouée pour {dest}: {err_str}")
                if "rate_limit" in err_str.lower() or "429" in err_str:
                    sleep_sec = 6.0 * (attempt + 1)
                    print(f"    ⏳ Rate limit détecté, pause de sécurité de {sleep_sec}s...")
                    time.sleep(sleep_sec)
                else:
                    time.sleep(1.5)

                if attempt == max_retries - 1:
                    test_result["error"] = err_str
                    print(f"    ❌ Échec définitif : {err_str[:80]}")

        results.append(test_result)
        time.sleep(delay_between_calls)

    total_time = round(time.time() - start_time_all, 1)

    # --------------------------------------------------------------------------
    # SAUVEGARDE DU DATASET DE FINE-TUNING (JSONL)
    # --------------------------------------------------------------------------
    dataset_file = out_path / "tour_guide_finetuning_dataset.jsonl"
    with open(dataset_file, "w", encoding="utf-8") as f:
        for record in fine_tuning_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # --------------------------------------------------------------------------
    # SAUVEGARDE DU RAPPORT D'ÉVALUATION (JSON)
    # --------------------------------------------------------------------------
    report_file = out_path / "benchmark_report.json"
    summary_metrics = {
        "timestamp": datetime.now().isoformat(),
        "total_tests_requested": max_tests,
        "total_tests_executed": len(results),
        "successful_tests": successful_count,
        "success_rate_percent": round((successful_count / len(results)) * 100, 1) if results else 0,
        "total_time_seconds": total_time,
        "avg_duration_seconds": round(total_time / len(results), 2) if results else 0,
        "total_pois_discovered": total_pois_found,
        "total_itinerary_stops_generated": total_itinerary_stops,
        "fine_tuning_records_saved": len(fine_tuning_records),
    }

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({
            "metrics": summary_metrics,
            "detailed_results": results
        }, f, ensure_ascii=False, indent=2)

    # --------------------------------------------------------------------------
    # SAUVEGARDE DU RAPPORT SYNTHÉTIQUE (MARKDOWN)
    # --------------------------------------------------------------------------
    md_file = out_path / "benchmark_summary.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write("# 📊 Rapport de Rodage & Évaluation — Smart Tour Guide AI\n\n")
        f.write(f"- **Date** : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **Nombre de tests exécutés** : {len(results)}\n")
        f.write(f"- **Taux de succès** : **{summary_metrics['success_rate_percent']}%** ({successful_count}/{len(results)})\n")
        f.write(f"- **Temps total** : {total_time}s (moyenne {summary_metrics['avg_duration_seconds']}s/test)\n")
        f.write(f"- **Points d'intérêt cartographiés** : {total_pois_found} POIs réels\n")
        f.write(f"- **Étapes d'itinéraires ordonnées** : {total_itinerary_stops} étapes\n")
        f.write(f"- **Paires d'entraînement sauvegardées** : {len(fine_tuning_records)} exemples JSONL\n\n")

        f.write("## 🏆 Tableau Récapitulatif par Destination\n\n")
        f.write("| # | Destination | Requête Testée | POIs | Étapes | Durée | Statut |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for r in results:
            stat_icon = "✅ Succès" if r["success"] else "❌ Erreur"
            f.write(f"| {r['test_id']:02d} | {r['destination']} | {r['query'][:45]}... | {r['features_count']} | {r['itinerary_stops_count']} | {r['duration_seconds']}s | {stat_icon} |\n")

    print("\n" + "=" * 70)
    print("🎉 RODAGE ET ENTRAÎNEMENT TERMINÉS AVEC SUCCÈS !")
    print(f"📈 Taux de réussite : {summary_metrics['success_rate_percent']}%")
    print(f"📍 Total POIs découverts : {total_pois_found}")
    print(f"📁 Fichier d'entraînement généré : {dataset_file.name}")
    print(f"📊 Rapport détaillé : {report_file.name}")
    print(f"📑 Synthèse Markdown : {md_file.name}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script de rodage et évaluation 100 tests pour Smart Tour Guide AI")
    parser.add_argument("--count", type=int, default=100, help="Nombre de tests à exécuter (1 à 100, défaut 100)")
    parser.add_argument("--delay", type=float, default=2.0, help="Délai entre les requêtes en secondes (défaut 2.0s)")
    parser.add_argument("--output", type=str, default="training_evaluation_output", help="Dossier de sortie des rapports")

    args = parser.parse_args()
    run_training_and_benchmark(
        max_tests=args.count,
        delay_between_calls=args.delay,
        output_dir=args.output
    )
