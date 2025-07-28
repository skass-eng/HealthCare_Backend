"""
Service d'analyse LLM avancé pour analyser le contenu des plaintes
Utilise une approche MULTI-PROMPTS pour une précision maximale
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration des modèles disponibles
class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"

class LLMAnalyzer:
    """Analyseur LLM avancé pour les plaintes médicales avec approche multi-prompts"""
    
    def __init__(self, provider: str = "openai", model: str = None, api_key: str = None, base_url: str = None):
        self.provider = LLMProvider(provider.lower())
        self.api_key = api_key
        self.base_url = base_url
        
        # Configuration par défaut des modèles
        self.default_models = {
            LLMProvider.OPENAI: "gpt-4o-mini",
            LLMProvider.ANTHROPIC: "claude-3-haiku-20240307", 
            LLMProvider.OLLAMA: "llama3.2:3b"
        }
        
        self.model = model or self.default_models[self.provider]
        
        # Initialiser le client
        self._init_client()
        
        logger.info(f"🤖 LLM Analyzer initialisé avec {self.provider.value} - {self.model}")
    
    def _init_client(self):
        """Initialiser le client LLM selon le provider"""
        try:
            if self.provider == LLMProvider.OPENAI:
                import openai
                
                # Configuration du client OpenAI
                client_kwargs = {}
                if self.api_key:
                    client_kwargs['api_key'] = self.api_key
                if self.base_url:
                    client_kwargs['base_url'] = self.base_url
                
                self.client = openai.OpenAI(**client_kwargs)
                
            elif self.provider == LLMProvider.ANTHROPIC:
                import anthropic
                
                client_kwargs = {}
                if self.api_key:
                    client_kwargs['api_key'] = self.api_key
                
                self.client = anthropic.Anthropic(**client_kwargs)
                
            elif self.provider == LLMProvider.OLLAMA:
                import ollama
                
                host = self.base_url or 'http://localhost:11434'
                self.client = ollama.Client(host=host)
            
            logger.info(f"✅ Client {self.provider.value} initialisé avec succès")
            
        except ImportError as e:
            logger.error(f"❌ Module requis non installé pour {self.provider.value}: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Erreur initialisation client {self.provider.value}: {e}")
            raise
    
    def _call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """Appeler le LLM avec le prompt donné"""
        try:
            if self.provider == LLMProvider.OPENAI:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=1000
                )
                return response.choices[0].message.content
                
            elif self.provider == LLMProvider.ANTHROPIC:
                response = self.client.messages.create(
                    model=self.model,
                    system=system_prompt or "",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=1000
                )
                return response.content[0].text
                
            elif self.provider == LLMProvider.OLLAMA:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                response = self.client.chat(
                    model=self.model,
                    messages=messages,
                    options={"temperature": 0.1}
                )
                return response['message']['content']
        
        except Exception as e:
            logger.error(f"❌ Erreur appel LLM {self.provider.value}: {e}")
            raise
    
    def analyze_complaint_complete(self, text_content: str, metadata: Dict = None) -> Dict:
        """
        Analyse complète d'une plainte avec APPROCHE MULTI-PROMPTS
        """
        if not text_content or not text_content.strip():
            raise ValueError("Le contenu du texte est vide")
        
        logger.info(f"🔍 Début analyse MULTI-PROMPTS - {len(text_content)} caractères")
        
        try:
            # === PROMPT 1: EXTRACTION CONTACT ===
            contact_info = self._extract_contact_info(text_content)
            logger.info(f"📞 Contact extrait: {contact_info}")
            
            # === PROMPT 2: ANALYSE SENTIMENT ===
            sentiment_analysis = self._analyze_sentiment(text_content)
            logger.info(f"😔 Sentiment analysé: {sentiment_analysis}")
            
            # === PROMPT 3: CLASSIFICATION SERVICE/PRIORITÉ ===
            classification = self._classify_service_priority(text_content)
            logger.info(f"🏥 Classification: {classification}")
            
            # === PROMPT 4: GÉNÉRATION TITRE/RÉSUMÉ ===
            summary_info = self._generate_summary(text_content)
            logger.info(f"📝 Résumé généré: {summary_info.get('titre_suggere', 'N/A')}")
            
            # === ASSEMBLAGE FINAL ===
            final_result = {
                "service": classification.get("service"),
                "priorite": classification.get("priorite"),
                "sentiment": sentiment_analysis.get("sentiment", 0.0),
                "score_urgence": sentiment_analysis.get("score_urgence", 5),
                "titre_suggere": summary_info.get("titre_suggere", "Plainte analysée"),
                "resume": summary_info.get("resume", ""),
                "mots_cles": summary_info.get("mots_cles", []),
                "contact_info": contact_info,
                "dates_importantes": self._extract_dates(text_content),
                "suggestions_reponse": summary_info.get("suggestions_reponse", []),
                "confidence_score": 0.85  # Plus haute car multi-prompts
            }
            
            logger.info(f"✅ Analyse multi-prompts terminée avec succès")
            return self._validate_and_clean_result(final_result)
            
        except Exception as e:
            logger.error(f"❌ Erreur analyse multi-prompts: {e}")
            return self._fallback_analysis(text_content)
    
    def _extract_contact_info(self, text: str) -> Dict:
        """PROMPT 1: Extraction spécialisée des informations de contact"""
        
        system_prompt = """Tu es un expert en extraction d'informations de contact de plaignants.
Ta SEULE mission est de trouver les coordonnées de la PERSONNE QUI SE PLAINT, pas des employés mentionnés.

Réponds UNIQUEMENT au format JSON :
{
  "nom": "nom complet du plaignant ou null",
  "email": "email du plaignant ou null", 
  "telephone": "numéro du plaignant ou null"
}

PLAIGNANT = La personne qui :
✅ Écrit la plainte ("Je", "Mon nom est", "Je m'appelle", "Je suis")
✅ Signe le document (en bas de page)
✅ Est présentée comme "patient", "famille de", "accompagnant"
✅ Demande réparation ou solution

❌ NE PAS PRENDRE :
❌ Médecins mentionnés ("Dr X", "Docteur Y")
❌ Infirmières ("Mme Z infirmière")
❌ Personnel administratif
❌ Autres patients mentionnés dans le récit
❌ Noms mentionnés dans les événements décrits

RECHERCHE TECHNIQUES :
📧 EMAIL : formats xxx@xxx.xxx, xxx@xxx.fr, xxx@gmail.com, xxx@hotmail.com, xxx@yahoo.fr
📞 TÉLÉPHONE : 06, 07, 01-05, +33, formats XX.XX.XX.XX.XX, XX-XX-XX-XX-XX, XXXXXXXXXX"""

        prompt = f"""
MISSION : Trouver les coordonnées de la PERSONNE QUI DÉPOSE CETTE PLAINTE.

TEXTE COMPLET À ANALYSER :
{text}

⚠️ ATTENTION : Les coordonnées peuvent être :
- À la FIN du document (signature)
- Au DÉBUT (en-tête)
- Dans le CORPS du texte

Identifie QUI se plaint (le plaignant), pas les employés mentionnés dans l'histoire.

Exemple:
- ✅ "Je suis Marie Dupont, j'ai été mal reçue..." → nom: "Marie Dupont"
- ❌ "Le Dr Martin m'a mal soigné" → ne pas prendre "Dr Martin"

Cherche activement l'email et le téléphone du plaignant PARTOUT dans le texte.
Réponds en JSON strict."""

        try:
            response = self._call_llm(prompt, system_prompt)
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:-3]
            
            contact_data = json.loads(response)
            
            # Nettoyer les données
            return {
                "nom": str(contact_data.get("nom", "") or "").strip()[:100],
                "email": str(contact_data.get("email", "") or "").strip()[:100],
                "telephone": str(contact_data.get("telephone", "") or "").strip()[:20]
            }
            
        except Exception as e:
            logger.warning(f"Erreur extraction contact: {e}")
            return {"nom": "", "email": "", "telephone": ""}
    
    def _analyze_sentiment(self, text: str) -> Dict:
        """PROMPT 2: Analyse spécialisée du sentiment et urgence"""
        
        system_prompt = """Tu es un expert en analyse émotionnelle de plaintes médicales.
Ta mission est d'analyser le sentiment et l'urgence avec des descriptions claires.

Réponds UNIQUEMENT au format JSON :
{
  "sentiment": "description du sentiment",
  "score_urgence": "description de l'urgence"
}

ÉCHELLE SENTIMENT (1-10) :
10 = "Très content" : éloge, "excellent", "parfait", remerciements chaleureux
9 = "Content" : satisfaction élevée, "très bien", recommandations positives
8 = "Satisfait" : satisfaction, "bien", "correct", expérience positive
7 = "Plutôt satisfait" : globalement positif avec quelques réserves
6 = "Neutre" : factuel, informatif, sans émotion particulière
5 = "Légèrement mécontent" : petite déception, problème mineur
4 = "Mécontent" : mécontentement, "mauvais", "décevant", problème notable
3 = "Très mécontent" : forte déception, colère modérée, problème sérieux
2 = "En colère" : indignation, "scandaleux", "inacceptable", très contrarié
1 = "Très en colère" : rage, "horrible", négligence grave, traumatisme

ÉCHELLE URGENCE (1-10) :
10 = "Urgence vitale" : danger immédiat, risque de décès, négligence mortelle
9 = "Urgence élevée" : risque grave pour la santé, intervention immédiate requise
8 = "Urgence importante" : problème de santé sérieux, nécessite attention rapide
7 = "Priorité élevée" : impact important sur la santé ou bien-être
6 = "Priorité modérée" : problème significatif mais pas critique
5 = "Priorité normale" : problème standard nécessitant traitement
4 = "Priorité faible" : problème mineur, peut attendre
3 = "Non urgent" : plainte de confort, amélioration souhaitable
2 = "Suggestion" : recommandation d'amélioration, pas de problème majeur
1 = "Information" : simple retour d'expérience, pas de problème"""

        prompt = f"""
Analyse le sentiment et l'urgence de cette plainte avec des MOTS CLAIRS :

TEXTE À ANALYSER :
{text[:1500]}

Utilise les descriptions exactes de l'échelle (ex: "Très mécontent", "Priorité élevée").
Sois PRÉCIS sur le sentiment (évite "Neutre" sauf si vraiment factuel)."""

        try:
            response = self._call_llm(prompt, system_prompt)
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:-3]
            
            sentiment_data = json.loads(response)
            
            return {
                "sentiment": sentiment_data.get("sentiment", "Mécontent"),
                "score_urgence": sentiment_data.get("score_urgence", "Priorité modérée")
            }
            
        except Exception as e:
            logger.warning(f"Erreur analyse sentiment: {e}")
            return {"sentiment": "Mécontent", "score_urgence": "Priorité modérée"}  # Défaut
    
    def _classify_service_priority(self, text: str) -> Dict:
        """PROMPT 3: Classification spécialisée service et priorité"""
        
        system_prompt = """Tu es un expert en classification médicale hospitalière.
Ta mission est d'identifier le service et la priorité.

Réponds UNIQUEMENT au format JSON :
{
  "service": "CARDIOLOGIE|URGENCES|PEDIATRIE|CHIRURGIE|RADIOLOGIE|ONCOLOGIE|PSYCHIATRIE|MATERNITE|GERIATRIE|GENERAL",
  "priorite": "URGENT|ELEVE|MOYEN|FAIBLE"
}

SERVICES (mots-clés) :
- CARDIOLOGIE : cœur, cardiaque, cardiologue, pression, arythmie, infarctus
- URGENCES : urgence, accident, trauma, ambulance, samu, emergency
- PEDIATRIE : enfant, bébé, pédiatre, nourrisson, vaccination, jeune
- CHIRURGIE : opération, chirurgien, bloc, anesthésie, intervention
- RADIOLOGIE : radio, scanner, IRM, échographie, imagerie
- Si aucun spécifique → GENERAL

PRIORITÉS :
- URGENT : danger immédiat, urgence vitale, négligence grave
- ELEVE : problème sérieux, impact significatif
- MOYEN : problème modéré, amélioration souhaitée  
- FAIBLE : suggestion, plainte mineure"""

        prompt = f"""
Identifie le service hospitalier et la priorité :

TEXTE À ANALYSER :
{text[:1500]}

Cherche les mots-clés spécifiques pour identifier le bon service."""

        try:
            response = self._call_llm(prompt, system_prompt)
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:-3]
            
            classification_data = json.loads(response)
            
            return {
                "service": classification_data.get("service", "GENERAL"),
                "priorite": classification_data.get("priorite", "MOYEN")
            }
            
        except Exception as e:
            logger.warning(f"Erreur classification: {e}")
            return {"service": "GENERAL", "priorite": "MOYEN"}
    
    def _generate_summary(self, text: str) -> Dict:
        """PROMPT 4: Génération spécialisée titre, résumé et suggestions"""
        
        system_prompt = """Tu es un expert en rédaction de résumés médicaux.
Ta mission est de créer un titre, résumé et suggestions.

Réponds UNIQUEMENT au format JSON :
{
  "titre_suggere": "Titre informatif et précis",
  "resume": "Résumé en 3-4 phrases détaillées",
  "mots_cles": ["mot1", "mot2", "mot3"],
  "suggestions_reponse": ["action1", "action2", "action3"]
}

TITRE : Décris le problème principal (ex: "Attente excessive aux urgences - Personnel désagréable")
RÉSUMÉ : Couvre problème + contexte + impact + attentes
MOTS-CLÉS : 3-5 mots décrivant les aspects principaux
SUGGESTIONS : Actions concrètes pour répondre"""

        prompt = f"""
Génère titre, résumé et suggestions pour cette plainte :

TEXTE À ANALYSER :
{text[:1500]}

Crée un titre informatif qui décrit le vrai problème."""

        try:
            response = self._call_llm(prompt, system_prompt)
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:-3]
            
            summary_data = json.loads(response)
            
            return {
                "titre_suggere": str(summary_data.get("titre_suggere", "Plainte analysée"))[:200],
                "resume": str(summary_data.get("resume", ""))[:1000],
                "mots_cles": summary_data.get("mots_cles", [])[:5],
                "suggestions_reponse": summary_data.get("suggestions_reponse", [])[:3]
            }
            
        except Exception as e:
            logger.warning(f"Erreur génération résumé: {e}")
            return {
                "titre_suggere": "Plainte nécessitant une analyse",
                "resume": "Résumé indisponible - analyse manuelle recommandée",
                "mots_cles": ["analyse", "plainte"],
                "suggestions_reponse": ["Analyse manuelle", "Contact avec le plaignant"]
            }
    
    def _extract_dates(self, text: str) -> List[str]:
        """Extraction simple des dates avec regex"""
        import re
        
        # Patterns pour dates françaises
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',  # DD/MM/YYYY ou DD-MM-YYYY
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',  # YYYY/MM/DD ou YYYY-MM-DD
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            dates.extend(matches)
        
        return list(set(dates))[:5]  # Limiter à 5 dates uniques
    
    def _validate_and_clean_result(self, result: Dict) -> Dict:
        """Valider et nettoyer le résultat final"""
        
        # Services valides
        valid_services = ['CARDIOLOGIE', 'URGENCES', 'PEDIATRIE', 'CHIRURGIE', 
                         'RADIOLOGIE', 'ONCOLOGIE', 'PSYCHIATRIE', 'MATERNITE', 
                         'GERIATRIE', 'GENERAL']
        
        # Priorités valides  
        valid_priorities = ['URGENT', 'ELEVE', 'MOYEN', 'FAIBLE']
        
        cleaned = {}
        
        # Validation service
        service = result.get('service', '').upper()
        cleaned['service'] = service if service in valid_services else 'GENERAL'
        
        # Validation priorité
        priorite = result.get('priorite', '').upper()
        cleaned['priorite'] = priorite if priorite in valid_priorities else 'MOYEN'
        
        # Validation sentiment
        cleaned['sentiment'] = max(-1.0, min(1.0, float(result.get('sentiment', 0))))
        
        # Validation score urgence
        cleaned['score_urgence'] = max(0, min(10, int(result.get('score_urgence', 5))))
        
        # Validation confidence
        cleaned['confidence_score'] = max(0.0, min(1.0, float(result.get('confidence_score', 0.5))))
        
        # Champs texte
        cleaned['titre_suggere'] = str(result.get('titre_suggere', 'Plainte analysée'))[:200]
        cleaned['resume'] = str(result.get('resume', ''))[:1000]
        
        # Listes
        cleaned['mots_cles'] = result.get('mots_cles', [])[:10]
        cleaned['dates_importantes'] = result.get('dates_importantes', [])[:5]
        cleaned['suggestions_reponse'] = result.get('suggestions_reponse', [])[:5]
        
        # Contact info
        cleaned['contact_info'] = result.get('contact_info', {
            'nom': '', 'email': '', 'telephone': ''
        })
        
        return cleaned
    
    def _fallback_analysis(self, text_content: str) -> Dict:
        """Analyse de secours simplifiée avec nouveau format textuel"""
        logger.warning("🔄 Utilisation de l'analyse de secours")
        
        text_lower = text_content.lower()
        
        # Détection basique du service
        service = 'GENERAL'
        if any(word in text_lower for word in ['cardiologie', 'cœur', 'cardiaque']):
            service = 'CARDIOLOGIE'
        elif any(word in text_lower for word in ['urgence', 'accident']):
            service = 'URGENCES'
        elif any(word in text_lower for word in ['enfant', 'bébé']):
            service = 'PEDIATRIE'
        elif any(word in text_lower for word in ['chirurgie', 'opération']):
            service = 'CHIRURGIE'
        
        # Sentiment basique avec descriptions textuelles
        sentiment_description = "Mécontent"  # Défaut pour plainte
        if any(word in text_lower for word in ['scandaleux', 'horrible', 'inacceptable', 'révoltant']):
            sentiment_description = "Très en colère"
        elif any(word in text_lower for word in ['catastrophe', 'drame', 'traumatisant']):
            sentiment_description = "En colère" 
        elif any(word in text_lower for word in ['décevant', 'mauvais', 'problème']):
            sentiment_description = "Très mécontent"
        elif any(word in text_lower for word in ['bien', 'satisfait', 'correct']):
            sentiment_description = "Satisfait"
        elif any(word in text_lower for word in ['excellent', 'parfait', 'merci']):
            sentiment_description = "Content"
        
        # Urgence basique avec descriptions textuelles
        urgence_description = "Priorité modérée"  # Défaut
        if any(word in text_lower for word in ['urgence', 'urgent', 'immédiat', 'grave', 'danger']):
            urgence_description = "Urgence élevée"
        elif any(word in text_lower for word in ['vital', 'mort', 'décès', 'critique']):
            urgence_description = "Urgence vitale"
        elif any(word in text_lower for word in ['important', 'sérieux', 'préoccupant']):
            urgence_description = "Priorité élevée"
        elif any(word in text_lower for word in ['mineur', 'petit', 'suggestion']):
            urgence_description = "Priorité faible"
        
        # Extraction basique du nom (recherche de patterns courants)
        nom_detecte = ''
        email_detecte = ''
        telephone_detecte = ''
        
        # Recherche simple de nom (après "Je suis", "Mon nom")
        import re
        nom_patterns = [
            r'je suis ([A-Z][a-z]+ [A-Z][a-z]+)',
            r'mon nom est ([A-Z][a-z]+ [A-Z][a-z]+)',
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*(?:Inspectrice|Docteur|Madame|Monsieur)'
        ]
        
        for pattern in nom_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                nom_detecte = match.group(1)
                break
        
        # Recherche d'email
        email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text_content)
        if email_match:
            email_detecte = email_match.group(1)
        
        # Recherche de téléphone
        phone_match = re.search(r'(?:Téléphone[:\s]*)?(\d{2}(?:\s?\d{2}){4})', text_content)
        if phone_match:
            telephone_detecte = phone_match.group(1)
        
        return {
            'service': service,
            'priorite': 'MOYEN',
            'sentiment': sentiment_description,  # ✅ NOUVEAU FORMAT TEXTUEL
            'score_urgence': urgence_description,  # ✅ NOUVEAU FORMAT TEXTUEL
            'titre_suggere': f'Plainte {sentiment_description.lower()} - {service.lower()}',
            'resume': text_content[:200] + '...' if len(text_content) > 200 else text_content,
            'mots_cles': ['plainte', service.lower()],
            'contact_info': {  # ✅ EXTRACTION BASIQUE DU CONTACT
                'nom': nom_detecte,
                'email': email_detecte,
                'telephone': telephone_detecte
            },
            'dates_importantes': [],
            'suggestions_reponse': ['Analyse manuelle recommandée - LLM indisponible'],
            'confidence_score': 0.3
        }
    
    def test_connection(self) -> bool:
        """Tester la connexion au LLM"""
        try:
            test_prompt = "Réponds simplement 'OK' si tu me reçois."
            response = self._call_llm(test_prompt, "Tu es un assistant de test.")
            return 'ok' in response.lower()
        except Exception as e:
            logger.error(f"❌ Test connexion LLM échoué: {e}")
            return False 