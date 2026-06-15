"""
Service d'analyse IA pour les plaintes avec prompts spécialisés
"""
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger(__name__)

@dataclass
class AnalysisResult:
    """Résultat d'une analyse IA"""
    success: bool
    content: str
    confidence: float
    metadata: Dict[str, Any]
    error: Optional[str] = None

class ComplaintAnalysisService:
    """Service d'analyse complète des plaintes avec IA"""
    
    def __init__(self, llm_provider=None):
        """
        Initialise le service d'analyse
        
        Args:
            llm_provider: Provider LLM pour les requêtes d'analyse
        """
        self.llm_provider = llm_provider
        self.prompts = self._initialize_prompts()
    
    def _initialize_prompts(self) -> Dict[str, str]:
        """Initialise les prompts spécialisés pour chaque type d'analyse"""
        return {
            "sentiment": """Analyse le sentiment d'une plainte hospitaliere et attribue un SCORE PRECIS et CALIBRE.
(Prompt V2 valide par banc d'essai: erreur moyenne 0.071 vs 0.893, granularite x2.7, signes corrects.)

PROCEDE EN 2 ETAPES:
ETAPE 1 - LE SIGNE (le plus important):
  - Le plaignant exprime un reproche, une insatisfaction, une colere -> score NEGATIF (strictement < 0).
  - Simple demande d'information, constat administratif, question SANS reproche -> NEUTRE (entre -0.05 et +0.05).
  - Remerciement, satisfaction, eloge -> score POSITIF (strictement > 0).
  INTERDIT: donner un score negatif a une plainte neutre ou positive, ou positif a une plainte negative.
ETAPE 2 - LA MAGNITUDE selon l'intensite (utilise TOUTE l'echelle, precis au centieme, jamais une valeur par defaut):
  cote NEGATIF: -1.00 a -0.85 colere extreme/danger vital/erreur grave | -0.84 a -0.55 forte insatisfaction/prejudice | -0.54 a -0.25 insatisfaction moderee | -0.24 a -0.06 gene legere ("un peu", "dans l'ensemble ca a ete").
  NEUTRE: -0.05 a +0.05.
  cote POSITIF: +0.06 a +0.50 plutot satisfait (avec reserve) | +0.51 a +0.84 satisfait | +0.85 a +1.00 tres reconnaissant.
Deux plaintes d'intensites differentes ne doivent JAMAIS avoir le meme score. Le score est coherent avec "intensite_emotionnelle".

EXEMPLES calibres (couvrant toute l'echelle):
- "Scandaleux, une erreur de medicament a failli tuer mon pere" -> {{"score_sentiment": -0.95, "sentiment_principal": "negatif", "intensite_emotionnelle": "elevee"}}
- "Mon operation a ete annulee trois fois sans explication, j'ai perdu confiance" -> {{"score_sentiment": -0.70, "sentiment_principal": "negatif", "intensite_emotionnelle": "elevee"}}
- "On ne m'a pas explique mon traitement a la sortie" -> {{"score_sentiment": -0.42, "sentiment_principal": "negatif", "intensite_emotionnelle": "moderee"}}
- "L'attente etait un peu longue mais ca a ete" -> {{"score_sentiment": -0.15, "sentiment_principal": "negatif", "intensite_emotionnelle": "faible"}}
- "Je voudrais une copie de mon dossier medical et la procedure" -> {{"score_sentiment": 0.00, "sentiment_principal": "neutre", "intensite_emotionnelle": "faible"}}
- "Globalement satisfait, le medecin a ete a l'ecoute malgre l'attente" -> {{"score_sentiment": 0.50, "sentiment_principal": "positif", "intensite_emotionnelle": "moderee"}}
- "Un immense merci, l'equipe a ete extraordinaire" -> {{"score_sentiment": 0.93, "sentiment_principal": "positif", "intensite_emotionnelle": "elevee"}}

Plainte a analyser:
{complaint_text}

Reponds UNIQUEMENT avec ce JSON (score_sentiment = nombre a 2 decimales entre -1.0 et 1.0, signe coherent avec l'etape 1):
{{
    "sentiment_principal": "positif/negatif/neutre",
    "intensite_emotionnelle": "faible/moderee/elevee",
    "score_sentiment": -0.42,
    "mots_cles_emotionnels": ["mot1", "mot2"],
    "recommandations_reponse": "conseils pour la tonalite de reponse"
}}
""",
            
            "summary": """
Rédige un résumé clair et synthétique de cette plainte médicale.

Plainte à analyser:
{complaint_text}

Instructions:
1. Résume les faits principaux en 3-5 phrases maximum
2. Identifie les services/personnes concernés
3. Précise la nature du problème
4. Indique la demande du plaignant

Format de réponse JSON:
{{
    "resume_executif": "résumé en 3-5 phrases",
    "faits_principaux": ["fait1", "fait2", "fait3"],
    "services_concernes": ["service1", "service2"],
    "nature_probleme": "description du type de problème",
    "demande_plaignant": "ce que demande le plaignant",
    "date_incident": "date mentionnée ou 'non précisée'",
    "gravite_estimee": "faible/modérée/élevée"
}}
""",
            
            "contacts": """
Identifie tous les contacts (personnes, services, départements) mentionnés dans cette plainte.

Plainte à analyser:
{complaint_text}

Instructions:
1. Extrais tous les noms de personnes mentionnées
2. Identifie les services/départements
3. Note les fonctions/rôles mentionnés
4. Indique les numéros de téléphone, emails si présents

Format de réponse JSON:
{{
    "personnes_mentionnees": [
        {{
            "nom": "nom de la personne",
            "fonction": "fonction si mentionnée",
            "service": "service si mentionné",
            "contexte": "dans quel contexte cette personne est mentionnée"
        }}
    ],
    "services_departements": [
        {{
            "nom": "nom du service",
            "contexte": "comment ce service est impliqué"
        }}
    ],
    "coordonnees_trouvees": [
        {{
            "type": "téléphone/email/adresse",
            "valeur": "la coordonnée",
            "appartient_a": "à qui appartient cette coordonnée"
        }}
    ],
    "interlocuteurs_cles": ["personnes importantes à contacter"]
}}
""",
            
            "legal_response": """
Rédige une réponse juridique officielle à cette plainte au nom du Responsable Qualité.

Contexte de la plainte:
{complaint_text}

Résumé de l'analyse:
{analysis_summary}

Instructions:
1. Rédige une réponse officielle et professionnelle
2. Utilise un ton juridique et favorable à l'établissement
3. Évite toute admission de faute
4. Propose des solutions constructives
5. Assure le suivi approprié

Format de réponse JSON:
{{
    "reponse_officielle": "texte complet de la réponse",
    "points_cles": ["point1", "point2"],
    "actions_proposees": ["action1", "action2"],
    "engagement_suivi": "description de l'engagement de suivi",
    "tone_juridique": "description de l'approche juridique utilisée",
    "recommandations_internes": ["recommandation1", "recommandation2"]
}}
""",
            
            "extract_complaint_data": """
Tu es un assistant spécialisé dans l'extraction de données à partir de documents de plaintes hospitalières.

Texte du document de plainte à analyser:
{complaint_text}

Instructions:
1. Extrais toutes les informations pertinentes du document
2. Identifie les informations du plaignant (nom, prénom, email, téléphone)
3. Détermine l'objet/titre de la plainte
4. Extrais la description détaillée des faits
5. Identifie la date de l'incident si mentionnée
6. Détermine le service concerné si mentionné
7. Évalue la priorité suggérée (URGENT, ELEVE, MOYEN, BAS)

Important: Si une information n'est pas trouvée dans le document, mets null.

Format de réponse JSON strictement requis:
{{
    "plaignant": {{
        "nom": "nom de famille du plaignant ou null",
        "prenom": "prénom du plaignant ou null",
        "email": "email du plaignant ou null",
        "telephone": "numéro de téléphone ou null"
    }},
    "plainte": {{
        "titre": "objet/titre résumant la plainte (max 100 caractères)",
        "description": "description complète des faits relatés",
        "date_incident": "date au format YYYY-MM-DD ou null",
        "service_concerne": "nom du service hospitalier mentionné ou null",
        "mode_reception": "courrier/email/oral/autre selon le document"
    }},
    "analyse": {{
        "priorite_suggeree": "URGENT/ELEVE/MOYEN/BAS",
        "mots_cles": ["mot1", "mot2", "mot3"],
        "gravite_estimee": "faible/modérée/élevée",
        "resume_court": "résumé en 2-3 phrases maximum"
    }},
    "confiance_extraction": {{
        "score_global": 0.0 à 1.0,
        "champs_incertains": ["liste des champs extraits avec incertitude"]
    }}
}}
""",

            # ===== PROMPTS SPÉCIALISÉS POUR EXTRACTION HAUTE CONFIANCE =====
            
            "extract_plaignant": """
Tu es un expert en extraction d'informations de contact à partir de documents de plaintes hospitalières françaises.

DOCUMENT À ANALYSER:
---
{complaint_text}
---

OBJECTIF: Extraire les informations du PLAIGNANT (la personne qui DÉPOSE la plainte).

RÈGLES D'IDENTIFICATION DU PLAIGNANT:
1. C'est la personne qui SIGNE le document (en fin de lettre)
2. C'est celle qui dit "je", "nous", "ma mère", "mon père" 
3. Ses coordonnées sont souvent en haut à gauche (expéditeur)
4. Son nom apparaît après "Cordialement", "Sincères salutations", etc.

À NE PAS CONFONDRE AVEC:
- Le DESTINATAIRE (Directeur, Service Qualité, Médecin chef...)
- Le personnel hospitalier mentionné dans la plainte
- Les témoins ou accompagnants

EXEMPLES DE PATTERNS À CHERCHER:
- "Monsieur Jean DUPONT" en signature → nom="DUPONT", prenom="Jean"
- "Mme Marie MARTIN" → nom="MARTIN", prenom="Marie"  
- "Cordialement, Pierre Durand" → nom="Durand", prenom="Pierre"
- Email dans les coordonnées expéditeur: jean.dupont@email.com
- Téléphone: 06 12 34 56 78 ou 0612345678

RÉPONDS UNIQUEMENT AVEC CE JSON (pas de texte avant/après):
{{
    "nom": "NOM de famille en MAJUSCULES ou null si non trouvé",
    "prenom": "Prénom avec majuscule initiale ou null si non trouvé",
    "email": "email@exemple.com ou null si non trouvé",
    "telephone": "0612345678 ou null si non trouvé",
    "confiance": 0.8
}}
""",

            "extract_service": """
Tu es un expert en identification des services hospitaliers dans les documents de plaintes.

Texte du document à analyser:
{complaint_text}

OBJECTIF: Identifier le(s) service(s) hospitalier(s) concerné(s) par la plainte.

Instructions précises:
1. Cherche les noms de services: Urgences, Cardiologie, Chirurgie, Radiologie, Maternité, etc.
2. Identifie les personnes du personnel mentionnées (médecins, infirmiers, aides-soignants)
3. Note le lieu précis si mentionné (étage, bâtiment, chambre)

Services hospitaliers courants:
- Urgences, SAMU, Réanimation
- Cardiologie, Pneumologie, Neurologie
- Chirurgie (orthopédique, viscérale, cardiaque)
- Radiologie, Imagerie médicale
- Maternité, Pédiatrie, Néonatologie
- Oncologie, Hématologie
- Psychiatrie
- Médecine générale, Médecine interne
- Laboratoire, Pharmacie
- Administration, Accueil

IMPORTANT: Retourne UNIQUEMENT le JSON, sans texte avant ou après.

Format JSON STRICT:
{{
    "service_principal": "Nom du service principal concerné ou null",
    "services_secondaires": ["autres services mentionnés"],
    "personnel_mentionne": [
        {{"nom": "Dr Dupont", "fonction": "médecin", "service": "Cardiologie"}}
    ],
    "lieu_precis": "étage/bâtiment/chambre ou null",
    "confiance": 0.0 à 1.0
}}
""",

            "extract_description": """
Tu es un expert en analyse et synthèse de plaintes hospitalières.

Texte du document à analyser:
{complaint_text}

OBJECTIF: Extraire et structurer la description des faits de la plainte.

Instructions précises:
1. Identifie l'objet/titre de la plainte (1 phrase courte)
2. Résume les faits principaux de manière chronologique
3. Identifie la date de l'incident si mentionnée
4. Note le mode de réception du document (courrier, email, oral, etc.)
5. Extrait les demandes/attentes du plaignant

IMPORTANT: Retourne UNIQUEMENT le JSON, sans texte avant ou après.

Format JSON STRICT:
{{
    "titre": "Objet de la plainte en 1 phrase (max 100 caractères)",
    "description": "Description complète et structurée des faits",
    "date_incident": "YYYY-MM-DD ou null",
    "mode_reception": "courrier/email/oral/formulaire/autre",
    "demandes_plaignant": ["demande 1", "demande 2"],
    "confiance": 0.0 à 1.0
}}
""",

            "extract_analyse": """
Tu es un expert en analyse de risques et priorisation des plaintes hospitalières.

Texte du document à analyser:
{complaint_text}

OBJECTIF: Analyser la gravité et la priorité de cette plainte.

Critères de priorisation:
- URGENT: Mise en danger de la vie, erreur médicale grave, risque juridique immédiat
- ELEVE: Préjudice significatif, défaut de soins important, plainte récurrente
- MOYEN: Insatisfaction sur la prise en charge, délais excessifs, communication défaillante
- BAS: Problème mineur, suggestion d'amélioration, remarque générale

Instructions:
1. Évalue la gravité des faits décrits
2. Identifie les mots-clés importants
3. Propose une priorité de traitement
4. Rédige un résumé exécutif en 2-3 phrases

IMPORTANT: Retourne UNIQUEMENT le JSON, sans texte avant ou après.

Format JSON STRICT:
{{
    "priorite_suggeree": "URGENT/ELEVE/MOYEN/BAS",
    "gravite_estimee": "faible/modérée/élevée/critique",
    "mots_cles": ["mot1", "mot2", "mot3", "mot4", "mot5"],
    "resume_court": "Résumé en 2-3 phrases",
    "risques_identifies": ["risque 1", "risque 2"],
    "confiance": 0.0 à 1.0
}}
"""
        }
    
    def analyze_sentiment(self, complaint_text: str) -> AnalysisResult:
        """Analyse le sentiment de la plainte"""
        logger.info("Démarrage de l'analyse de sentiment")
        
        if not self.llm_provider:
            return AnalysisResult(
                success=False,
                content="",
                confidence=0.0,
                metadata={},
                error="LLM provider non configuré"
            )
        
        try:
            prompt = self.prompts["sentiment"].format(complaint_text=complaint_text)
            response = self.llm_provider.generate_response(prompt)
            
            # Parse la réponse JSON
            try:
                result = json.loads(response)
                logger.info("Analyse de sentiment terminée avec succès")
                return AnalysisResult(
                    success=True,
                    content=json.dumps(result, ensure_ascii=False, indent=2),
                    confidence=0.9,
                    metadata={"analysis_type": "sentiment", "model_used": self.llm_provider.model_name}
                )
            except json.JSONDecodeError:
                logger.warning("Réponse LLM non-JSON pour l'analyse de sentiment")
                return AnalysisResult(
                    success=True,
                    content=response,
                    confidence=0.7,
                    metadata={"analysis_type": "sentiment", "format": "text"}
                )
                
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de sentiment: {str(e)}")
            return AnalysisResult(
                success=False,
                content="",
                confidence=0.0,
                metadata={},
                error=str(e)
            )
    
    def generate_summary(self, complaint_text: str) -> AnalysisResult:
        """Génère un résumé synthétique de la plainte"""
        logger.info("Démarrage de la génération de résumé")
        
        if not self.llm_provider:
            return AnalysisResult(
                success=False,
                content="",
                confidence=0.0,
                metadata={},
                error="LLM provider non configuré"
            )
        
        try:
            prompt = self.prompts["summary"].format(complaint_text=complaint_text)
            response = self.llm_provider.generate_response(prompt)
            
            try:
                result = json.loads(response)
                logger.info("Génération de résumé terminée avec succès")
                return AnalysisResult(
                    success=True,
                    content=json.dumps(result, ensure_ascii=False, indent=2),
                    confidence=0.9,
                    metadata={"analysis_type": "summary", "model_used": self.llm_provider.model_name}
                )
            except json.JSONDecodeError:
                logger.warning("Réponse LLM non-JSON pour le résumé")
                return AnalysisResult(
                    success=True,
                    content=response,
                    confidence=0.7,
                    metadata={"analysis_type": "summary", "format": "text"}
                )
                
        except Exception as e:
            logger.error(f"Erreur lors de la génération de résumé: {str(e)}")
            return AnalysisResult(
                success=False,
                content="",
                confidence=0.0,
                metadata={},
                error=str(e)
            )
    
    def extract_contacts(self, complaint_text: str) -> AnalysisResult:
        """Extrait les contacts mentionnés dans la plainte"""
        logger.info("Démarrage de l'extraction de contacts")
        
        if not self.llm_provider:
            return AnalysisResult(
                success=False,
                content="",
                confidence=0.0,
                metadata={},
                error="LLM provider non configuré"
            )
        
        try:
            prompt = self.prompts["contacts"].format(complaint_text=complaint_text)
            response = self.llm_provider.generate_response(prompt)
            
            try:
                result = json.loads(response)
                logger.info("Extraction de contacts terminée avec succès")
                return AnalysisResult(
                    success=True,
                    content=json.dumps(result, ensure_ascii=False, indent=2),
                    confidence=0.8,
                    metadata={"analysis_type": "contacts", "model_used": self.llm_provider.model_name}
                )
            except json.JSONDecodeError:
                logger.warning("Réponse LLM non-JSON pour l'extraction de contacts")
                return AnalysisResult(
                    success=True,
                    content=response,
                    confidence=0.6,
                    metadata={"analysis_type": "contacts", "format": "text"}
                )
                
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de contacts: {str(e)}")
            return AnalysisResult(
                success=False,
                content="",
                confidence=0.0,
                metadata={},
                error=str(e)
            )
    
    def generate_legal_response(self, complaint_text: str, analysis_summary: str) -> AnalysisResult:
        """Génère une réponse juridique officielle"""
        logger.info("Démarrage de la génération de réponse juridique")
        
        if not self.llm_provider:
            return AnalysisResult(
                success=False,
                content="",
                confidence=0.0,
                metadata={},
                error="LLM provider non configuré"
            )
        
        try:
            prompt = self.prompts["legal_response"].format(
                complaint_text=complaint_text,
                analysis_summary=analysis_summary
            )
            response = self.llm_provider.generate_response(prompt)
            
            try:
                result = json.loads(response)
                logger.info("Génération de réponse juridique terminée avec succès")
                return AnalysisResult(
                    success=True,
                    content=json.dumps(result, ensure_ascii=False, indent=2),
                    confidence=0.9,
                    metadata={"analysis_type": "legal_response", "model_used": self.llm_provider.model_name}
                )
            except json.JSONDecodeError:
                logger.warning("Réponse LLM non-JSON pour la réponse juridique")
                return AnalysisResult(
                    success=True,
                    content=response,
                    confidence=0.8,
                    metadata={"analysis_type": "legal_response", "format": "text"}
                )
                
        except Exception as e:
            logger.error(f"Erreur lors de la génération de réponse juridique: {str(e)}")
            return AnalysisResult(
                success=False,
                content="",
                confidence=0.0,
                metadata={},
                error=str(e)
            )
    
    def perform_complete_analysis(self, complaint_text: str) -> Dict[str, AnalysisResult]:
        """
        Effectue l'analyse complète de la plainte (sentiment, résumé, contacts).
        
        🚀 OPTIMISÉ: Les 3 analyses sont exécutées EN PARALLÈLE.
        """
        start_time = time.time()
        logger.info("⚡ Démarrage de l'analyse complète de la plainte EN PARALLÈLE")
        
        results = {}
        
        # 🚀 EXÉCUTION PARALLÈLE DES 3 ANALYSES
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self.analyze_sentiment, complaint_text): "sentiment",
                executor.submit(self.generate_summary, complaint_text): "summary",
                executor.submit(self.extract_contacts, complaint_text): "contacts",
            }
            
            for future in as_completed(futures):
                analysis_name = futures[future]
                try:
                    result = future.result(timeout=120)
                    results[analysis_name] = result
                    logger.info(f"✅ [PARALLEL] {analysis_name} terminé")
                except Exception as e:
                    logger.error(f"❌ [PARALLEL] Erreur {analysis_name}: {e}")
                    results[analysis_name] = AnalysisResult(
                        success=False,
                        content="",
                        confidence=0.0,
                        metadata={},
                        error=str(e)
                    )
        
        elapsed_time = time.time() - start_time
        logger.info(f"✅ Analyse complète PARALLÈLE terminée en {elapsed_time:.2f}s")
        return results

    # ===== MÉTHODES HELPER POUR EXTRACTION PARALLÈLE =====
    
    def _extract_plaignant_parallel(self, complaint_text: str) -> Tuple[str, Dict[str, Any], float, Optional[str]]:
        """
        Extrait les informations du plaignant (exécuté en parallèle).
        
        Returns:
            Tuple (nom_extraction, data_dict, confiance, erreur)
        """
        try:
            logger.info("📧 [PARALLEL] Extraction des informations du plaignant...")
            prompt = self.prompts["extract_plaignant"].format(complaint_text=complaint_text)
            response = self.llm_provider.generate_response(prompt)
            
            data = json.loads(response)
            confiance = data.get("confiance", 0.5)
            logger.info(f"✅ [PARALLEL] Plaignant extrait (confiance: {confiance})")
            return ("plaignant", data, confiance, None)
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ [PARALLEL] Erreur parsing JSON plaignant: {e}")
            return ("plaignant", {}, 0.0, f"Erreur JSON: {e}")
        except Exception as e:
            logger.error(f"❌ [PARALLEL] Erreur extraction plaignant: {e}")
            return ("plaignant", {}, 0.0, str(e))
    
    def _extract_service_parallel(self, complaint_text: str) -> Tuple[str, Dict[str, Any], float, Optional[str]]:
        """
        Extrait les informations du service (exécuté en parallèle).
        
        Returns:
            Tuple (nom_extraction, data_dict, confiance, erreur)
        """
        try:
            logger.info("🏥 [PARALLEL] Extraction des informations du service...")
            prompt = self.prompts["extract_service"].format(complaint_text=complaint_text)
            response = self.llm_provider.generate_response(prompt)
            
            data = json.loads(response)
            confiance = data.get("confiance", 0.5)
            logger.info(f"✅ [PARALLEL] Service extrait: {data.get('service_principal')} (confiance: {confiance})")
            return ("service", data, confiance, None)
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ [PARALLEL] Erreur parsing JSON service: {e}")
            return ("service", {}, 0.0, f"Erreur JSON: {e}")
        except Exception as e:
            logger.error(f"❌ [PARALLEL] Erreur extraction service: {e}")
            return ("service", {}, 0.0, str(e))
    
    def _extract_description_parallel(self, complaint_text: str) -> Tuple[str, Dict[str, Any], float, Optional[str]]:
        """
        Extrait la description de la plainte (exécuté en parallèle).
        
        Returns:
            Tuple (nom_extraction, data_dict, confiance, erreur)
        """
        try:
            logger.info("📝 [PARALLEL] Extraction de la description...")
            prompt = self.prompts["extract_description"].format(complaint_text=complaint_text)
            response = self.llm_provider.generate_response(prompt)
            
            data = json.loads(response)
            confiance = data.get("confiance", 0.5)
            titre = data.get("titre", "")[:50] if data.get("titre") else "N/A"
            logger.info(f"✅ [PARALLEL] Description extraite: {titre}... (confiance: {confiance})")
            return ("description", data, confiance, None)
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ [PARALLEL] Erreur parsing JSON description: {e}")
            return ("description", {}, 0.0, f"Erreur JSON: {e}")
        except Exception as e:
            logger.error(f"❌ [PARALLEL] Erreur extraction description: {e}")
            return ("description", {}, 0.0, str(e))
    
    def _extract_analyse_parallel(self, complaint_text: str) -> Tuple[str, Dict[str, Any], float, Optional[str]]:
        """
        Extrait l'analyse de priorité (exécuté en parallèle).
        
        Returns:
            Tuple (nom_extraction, data_dict, confiance, erreur)
        """
        try:
            logger.info("🎯 [PARALLEL] Extraction de l'analyse de priorité...")
            prompt = self.prompts["extract_analyse"].format(complaint_text=complaint_text)
            response = self.llm_provider.generate_response(prompt)
            
            data = json.loads(response)
            confiance = data.get("confiance", 0.5)
            logger.info(f"✅ [PARALLEL] Analyse extraite: priorité={data.get('priorite_suggeree', 'N/A')} (confiance: {confiance})")
            return ("analyse", data, confiance, None)
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ [PARALLEL] Erreur parsing JSON analyse: {e}")
            return ("analyse", {}, 0.0, f"Erreur JSON: {e}")
        except Exception as e:
            logger.error(f"❌ [PARALLEL] Erreur extraction analyse: {e}")
            return ("analyse", {}, 0.0, str(e))

    def extract_complaint_data_from_pdf_multi_prompt(self, complaint_text: str) -> AnalysisResult:
        """
        Extrait les données structurées d'une plainte en utilisant plusieurs prompts spécialisés.
        
        🚀 OPTIMISÉ: Les 4 prompts sont exécutés EN PARALLÈLE pour réduire le temps de ~70%.
        
        Args:
            complaint_text: Texte extrait du PDF de plainte
            
        Returns:
            AnalysisResult contenant les données extraites avec haute confiance
        """
        start_time = time.time()
        logger.info("🔬 Démarrage de l'extraction MULTI-PROMPT PARALLÈLE depuis le PDF de plainte")
        
        if not self.llm_provider:
            logger.warning("LLM non disponible, utilisation du fallback")
            return self._extract_complaint_data_fallback(complaint_text)
        
        # Résultats par catégorie (valeurs par défaut)
        results = {
            "plaignant": {"nom": None, "prenom": None, "email": None, "telephone": None},
            "plainte": {"titre": None, "description": None, "date_incident": None, "service_concerne": None, "mode_reception": "pdf_import"},
            "analyse": {"priorite_suggeree": "MOYEN", "mots_cles": [], "gravite_estimee": "modérée", "resume_court": ""},
            "confiance_extraction": {"score_global": 0.0, "champs_incertains": [], "scores_par_categorie": {}}
        }
        
        confiances = []
        
        # 🚀 EXÉCUTION PARALLÈLE DES 4 PROMPTS
        logger.info("⚡ Lancement des 4 extractions en PARALLÈLE...")
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Soumettre les 4 tâches en parallèle
            futures = {
                executor.submit(self._extract_plaignant_parallel, complaint_text): "plaignant",
                executor.submit(self._extract_service_parallel, complaint_text): "service",
                executor.submit(self._extract_description_parallel, complaint_text): "description",
                executor.submit(self._extract_analyse_parallel, complaint_text): "analyse",
            }
            
            # Récupérer les résultats au fur et à mesure qu'ils arrivent
            for future in as_completed(futures):
                extraction_name = futures[future]
                try:
                    name, data, confiance, error = future.result(timeout=120)  # Timeout 2 min par extraction
                    
                    if error:
                        results["confiance_extraction"]["champs_incertains"].append(name)
                        continue
                    
                    # Intégrer les données selon le type d'extraction
                    if name == "plaignant":
                        results["plaignant"]["nom"] = data.get("nom")
                        results["plaignant"]["prenom"] = data.get("prenom")
                        results["plaignant"]["email"] = data.get("email")
                        results["plaignant"]["telephone"] = data.get("telephone")
                        confiances.append(confiance)
                        results["confiance_extraction"]["scores_par_categorie"]["plaignant"] = confiance
                    
                    elif name == "service":
                        results["plainte"]["service_concerne"] = data.get("service_principal")
                        results["service_details"] = {
                            "services_secondaires": data.get("services_secondaires", []),
                            "personnel_mentionne": data.get("personnel_mentionne", []),
                            "lieu_precis": data.get("lieu_precis")
                        }
                        confiances.append(confiance)
                        results["confiance_extraction"]["scores_par_categorie"]["service"] = confiance
                    
                    elif name == "description":
                        results["plainte"]["titre"] = data.get("titre")
                        results["plainte"]["description"] = data.get("description")
                        results["plainte"]["date_incident"] = data.get("date_incident")
                        results["plainte"]["mode_reception"] = data.get("mode_reception", "pdf_import")
                        results["demandes_plaignant"] = data.get("demandes_plaignant", [])
                        confiances.append(confiance)
                        results["confiance_extraction"]["scores_par_categorie"]["description"] = confiance
                    
                    elif name == "analyse":
                        results["analyse"]["priorite_suggeree"] = data.get("priorite_suggeree", "MOYEN")
                        results["analyse"]["gravite_estimee"] = data.get("gravite_estimee", "modérée")
                        results["analyse"]["mots_cles"] = data.get("mots_cles", [])
                        results["analyse"]["resume_court"] = data.get("resume_court", "")
                        results["risques_identifies"] = data.get("risques_identifies", [])
                        confiances.append(confiance)
                        results["confiance_extraction"]["scores_par_categorie"]["analyse"] = confiance
                        
                except Exception as e:
                    logger.error(f"❌ Erreur récupération résultat {extraction_name}: {e}")
                    results["confiance_extraction"]["champs_incertains"].append(extraction_name)
        
        # Calcul du score de confiance global (moyenne des confiances)
        if confiances:
            results["confiance_extraction"]["score_global"] = round(sum(confiances) / len(confiances), 2)
        else:
            results["confiance_extraction"]["score_global"] = 0.3
        
        elapsed_time = time.time() - start_time
        logger.info(f"🏁 Extraction MULTI-PROMPT PARALLÈLE terminée en {elapsed_time:.2f}s. Score global: {results['confiance_extraction']['score_global']}")
        
        return AnalysisResult(
            success=True,
            content=json.dumps(results, ensure_ascii=False, indent=2),
            confidence=results["confiance_extraction"]["score_global"],
            metadata={
                "analysis_type": "extract_complaint_data_multi_prompt",
                "model_used": self.llm_provider.model_name,
                "source": "llm_multi_prompt_parallel",
                "prompts_used": 4,
                "execution_mode": "parallel",
                "execution_time_seconds": round(elapsed_time, 2),
                "scores_par_categorie": results["confiance_extraction"]["scores_par_categorie"]
            }
        )

    def extract_complaint_data_from_pdf(self, complaint_text: str, use_multi_prompt: bool = True) -> AnalysisResult:
        """
        Extrait les données structurées d'une plainte à partir du texte d'un PDF.
        Utilisé pour la fonctionnalité "Création depuis un PDF".
        
        Args:
            complaint_text: Texte extrait du PDF de plainte
            use_multi_prompt: Si True, utilise plusieurs prompts spécialisés pour une meilleure précision
            
        Returns:
            AnalysisResult contenant les données extraites au format JSON
        """
        logger.info("Démarrage de l'extraction de données depuis le PDF de plainte")
        
        # Utiliser la méthode multi-prompt pour une meilleure précision
        if use_multi_prompt:
            logger.info("🔬 Utilisation de la méthode MULTI-PROMPT pour haute confiance")
            return self.extract_complaint_data_from_pdf_multi_prompt(complaint_text)
        
        if not self.llm_provider:
            # Fallback: extraction basique sans LLM
            return self._extract_complaint_data_fallback(complaint_text)
        
        try:
            prompt = self.prompts["extract_complaint_data"].format(complaint_text=complaint_text)
            response = self.llm_provider.generate_response(prompt)
            
            try:
                result = json.loads(response)
                logger.info("Extraction de données PDF terminée avec succès via LLM")
                return AnalysisResult(
                    success=True,
                    content=json.dumps(result, ensure_ascii=False, indent=2),
                    confidence=result.get("confiance_extraction", {}).get("score_global", 0.8),
                    metadata={
                        "analysis_type": "extract_complaint_data",
                        "model_used": self.llm_provider.model_name,
                        "source": "llm"
                    }
                )
            except json.JSONDecodeError:
                logger.warning("Réponse LLM non-JSON pour l'extraction de données PDF")
                # Tenter de parser partiellement
                return self._extract_complaint_data_fallback(complaint_text)
                
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction LLM de données PDF: {str(e)}")
            # Fallback sur extraction basique
            return self._extract_complaint_data_fallback(complaint_text)
    
    def _extract_complaint_data_fallback(self, complaint_text: str) -> AnalysisResult:
        """
        Extraction basique de données sans LLM (fallback).
        Utilise des heuristiques simples pour extraire les informations.
        """
        logger.info("Utilisation du fallback pour l'extraction de données PDF")
        
        import re
        
        # Patterns de base pour l'extraction
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        phone_pattern = r'(?:0|\+33)[1-9](?:[\s.-]?\d{2}){4}'
        date_pattern = r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})'
        
        # Extraction email
        emails = re.findall(email_pattern, complaint_text)
        email = emails[0] if emails else None
        
        # Extraction téléphone
        phones = re.findall(phone_pattern, complaint_text)
        telephone = phones[0].replace(" ", "").replace(".", "").replace("-", "") if phones else None
        
        # Extraction date
        dates = re.findall(date_pattern, complaint_text)
        date_incident = None
        if dates:
            day, month, year = dates[0]
            if len(year) == 2:
                year = "20" + year
            date_incident = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # Extraction nom/prénom (heuristiques simples)
        # Chercher après "Madame", "Monsieur", "M.", "Mme"
        name_patterns = [
            r'(?:Madame|Mme\.?)\s+([A-Z][a-zéèêëàâäùûü]+)\s+([A-Z][A-ZÉÈÊËÀÂÄÙÛÜ]+)',
            r'(?:Monsieur|Mr?\.?)\s+([A-Z][a-zéèêëàâäùûü]+)\s+([A-Z][A-ZÉÈÊËÀÂÄÙÛÜ]+)',
            r'(?:Nom|NOM)\s*[:\s]+([A-ZÉÈÊËÀÂÄÙÛÜ][a-zéèêëàâäùûü]+)',
        ]
        
        prenom = None
        nom = None
        for pattern in name_patterns:
            matches = re.findall(pattern, complaint_text)
            if matches:
                if isinstance(matches[0], tuple):
                    prenom, nom = matches[0]
                else:
                    nom = matches[0]
                break
        
        # Extraction du titre (première ligne significative ou après "Objet:")
        titre = None
        objet_match = re.search(r'(?:Objet|OBJET)\s*[:\s]+(.+?)(?:\n|$)', complaint_text)
        if objet_match:
            titre = objet_match.group(1).strip()[:100]
        else:
            # Prendre les premiers mots significatifs
            lines = complaint_text.split('\n')
            for line in lines:
                if len(line.strip()) > 20:
                    titre = line.strip()[:100]
                    break
        
        if not titre:
            titre = "Plainte importée depuis PDF"
        
        # Détection du service concerné
        services_keywords = {
            "urgence": "Urgences",
            "cardiologie": "Cardiologie",
            "chirurgie": "Chirurgie",
            "pédiatrie": "Pédiatrie",
            "maternité": "Gynécologie",
            "radiologie": "Radiologie",
            "laboratoire": "Laboratoire",
            "pharmacie": "Pharmacie",
            "accueil": "Administration",
            "consultation": "Consultation",
        }
        
        service_concerne = None
        text_lower = complaint_text.lower()
        for keyword, service in services_keywords.items():
            if keyword in text_lower:
                service_concerne = service
                break
        
        # Évaluation de la priorité basique
        mots_urgents = ["urgent", "grave", "immédiat", "danger", "décès", "mort", "critique"]
        mots_eleves = ["important", "serious", "inacceptable", "scandaleux", "préoccupant"]
        
        priorite = "MOYEN"
        if any(mot in text_lower for mot in mots_urgents):
            priorite = "URGENT"
        elif any(mot in text_lower for mot in mots_eleves):
            priorite = "ELEVE"
        
        # Construire le résultat
        result = {
            "plaignant": {
                "nom": nom,
                "prenom": prenom,
                "email": email,
                "telephone": telephone
            },
            "plainte": {
                "titre": titre,
                "description": complaint_text[:2000] if len(complaint_text) > 2000 else complaint_text,
                "date_incident": date_incident,
                "service_concerne": service_concerne,
                "mode_reception": "pdf_import"
            },
            "analyse": {
                "priorite_suggeree": priorite,
                "mots_cles": [],
                "gravite_estimee": "modérée" if priorite == "MOYEN" else ("élevée" if priorite in ["URGENT", "ELEVE"] else "faible"),
                "resume_court": f"Plainte importée depuis PDF. {titre if titre else ''}"
            },
            "confiance_extraction": {
                "score_global": 0.5,
                "champs_incertains": ["nom", "prenom", "date_incident"]
            }
        }
        
        return AnalysisResult(
            success=True,
            content=json.dumps(result, ensure_ascii=False, indent=2),
            confidence=0.5,
            metadata={
                "analysis_type": "extract_complaint_data",
                "source": "fallback_regex",
                "model_used": "none"
            }
        )
