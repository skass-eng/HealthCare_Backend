"""
Service d'analyse IA pour les plaintes avec prompts spécialisés
"""
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
import json

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
            "sentiment": """
Analyse le sentiment de cette plainte médicale et détermine le niveau d'émotion du plaignant.

Plainte à analyser:
{complaint_text}

Instructions:
1. Identifie le sentiment principal (positif, négatif, neutre)
2. Évalue l'intensité émotionnelle (faible, modérée, élevée)
3. Identifie les mots-clés émotionnels
4. Propose des recommandations pour la réponse

Format de réponse JSON:
{{
    "sentiment_principal": "positif/négatif/neutre",
    "intensite_emotionnelle": "faible/modérée/élevée",
    "score_sentiment": 0.0, // de -1.0 (très négatif) à 1.0 (très positif)
    "mots_cles_emotionnels": ["mot1", "mot2"],
    "recommandations_reponse": "conseils pour la tonalité de réponse"
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
        """Effectue l'analyse complète de la plainte (sentiment, résumé, contacts)"""
        logger.info("Démarrage de l'analyse complète de la plainte")
        
        results = {}
        
        # 1. Analyse de sentiment
        results["sentiment"] = self.analyze_sentiment(complaint_text)
        
        # 2. Génération de résumé
        results["summary"] = self.generate_summary(complaint_text)
        
        # 3. Extraction de contacts
        results["contacts"] = self.extract_contacts(complaint_text)
        
        logger.info("Analyse complète terminée")
        return results
