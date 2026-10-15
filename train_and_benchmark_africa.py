"""
Script de Rodage, Évaluation et Entraînement de l'IA Smart Tour Guide
Spécialisé sur l'Afrique authentique, les pays et villes méconnus, et les quartiers locaux.
Mise en valeur spéciale : CAMEROUN (Yaoundé, Douala, Foumban, Kribi, Bafoussam, Maroua).
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# 100 SCÉNARIOS DE TEST SUR L'AFRIQUE, LE CAMEROUN ET LES QUARTIERS AUTHENTIQUES
# ------------------------------------------------------------------------------
AFRICAN_SCENARIOS = [
    # ==========================================================================
    # CAMEROUN (En vedette - 25 scénarios)
    # ==========================================================================
    {
        "city": "Yaoundé",
        "country": "Cameroun",
        "tests": [
            "Fais-moi découvrir le Mont Fébé à Yaoundé et le Musée National au centre-ville avec leurs secrets historiques.",
            "Où manger le meilleur Ndolé authentique et le Poulet DG dans le quartier Bastos ou à Mvog-Ada ?",
            "Organise un itinéraire à pied à Yaoundé reliant le Monument de la Réunification, le Bois Sainte-Anastasie et le marché central.",
            "Comment explorer en immersion l'effervescence du marché Mokolo tout en découvrant les tissus wax et le koki chaud ?",
            "Quelles sont les galeries d'art contemporain et centres culturels incontournables dans le quartier Bastos ?"
        ]
    },
    {
        "city": "Douala",
        "country": "Cameroun",
        "tests": [
            "Raconte l'histoire de la Pagode de Manga Bell (Palais des Rois Bell) et de l'époque coloniale dans le quartier Bonanjo.",
            "Où déguster le meilleur poisson braisé du fleuve Wouri le soir dans l'ambiance animée du quartier Deido ?",
            "Planifie un parcours pédestre à Bonanjo reliant le Musée Maritime, la Place du Gouvernement et la cathédrale Saint-Pierre-et-Paul.",
            "Quels sont les spots branchés et galeries d'art (comme Doual'art) à visiter dans le quartier Bonapriso ?",
            "Quelles astuces pour négocier et dénicher des merveilles d'artisanat local au marché des fleurs et d'Akwa ?"
        ]
    },
    {
        "city": "Kribi",
        "country": "Cameroun",
        "tests": [
            "Présente-moi les spectaculaires Chutes de la Lobé qui se jettent directement dans l'Océan Atlantique.",
            "Où savourer les légendaires crevettes royales grillées de Kribi sur la plage de Grand Batanga ?",
            "Organise une excursion en pirogue sur la rivière Lobé à la rencontre de la communauté Bagyeli.",
            "Quelles sont les plus belles plages sauvages de sable blanc entre Kribi et le phare colonial ?",
            "Quels conseils pour un séjour écologique et reposant dans les écolodges de la côte camerounaise ?"
        ]
    },
    {
        "city": "Foumban",
        "country": "Cameroun",
        "tests": [
            "Raconte-moi l'histoire fascinante du Sultanat Bamoun, du Roi Njoya et de son alphabet secret Shü-mom au Palais Royal de Foumban.",
            "Quels sont les ateliers de fonderie de bronze et de sculpture sur bois à visiter dans la rue des artisans de Foumban ?",
            "Décris l'architecture extraordinaire du Musée des Rois Bamoun inauguré en forme d'araignée et de serpent à deux têtes.",
            "Où goûter aux spécialités culinaires du pays Bamoun sur la place du marché royal ?",
            "Quelles sont les traditions et rites de la grande fête culturelle du Nguon célébrée à Foumban ?"
        ]
    },
    {
        "city": "Bafoussam",
        "country": "Cameroun",
        "tests": [
            "Fais-moi visiter la majestueuse Chefferie Bamiléké de Bandjoun et ses cases traditionnelles aux toits de chaume.",
            "Quels sont les rituels sacrés, les danses et le rôle des notables dans les royaumes traditionnels de l'Ouest camerounais ?",
            "Trace une journée de découverte reliant la chefferie de Bafoussam, les chutes de la Métché et les collines verdoyantes.",
            "Où savourer le plat traditionnel Taro à la sauce jaune (sauce achu) préparé selon les règles de l'art ?",
            "Comment aborder avec respect et dignité les lieux sacrés et les reliques ancestrales en pays bamiléké ?"
        ]
    },

    # ==========================================================================
    # BÉNIN (Ouidah, Ganvié, Cotonou, Abomey - 10 scénarios)
    # ==========================================================================
    {
        "city": "Ouidah",
        "country": "Bénin",
        "tests": [
            "Raconte l'histoire poignante de la Route des Esclaves jusqu'à la Porte du Non-Retour sur la plage de Ouidah.",
            "Présente-moi le Temple des Pythons sacrés et la signification spirituelle du culte Vodun au Bénin.",
            "Trace un parcours pédestre à Ouidah reliant le fort portugais Saint-Jean-Baptiste, la basilique et la forêt sacrée de Kpassè.",
            "Quelles sont les œuvres d'art vaudou contemporaines à découvrir à la Fondation Zinsou de Ouidah ?",
            "Où savourer un repas béninois traditionnel (Amiwo au poulet bicyclette) près de la lagune ?"
        ]
    },
    {
        "city": "Cotonou",
        "country": "Bénin",
        "tests": [
            "Fais-moi vivre l'atmosphère unique de Ganvié, la célèbre cité lacustre sur pilotis du lac Nokoué.",
            "Comment naviguer dans l'immense marché Dantokpa à Cotonou et dénicher des épices et tissus authentiques ?",
            "Quels restaurants et bars chaleureux explorer le soir dans le quartier vivant de la Haie Vive ?",
            "Présente-moi les Palais Royaux d'Abomey et les bas-reliefs de la dynastie des rois du Danxomé.",
            "Quelles précautions et conseils d'étiquette pour visiter Ganvié en pirogue dans le respect des habitants ?"
        ]
    },

    # ==========================================================================
    # TOGO (Lomé, Aneho, Kpalimé - 10 scénarios)
    # ==========================================================================
    {
        "city": "Lomé",
        "country": "Togo",
        "tests": [
            "Raconte l'histoire du Grand Marché d'Assigamé et le rôle légendaire des Nana Benz à Lomé.",
            "Présente-moi le Marché des fétiches d'Akodésséwa et son rôle dans la médecine traditionnelle togolais.",
            "Planifie une balade à pied le long du front de mer de Lomé, de Kodjoviakopé jusqu'au Palais de Lomé.",
            "Où manger le meilleur Ayimolou au poisson et goûter à la bière locale au quartier Bè ?",
            "Quels espaces d'art contemporain et jardins botaniques explorer au Palais de Lomé réhabilité ?"
        ]
    },
    {
        "city": "Kpalimé",
        "country": "Togo",
        "tests": [
            "Présente-moi la région de Kpalimé, le Mont Kloto et ses sentiers de cascades au milieu des plantations de cacao et café.",
            "Quels ateliers d'artisans (batiks, céramique, poterie) visiter dans le centre de Kpalimé ?",
            "Organise une randonnée pédestre jusqu'à la cascade de Kpime ou de Womé avec un guide local.",
            "Quels fruits tropicaux d'exception et plats du terroir togolais déguster sur le marché de Kpalimé ?",
            "Quels sont les trésors coloniaux et l'histoire de la ville historique d'Aného au bord du lac Togo ?"
        ]
    },

    # ==========================================================================
    # RWANDA (Kigali, Nyamirambo, Butare - 10 scénarios)
    # ==========================================================================
    {
        "city": "Kigali",
        "country": "Rwanda",
        "tests": [
            "Fais-moi découvrir le quartier historique et vibrant de Nyamirambo à Kigali à travers sa visite communautaire.",
            "Où goûter au célèbre café d'origine rwandaise (Bourbon) et visiter les milk bars traditionnels ?",
            "Trace un parcours pédestre à Kigali passant par le centre culturel Inema Arts et le quartier diplomatique de Kiyovu.",
            "Explique la portée historique et mémorielle du Mémorial du Génocide de Gisozi à Kigali.",
            "Quels marchés artisanaux comme Kimironko permettent de découvrir l'artisanat géométrique de l'Agaseke ?"
        ]
    },
    {
        "city": "Huye",
        "country": "Rwanda",
        "tests": [
            "Présente-moi l'ancienne capitale royale de Nyanza (Rukari) et les majestueuses vaches Inyambo aux longues cornes.",
            "Fais-moi visiter le Musée Ethnographique National de Huye (Butare) et ses collections de vannerie.",
            "Organise une découverte de la forêt primaire de Nyungwe avec sa passerelle suspendue dans la canopée.",
            "Quels sont les secrets de l'art traditionnel de l'Imigongo fait à partir de bouse de vache et de pigments naturels ?",
            "Comment fonctionne la propreté exemplaire de Kigali et la journée citoyenne de l'Umuganda ?"
        ]
    },

    # ==========================================================================
    # CAP-VERT (Mindelo, Cidade Velha - 10 scénarios)
    # ==========================================================================
    {
        "city": "Mindelo",
        "country": "Cap-Vert",
        "tests": [
            "Raconte l'âme musicale de Mindelo sur l'île de São Vicente et l'héritage de la Diva aux pieds nus Cesária Évora.",
            "Où écouter de la Morna et du Coladeira en direct le soir dans les tavernes du quartier colonial ?",
            "Planifie un parcours pédestre à Mindelo partant de la Praça Nova vers le marché aux poissons et la réplique de la Tour de Belém.",
            "Fais-moi découvrir la plage de Laginha et les collines volcaniques du Monte Verde dominant l'océan.",
            "Quelles traditions et costumes caractérisent le spectaculaire Carnaval de Mindelo inspiré de Rio ?"
        ]
    },
    {
        "city": "Praia",
        "country": "Cap-Vert",
        "tests": [
            "Présente-moi Cidade Velha sur l'île de Santiago, première cité coloniale européenne sous les tropiques classée UNESCO.",
            "Raconte l'histoire de la forteresse royale São Filipe et du Pilori de Cidade Velha face à l'Atlantique.",
            "Où savourer la vraie Cachupa capverdienne mijotée au maïs, haricots et viandes savoureuses au quartier du Plateau ?",
            "Comment explorer le marché animé de Sucupira à Praia pour vivre le quotidien des habitants de Santiago ?",
            "Quelles sont les randonnées secrètes dans la vallée luxuriante de Serra Malagueta ?"
        ]
    },

    # ==========================================================================
    # SÃO TOMÉ-ET-PRÍNCIPE (10 scénarios)
    # ==========================================================================
    {
        "city": "São Tomé",
        "country": "São Tomé-et-Príncipe",
        "tests": [
            "Raconte l'histoire des anciennes plantations coloniales de cacao (les Roças) comme la Roça Agostinho Neto.",
            "Pourquoi São Tomé était-elle surnommée l'île chocolat et où déguster le meilleur chocolat noir d'origine de Claudio Corallo ?",
            "Planifie un itinéraire le long de la côte est menant à la spectaculaire aiguille volcanique du Cão Grande.",
            "Quels sont les secrets des maisons en bois sur pilotis et du fort colonial de São Sebastião ?",
            "Où goûter au Calulu traditionnel, ragoût de poisson séché aux herbes médicinales locales ?"
        ]
    },
    {
        "city": "Príncipe",
        "country": "São Tomé-et-Príncipe",
        "tests": [
            "Présente-moi l'île de Príncipe, réserve de biosphère de l'UNESCO, ses forêts vierges et ses plages désertes comme Banana Beach.",
            "Fais-moi visiter la capitale miniature Santo António et ses maisons coloniales créoles au bord de la rivière.",
            "Comment observer la ponte des tortues marines et les oiseaux endémiques sur les sentiers écologiques ?",
            "Quelles sont les initiatives écotouristiques durables à la Roça Sundy où la théorie de la relativité d'Einstein fut testée ?",
            "Quels conseils pour se déplacer entre les îles et vivre la philosophie locale du « Leve-Leve » (douceur de vivre) ?"
        ]
    },

    # ==========================================================================
    # MADAGASCAR (Antananarivo, Majunga - 10 scénarios)
    # ==========================================================================
    {
        "city": "Antananarivo",
        "country": "Madagascar",
        "tests": [
            "Raconte l'histoire royale du Rova de Manjakamiadana sur la plus haute colline d'Antananarivo dominant la ville.",
            "Comment explorer le marché traditionnel d'Analakely et descendre les célèbres escaliers historiques d'Antaninarenina ?",
            "Où savourer le plat national malgache Romazava au zébu et au brède mafana dans le quartier d'Isoraka ?",
            "Fais-moi découvrir la colline royale sacrée d'Ambohimanga, berceau de la royauté Merina classé par l'UNESCO.",
            "Quels ateliers d'artisanat du bois marqueté et du papier Antemoro visiter dans les ruelles de Tana ?"
        ]
    },
    {
        "city": "Sainte-Marie",
        "country": "Madagascar",
        "tests": [
            "Raconte l'histoire légendaire des pirates et forbans réfugiés sur l'île Sainte-Marie (Nosy Boraha) au 17e siècle.",
            "Où se trouve le cimetière des pirates de l'île aux Forbans et quelles épaves reposent dans la baie ?",
            "Comment assister de manière responsable à la migration et aux sauts des baleines à bosse dans le canal de Sainte-Marie ?",
            "Organise une balade en pirogue traditionnelle sur l'Île aux Nattes avec ses lagons turquoise protégés par la barrière.",
            "Quelles plantations de vanille, de cannelle et de girofle visiter pour sentir les effluves parfumées de l'île ?"
        ]
    },

    # ==========================================================================
    # GABON (Libreville, Lambaréné - 5 scénarios)
    # ==========================================================================
    {
        "city": "Libreville",
        "country": "Gabon",
        "tests": [
            "Présente-moi l'histoire du quartier Mont-Bouët et de son marché cosmopolite à Libreville.",
            "Où déguster du poisson braisé et du Poulet Nyembwe à la sauce aux graines de palme dans le quartier animé de Louis ?",
            "Fais-moi visiter l'église Saint-Michel de Nkembo avec ses remarquables colonnes sculptées par un artiste aveugle.",
            "Organise une escapade historique jusqu'à Lambaréné sur le fleuve Ogooué pour visiter l'hôpital du docteur Albert Schweitzer.",
            "Quels sont les chefs-d'œuvre de la sculpture sur pierre de Mbigou et des masques Fang au Musée National de Libreville ?"
        ]
    },

    # ==========================================================================
    # COMORES & ZANZIBAR MÉCONNUE (10 scénarios)
    # ==========================================================================
    {
        "city": "Moroni",
        "country": "Comores",
        "tests": [
            "Présente-moi l'architecture ancienne de la médina de Badjanani à Moroni et la Grande Mosquée du Vendredi face au port.",
            "Où sentir les arômes des alambics d'Ylang-Ylang et de vanille sur les pentes du volcan Karthala ?",
            "Trace une promenade pédestre au marché Volo-Volo pour découvrir la vie quotidienne et l'artisanat comorien.",
            "Explique la tradition grandiose du Grand Mariage (Anda) aux Comores et son importance sociale.",
            "Quelles plages de lave noire et lagons blancs secrets explorer au nord de la Grande Comore ?"
        ]
    },
    {
        "city": "Stone Town",
        "country": "Zanzibar",
        "tests": [
            "Raconte l'histoire des portes en bois sculptées d'influence swahilie, arabe et indienne dans les ruelles de Stone Town.",
            "Fais-moi découvrir les étals du marché nocturne de Forodhani Gardens et goûter à la fameuse Zanzibar pizza.",
            "Organise un itinéraire pédestre reliant la Maison des Merveilles (Beit-al-Ajaib), l'Ancien Fort et la maison de Freddie Mercury.",
            "Quelle est l'histoire poignante de l'ancien marché aux esclaves et de la cathédrale anglicane de Stone Town ?",
            "Quelles plantations d'épices (Spice Tour) visiter aux alentours pour toucher et sentir clou de girofle, muscade et cardamome ?"
        ]
    }
]


def run_african_benchmark(
    max_tests: int = 100,
    delay_between_calls: float = 2.0,
    output_dir: str = "training_evaluation_output/africa_evaluation_data"
):
    """
    Exécute le benchmark et rodage spécialisé Afrique et Cameroun.
    """
    out_path = BASE_DIR / output_dir
    out_path.mkdir(exist_ok=True, parents=True)

    print("=" * 75)
    print("🌍 SMART TOUR GUIDE AI — SPÉCIAL AFRIQUE, CAMEROUN & QUARTIERS LOCAUX")
    print(f"📊 Objectif : {max_tests} requêtes culturelles et patrimoniales")
    print(f"🇨🇲 Mise à l'honneur : Cameroun (Yaoundé, Douala, Kribi, Foumban, Bafoussam)")
    print(f"⏱️ Pause anti-rate-limit : {delay_between_calls}s par requête")
    print(f"💾 Dossier de sortie : {out_path}")
    print("=" * 75)

    agent = TourGuideAgent()
    results = []
    fine_tuning_records = []

    total_scenarios = []
    for d in AFRICAN_SCENARIOS:
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
        country = item["country"]
        query = item["query"]

        print(f"\n[{idx:03d}/{len(total_scenarios):03d}] 📍 {dest} ({country}) : « {query[:65]}... »")

        session = TourSession.objects.create(
            title=f"Africa #{idx} - {dest} ({country})",
            destination=f"{dest}, {country}"
        )

        t0 = time.time()
        max_retries = 3
        test_result = {
            "test_id": idx,
            "destination": dest,
            "country": country,
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
                    destination=f"{dest}, {country}"
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

                fine_tuning_records.append({
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": query},
                        {"role": "assistant", "content": reply}
                    ],
                    "metadata": {
                        "destination": dest,
                        "country": country,
                        "features_count": len(features),
                        "itinerary_count": len(itinerary)
                    }
                })

                print(f"    ✅ Succès ({elapsed}s) | 📍 POIs: {len(features)} | 🚶 Étapes: {len(itinerary)} | 📝 Réponse: {len(reply)} car.")
                break

            except Exception as e:
                err_str = str(e)
                logger.warning(f"Tentative {attempt + 1}/{max_retries} pour {dest}: {err_str}")
                if "rate_limit" in err_str.lower() or "429" in err_str:
                    sleep_sec = 6.0 * (attempt + 1)
                    print(f"    ⏳ Rate limit détecté, pause adaptative de {sleep_sec}s...")
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
    # SAUVEGARDE DU DATASET DE FINE-TUNING SPÉCIAL AFRIQUE (JSONL)
    # --------------------------------------------------------------------------
    dataset_file = out_path / "tour_guide_africa_finetuning_dataset.jsonl"
    with open(dataset_file, "w", encoding="utf-8") as f:
        for record in fine_tuning_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # --------------------------------------------------------------------------
    # SAUVEGARDE DU RAPPORT D'ÉVALUATION (JSON)
    # --------------------------------------------------------------------------
    report_file = out_path / "africa_benchmark_report.json"
    summary_metrics = {
        "timestamp": datetime.now().isoformat(),
        "theme": "Afrique méconnue & Cameroun",
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
    md_file = out_path / "africa_benchmark_summary.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write("# 🌍 Rapport de Rodage — Spécial Afrique & Cameroun\n\n")
        f.write(f"- **Date** : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **Zone d'exploration** : Cameroun, Bénin, Togo, Rwanda, Cap-Vert, São Tomé-et-Príncipe, Madagascar, Gabon, Comores\n")
        f.write(f"- **Nombre de requêtes exécutées** : {len(results)}\n")
        f.write(f"- **Taux de succès** : **{summary_metrics['success_rate_percent']}%** ({successful_count}/{len(results)})\n")
        f.write(f"- **Temps total** : {total_time}s (moyenne {summary_metrics['avg_duration_seconds']}s/test)\n")
        f.write(f"- **Lieux & POIs géocodés** : {total_pois_found} POIs réels\n")
        f.write(f"- **Circuits & étapes ordonnées** : {total_itinerary_stops} étapes\n")
        f.write(f"- **Paires d'entraînement sauvegardées** : {len(fine_tuning_records)} exemples JSONL\n\n")

        f.write("## 🏆 Détail des Tests par Destination & Quartier\n\n")
        f.write("| # | Ville | Pays | Thématique & Requête | POIs | Étapes | Durée | Statut |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for r in results:
            stat_icon = "✅ Succès" if r["success"] else "❌ Erreur"
            f.write(f"| {r['test_id']:02d} | {r['destination']} | {r['country']} | {r['query'][:50]}... | {r['features_count']} | {r['itinerary_stops_count']} | {r['duration_seconds']}s | {stat_icon} |\n")

    print("\n" + "=" * 75)
    print("🎉 RODAGE AFRIQUE & CAMEROUN TERMINÉ AVEC SUCCÈS !")
    print(f"📈 Taux de réussite : {summary_metrics['success_rate_percent']}%")
    print(f"📍 Total POIs découverts : {total_pois_found}")
    print(f"📁 Dataset d'entraînement généré : {dataset_file.name}")
    print(f"📊 Rapport détaillé : {report_file.name}")
    print(f"📑 Synthèse Markdown : {md_file.name}")
    print("=" * 75)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script de rodage et entraînement sur l'Afrique et le Cameroun")
    parser.add_argument("--count", type=int, default=100, help="Nombre de tests à exécuter (1 à 100, défaut 100)")
    parser.add_argument("--delay", type=float, default=2.0, help="Délai entre les requêtes en secondes (défaut 2.0s)")
    parser.add_argument("--output", type=str, default="training_evaluation_output/africa_evaluation_data", help="Dossier de sortie")

    args = parser.parse_args()
    run_african_benchmark(
        max_tests=args.count,
        delay_between_calls=args.delay,
        output_dir=args.output
    )
