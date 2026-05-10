#!/usr/bin/env python3
"""
PROVIDER LLM - HealthCare AI Architecture ODYSSEE
Service d'abstraction pour les différents fournisseurs LLM (inspiré d'ODYSSEE)
Version: 1.0.0 - Architecture ODYSSEE
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    """Fournisseurs LLM supportés"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"

class BaseLLMService(ABC):
    """
    Classe de base pour les services LLM (pattern Strategy comme ODYSSEE)
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = None, **kwargs):
        self.api_key = api_key
        self.model = model
        self.config = kwargs
        self.model_name = model or "unknown"
    
    @abstractmethod
    async def analyze(self, prompt: str, parameters: Dict[str, Any] = None) -> str:
        """Analyser un prompt et retourner la réponse"""
        pass
    
    def generate_response(self, prompt: str, parameters: Dict[str, Any] = None) -> str:
        """Version synchrone pour compatibilité avec l'architecture modulaire"""
        # Simulation simple pour le développement
        logger.info(f"Génération de réponse LLM (simulation) - Modèle: {self.model_name}")
        
        prompt_lower = prompt.lower()
        
        # Analyser le type de prompt pour générer une réponse appropriée
        # IMPORTANT: Les prompts spécialisés multi-prompt sont testés EN PREMIER
        
        # Prompts spécialisés MULTI-PROMPT (haute confiance)
        if "extraire uniquement les informations du plaignant" in prompt_lower or "informations de contact" in prompt_lower:
            logger.info("🔍 Détection: extraction PLAIGNANT (multi-prompt)")
            return self._generate_extract_plaignant_response(prompt)
        elif "identifier le(s) service(s) hospitalier" in prompt_lower or "services hospitaliers courants" in prompt_lower:
            logger.info("🔍 Détection: extraction SERVICE (multi-prompt)")
            return self._generate_extract_service_response(prompt)
        elif "extraire et structurer la description" in prompt_lower or "description des faits" in prompt_lower:
            logger.info("🔍 Détection: extraction DESCRIPTION (multi-prompt)")
            return self._generate_extract_description_response(prompt)
        elif "analyser la gravité et la priorité" in prompt_lower or "critères de priorisation" in prompt_lower:
            logger.info("🔍 Détection: extraction ANALYSE (multi-prompt)")
            return self._generate_extract_analyse_response(prompt)
        # Prompts généraux
        elif "extraction de données" in prompt_lower or "extrais toutes les informations" in prompt_lower or '"plaignant"' in prompt_lower:
            logger.info("🔍 Détection: extraction de données de plainte (global)")
            return self._generate_extract_complaint_data_response(prompt)
        elif "sentiment" in prompt_lower:
            return self._generate_sentiment_response()
        elif "résumé" in prompt_lower or "summary" in prompt_lower:
            return self._generate_summary_response()
        elif "contact" in prompt_lower:
            return self._generate_contacts_response()
        elif "juridique" in prompt_lower or "legal" in prompt_lower:
            return self._generate_legal_response()
        else:
            return self._generate_generic_response()
    
    def _generate_sentiment_response(self) -> str:
        """Génère une réponse simulée pour l'analyse de sentiment"""
        return """{
    "sentiment_principal": "négatif",
    "intensite_emotionnelle": "modérée",
    "score_sentiment": -0.6,
    "mots_cles_emotionnels": ["insatisfait", "déçu", "problème"],
    "recommandations_reponse": "Adopter un ton empathique et proposer des solutions concrètes"
}"""
    
    def _generate_summary_response(self) -> str:
        """Génère une réponse simulée pour le résumé"""
        return """{
    "resume_executif": "Plainte concernant un problème de service nécessitant une attention particulière et un suivi approprié.",
    "faits_principaux": ["Problème de service identifié", "Demande de suivi du patient", "Nécessité d'amélioration"],
    "services_concernes": ["Service concerné", "Direction qualité"],
    "nature_probleme": "Problème de qualité de service",
    "demande_plaignant": "Amélioration du service et suivi",
    "date_incident": "non précisée",
    "gravite_estimee": "modérée"
}"""
    
    def _generate_contacts_response(self) -> str:
        """Génère une réponse simulée pour l'extraction de contacts"""
        return """{
    "personnes_mentionnees": [],
    "services_departements": [
        {
            "nom": "Service concerné", 
            "contexte": "Service impliqué dans la plainte"
        }
    ],
    "coordonnees_trouvees": [],
    "interlocuteurs_cles": []
}"""
    
    def _generate_legal_response(self) -> str:
        """Génère une réponse simulée pour la réponse juridique"""
        return """{
    "reponse_officielle": "Madame, Monsieur,\\n\\nNous avons pris connaissance de votre signalement et tenons à vous remercier de nous avoir fait part de vos préoccupations. Notre établissement accorde une importance primordiale à la qualité des soins et des services fournis à nos patients.\\n\\nUne enquête interne a été diligentée afin d'examiner les éléments que vous avez portés à notre attention. Nous mettons tout en œuvre pour assurer la continuité et l'amélioration de nos prestations.\\n\\nNous restons à votre disposition pour tout complément d'information.\\n\\nCordialement,\\nLe Responsable Qualité",
    "points_cles": ["Accusé de réception", "Enquête interne", "Engagement qualité"],
    "actions_proposees": ["Enquête interne", "Suivi des améliorations"],
    "engagement_suivi": "Suivi régulier et communication des résultats",
    "tone_juridique": "Professionnel, empathique, sans admission de responsabilité",
    "recommandations_internes": ["Révision des procédures", "Formation du personnel"]
}"""
    
    def _generate_extract_complaint_data_response(self, prompt: str) -> str:
        """Génère une réponse simulée pour l'extraction de données de plainte depuis PDF"""
        import re
        
        logger.info("📝 Extraction des données du PDF (fallback)")
        
        # Chercher des patterns dans le texte fourni
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', prompt)
        phone_match = re.search(r'(?:0|\+33)[1-9](?:[\s.-]?\d{2}){4}', prompt)
        
        email = email_match.group(0) if email_match else None
        phone = phone_match.group(0).replace(" ", "").replace(".", "").replace("-", "") if phone_match else None
        
        # Extraction nom/prénom améliorée
        nom = None
        prenom = None
        
        # Patterns pour les noms
        name_patterns = [
            r'(?:Madame|Mme\.?)\s+([A-ZÉÈÊËÀÂÄÙÛÜa-zéèêëàâäùûü]+)\s+([A-ZÉÈÊËÀÂÄÙÛÜ][A-ZÉÈÊËÀÂÄÙÛÜa-zéèêëàâäùûü]*)',
            r'(?:Monsieur|Mr?\.?)\s+([A-ZÉÈÊËÀÂÄÙÛÜa-zéèêëàâäùûü]+)\s+([A-ZÉÈÊËÀÂÄÙÛÜ][A-ZÉÈÊËÀÂÄÙÛÜa-zéèêëàâäùûü]*)',
            r'Je\s+soussigné[e]?,?\s+([A-ZÉÈÊËÀÂÄÙÛÜa-zéèêëàâäùûü]+)\s+([A-ZÉÈÊËÀÂÄÙÛÜ][A-ZÉÈÊËÀÂÄÙÛÜa-zéèêëàâäùûü]*)',
            r'Nom\s*[:\s]+([A-ZÉÈÊËÀÂÄÙÛÜ][a-zéèêëàâäùûü]+)',
            r'Patient[e]?\s*[:\s]+([A-ZÉÈÊËÀÂÄÙÛÜa-zéèêëàâäùûü]+)\s+([A-ZÉÈÊËÀÂÄÙÛÜ][A-ZÉÈÊËÀÂÄÙÛÜa-zéèêëàâäùûü]*)',
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, prompt, re.IGNORECASE)
            if matches:
                if isinstance(matches[0], tuple) and len(matches[0]) >= 2:
                    prenom, nom = matches[0][0], matches[0][1]
                elif isinstance(matches[0], str):
                    nom = matches[0]
                break
        
        # Extraction de la date
        date_incident = None
        date_patterns = [
            r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})',
            r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2})',
            r'(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    if groups[1].isdigit():
                        day, month, year = groups
                        if len(year) == 2:
                            year = "20" + year
                        date_incident = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    else:
                        # Format "10 mars 2024"
                        mois_map = {
                            'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04',
                            'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08',
                            'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'
                        }
                        day = groups[0].zfill(2)
                        month = mois_map.get(groups[1].lower(), '01')
                        year = groups[2]
                        date_incident = f"{year}-{month}-{day}"
                break
        
        # Extraction du titre/objet
        titre = None
        objet_patterns = [
            r'(?:Objet|OBJET)\s*[:\s]+(.+?)(?:\n|$)',
            r'(?:Réclamation|RÉCLAMATION|Plainte|PLAINTE)\s*[:\s]+(.+?)(?:\n|$)',
            r'(?:Concerne|CONCERNE)\s*[:\s]+(.+?)(?:\n|$)',
        ]
        
        for pattern in objet_patterns:
            match = re.search(pattern, prompt)
            if match:
                titre = match.group(1).strip()[:100]
                break
        
        if not titre:
            # Chercher une première phrase significative
            lines = prompt.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) > 30 and not re.match(r'^[\d\s\-\/\.\,]+$', line):
                    # Ignorer les lignes qui ressemblent à des instructions du prompt
                    if not any(x in line.lower() for x in ['tu es', 'instructions', 'format', 'json']):
                        titre = line[:100]
                        break
        
        # Extraction de la description
        description = ""
        # Chercher le corps du texte (après les en-têtes)
        content_start = prompt.find("Texte du document")
        if content_start > -1:
            # Trouver le début du contenu réel
            text_content = prompt[content_start:]
            # Ignorer la première ligne d'instruction
            lines = text_content.split('\n')[2:]  # Skip "Texte du document..." line
            for line in lines:
                if line.strip() and not any(x in line.lower() for x in ['instructions:', 'format', 'json', 'important:']):
                    description += line.strip() + " "
                    if len(description) > 500:
                        break
        
        if not description:
            description = "Plainte importée depuis un document PDF. Veuillez consulter le document original pour plus de détails."
        
        # Détection du service
        service_concerne = None
        service_patterns = [
            r'(?:service|département)\s+(?:de\s+|d\')?([A-Za-zÀ-ÿ\s]+?)(?:\.|,|\n|$)',
            r'(?:urgences|radiologie|cardiologie|chirurgie|pédiatrie|maternité|oncologie|neurologie)',
        ]
        
        for pattern in service_patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                if match.groups():
                    service_concerne = match.group(1).strip()[:50]
                else:
                    service_concerne = match.group(0).strip()[:50]
                break
        
        logger.info(f"📝 Données extraites: nom={nom}, prenom={prenom}, email={email}, tel={phone}, date={date_incident}")
        
        return json.dumps({
            "plaignant": {
                "nom": nom,
                "prenom": prenom,
                "email": email,
                "telephone": phone
            },
            "plainte": {
                "titre": titre or "Plainte importée depuis PDF",
                "description": description.strip()[:1000] if description else "Description non extraite",
                "date_incident": date_incident,
                "service_concerne": service_concerne,
                "mode_reception": "pdf_import"
            },
            "analyse": {
                "priorite_suggeree": "MOYEN",
                "mots_cles": ["plainte", "pdf", "importation"],
                "gravite_estimee": "modérée",
                "resume_court": titre or "Plainte importée depuis PDF nécessitant une analyse approfondie."
            },
            "confiance_extraction": {
                "score_global": 0.6,
                "champs_incertains": [k for k, v in {"nom": nom, "prenom": prenom, "date_incident": date_incident, "email": email}.items() if v is None]
            }
        }, ensure_ascii=False, indent=2)
    
    def _generate_extract_plaignant_response(self, prompt: str) -> str:
        """Génère une réponse simulée pour l'extraction du plaignant (multi-prompt)"""
        import re
        
        logger.info("📧 Extraction spécialisée PLAIGNANT (signataire, pas destinataire)")
        
        # Extraction email - prendre le DERNIER email (souvent celui du signataire)
        email_matches = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', prompt)
        email = email_matches[-1] if email_matches else None  # Dernier email = signataire
        
        # Extraction téléphone - prendre le DERNIER (souvent celui du signataire)
        phone_matches = re.findall(r'(?:0|\+33)[1-9](?:[\s.-]?\d{2}){4}', prompt)
        phone = phone_matches[-1].replace(" ", "").replace(".", "").replace("-", "") if phone_matches else None
        
        nom = None
        prenom = None
        
        # STRATÉGIE: Chercher le SIGNATAIRE (fin du document) plutôt que le destinataire
        
        # 1. Chercher après "Cordialement", "Sincèrement", "Salutations", signature
        signature_patterns = [
            r'(?:Cordialement|Sincèrement|Salutations|Bien à vous)[,\s]*[\n\r]+\s*([A-ZÉÈÊËÀÂÄÙÛÜa-zéèêëàâäùûü]+)\s+([A-ZÉÈÊËÀÂÄÙÛÜ]{2,})',
            r'(?:Cordialement|Sincèrement|Salutations|Bien à vous)[,\s]*[\n\r]+\s*([A-ZÉÈÊËÀÂÄÙÛÜ][a-zéèêëàâäùûü]+)\s+([A-ZÉÈÊËÀÂÄÙÛÜ][a-zéèêëàâäùûü]+)',
            r'Signature\s*[:\s]*([A-ZÉÈÊËÀÂÄÙÛÜa-zéèêëàâäùûü]+)\s+([A-ZÉÈÊËÀÂÄÙÛÜ]+)',
        ]
        
        for pattern in signature_patterns:
            matches = re.findall(pattern, prompt, re.IGNORECASE | re.MULTILINE)
            if matches:
                prenom, nom = matches[-1][0], matches[-1][1]  # Dernier match
                logger.info(f"📧 Trouvé via signature: {prenom} {nom}")
                break
        
        # 2. Si pas trouvé, chercher "Je soussigné(e)"
        if not nom:
            soussigne_patterns = [
                r'[Jj]e\s+soussigné[e]?[,\s]+([A-ZÉÈÊËÀÂÄÙÛÜa-zéèêëàâäùûü]+)\s+([A-ZÉÈÊËÀÂÄÙÛÜ]{2,})',
                r'[Jj]e\s+soussigné[e]?[,\s]+(?:Madame|Monsieur|Mme|Mr?\.?)\s+([A-ZÉÈÊËÀÂÄÙÛÜa-zéèêëàâäùûü]+)\s+([A-ZÉÈÊËÀÂÄÙÛÜ]{2,})',
            ]
            for pattern in soussigne_patterns:
                matches = re.findall(pattern, prompt)
                if matches:
                    prenom, nom = matches[0][0], matches[0][1]
                    logger.info(f"📧 Trouvé via 'je soussigné': {prenom} {nom}")
                    break
        
        # 3. Chercher dans les coordonnées expéditeur (souvent en haut, mais AVANT "À l'attention de")
        if not nom:
            # Chercher un bloc de coordonnées avant "À l'attention" ou "Destinataire"
            expediteur_match = re.search(r'^([A-ZÉÈÊËÀÂÄÙÛÜa-zéèêëàâäùûü]+\s+[A-ZÉÈÊËÀÂÄÙÛÜ]{2,}).*?(?=À l\'attention|Destinataire|Objet|Madame,|Monsieur,)', prompt, re.MULTILINE | re.DOTALL)
            if expediteur_match:
                parts = expediteur_match.group(1).strip().split()
                if len(parts) >= 2:
                    prenom = parts[0]
                    nom = parts[1]
                    logger.info(f"📧 Trouvé via expéditeur: {prenom} {nom}")
        
        # 4. ÉVITER les destinataires - NE PAS prendre les noms après ces patterns
        destinataire_indicators = ["à l'attention de", "destinataire", "monsieur le directeur", "madame la directrice", "service qualité"]
        
        # Calculer la confiance basée sur les champs trouvés
        fields_found = sum([1 for x in [nom, prenom, email, phone] if x])
        confiance = min(0.9, 0.4 + (fields_found * 0.15))
        
        logger.info(f"📧 Résultat plaignant: nom={nom}, prenom={prenom}, email={email}, tel={phone}, confiance={confiance}")
        
        return json.dumps({
            "nom": nom,
            "prenom": prenom,
            "email": email,
            "telephone": phone,
            "confiance": confiance
        }, ensure_ascii=False, indent=2)
    
    def _generate_extract_service_response(self, prompt: str) -> str:
        """Génère une réponse simulée pour l'extraction du service (multi-prompt)"""
        import re
        
        logger.info("🏥 Extraction spécialisée SERVICE")
        
        # Liste des services hospitaliers connus
        services_connus = [
            "urgences", "samu", "réanimation", "soins intensifs",
            "cardiologie", "pneumologie", "neurologie", "néphrologie",
            "chirurgie", "chirurgie orthopédique", "chirurgie viscérale", "chirurgie cardiaque",
            "radiologie", "imagerie médicale", "scanner", "irm",
            "maternité", "obstétrique", "pédiatrie", "néonatologie",
            "oncologie", "hématologie", "cancérologie",
            "psychiatrie", "gériatrie", "rééducation",
            "médecine générale", "médecine interne",
            "laboratoire", "pharmacie", "bloc opératoire",
            "accueil", "administration", "direction", "qualité"
        ]
        
        prompt_lower = prompt.lower()
        service_principal = None
        services_secondaires = []
        
        for service in services_connus:
            if service in prompt_lower:
                if service_principal is None:
                    service_principal = service.title()
                else:
                    services_secondaires.append(service.title())
        
        # Chercher les noms de médecins
        personnel = []
        dr_pattern = r'(?:Dr\.?|Docteur)\s+([A-ZÉÈÊËÀÂÄÙÛÜ][a-zéèêëàâäùûü]+)'
        dr_matches = re.findall(dr_pattern, prompt)
        for nom in dr_matches:
            personnel.append({"nom": f"Dr {nom}", "fonction": "médecin", "service": service_principal})
        
        # Chercher des mentions d'étage/bâtiment
        lieu_match = re.search(r'(?:étage|bâtiment|chambre|box)\s*[:\s]*(\d+|[A-Z])', prompt, re.IGNORECASE)
        lieu_precis = lieu_match.group(0) if lieu_match else None
        
        confiance = 0.8 if service_principal else 0.4
        
        logger.info(f"🏥 Résultat service: principal={service_principal}, secondaires={services_secondaires}, confiance={confiance}")
        
        return json.dumps({
            "service_principal": service_principal,
            "services_secondaires": services_secondaires,
            "personnel_mentionne": personnel,
            "lieu_precis": lieu_precis,
            "confiance": confiance
        }, ensure_ascii=False, indent=2)
    
    def _generate_extract_description_response(self, prompt: str) -> str:
        """Génère une réponse simulée pour l'extraction de la description (multi-prompt)"""
        import re
        
        logger.info("📝 Extraction spécialisée DESCRIPTION")
        
        # Extraction du titre/objet
        titre = None
        objet_patterns = [
            r'(?:Objet|OBJET)\s*[:\s]+(.+?)(?:\n|$)',
            r'(?:Réclamation|RÉCLAMATION)\s*[:\s]+(.+?)(?:\n|$)',
            r'(?:Plainte|PLAINTE)\s*[:\s]+(.+?)(?:\n|$)',
            r'(?:Concerne|CONCERNE)\s*[:\s]+(.+?)(?:\n|$)',
        ]
        
        for pattern in objet_patterns:
            match = re.search(pattern, prompt)
            if match:
                titre = match.group(1).strip()[:100]
                break
        
        if not titre:
            # Chercher une première phrase significative
            lines = prompt.split('\n')
            for line in lines[5:]:  # Sauter les premières lignes (instructions)
                line = line.strip()
                if len(line) > 30 and not re.match(r'^[\d\s\-\/\.\,]+$', line):
                    if not any(x in line.lower() for x in ['tu es', 'instructions', 'format', 'json', 'objectif']):
                        titre = line[:100]
                        break
        
        # Extraction de la date
        date_incident = None
        date_patterns = [
            r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})',
            r'(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    if groups[1].isdigit():
                        day, month, year = groups
                        date_incident = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    else:
                        mois_map = {
                            'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04',
                            'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08',
                            'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'
                        }
                        day = groups[0].zfill(2)
                        month = mois_map.get(groups[1].lower(), '01')
                        year = groups[2]
                        date_incident = f"{year}-{month}-{day}"
                break
        
        # Extraction de la description
        description = ""
        content_start = prompt.find("Texte du document")
        if content_start > -1:
            text_content = prompt[content_start:]
            lines = text_content.split('\n')[2:]
            for line in lines:
                if line.strip() and not any(x in line.lower() for x in ['instructions:', 'format', 'json', 'important:', 'objectif']):
                    description += line.strip() + " "
                    if len(description) > 800:
                        break
        
        if not description:
            description = "Description de la plainte extraite du document PDF."
        
        # Mode de réception
        mode = "pdf_import"
        if "courrier" in prompt.lower():
            mode = "courrier"
        elif "email" in prompt.lower() or "mail" in prompt.lower():
            mode = "email"
        elif "téléphone" in prompt.lower() or "oral" in prompt.lower():
            mode = "oral"
        
        # Demandes du plaignant
        demandes = []
        demande_patterns = [
            r'(?:je\s+(?:souhaite|demande|exige|attends))\s+(.+?)(?:\.|$)',
            r'(?:nous\s+(?:souhaitons|demandons))\s+(.+?)(?:\.|$)',
        ]
        for pattern in demande_patterns:
            matches = re.findall(pattern, prompt, re.IGNORECASE)
            demandes.extend([m.strip()[:100] for m in matches[:3]])
        
        confiance = 0.7 if titre and description else 0.5
        
        logger.info(f"📝 Résultat description: titre={titre[:50] if titre else None}..., date={date_incident}, confiance={confiance}")
        
        return json.dumps({
            "titre": titre or "Plainte importée depuis PDF",
            "description": description.strip()[:1000],
            "date_incident": date_incident,
            "mode_reception": mode,
            "demandes_plaignant": demandes,
            "confiance": confiance
        }, ensure_ascii=False, indent=2)
    
    def _generate_extract_analyse_response(self, prompt: str) -> str:
        """Génère une réponse simulée pour l'extraction de l'analyse (multi-prompt)"""
        import re
        
        logger.info("🎯 Extraction spécialisée ANALYSE")
        
        prompt_lower = prompt.lower()
        
        # Mots-clés de gravité
        mots_urgents = ["décès", "mort", "erreur médicale", "négligence", "infection nosocomiale", "danger", "vie"]
        mots_eleves = ["préjudice", "dommage", "avocat", "tribunal", "plainte pénale", "grave"]
        mots_moyens = ["attente", "délai", "accueil", "communication", "information", "insatisfait"]
        mots_bas = ["suggestion", "amélioration", "remarque", "conseil"]
        
        # Déterminer la priorité
        priorite = "MOYEN"
        gravite = "modérée"
        
        if any(mot in prompt_lower for mot in mots_urgents):
            priorite = "URGENT"
            gravite = "critique"
        elif any(mot in prompt_lower for mot in mots_eleves):
            priorite = "ELEVE"
            gravite = "élevée"
        elif any(mot in prompt_lower for mot in mots_bas):
            priorite = "BAS"
            gravite = "faible"
        
        # Extraire les mots-clés significatifs
        mots_cles = []
        keywords_patterns = [
            r'\b(urgence|soins|traitement|diagnostic|médecin|infirmier|hôpital|clinique)\b',
            r'\b(douleur|souffrance|attente|retard|erreur|problème|incident)\b',
            r'\b(qualité|prise en charge|accueil|communication|information)\b',
        ]
        
        for pattern in keywords_patterns:
            matches = re.findall(pattern, prompt_lower)
            mots_cles.extend(matches)
        
        mots_cles = list(set(mots_cles))[:5]  # Dédupliquer et limiter
        
        # Résumé court
        resume = f"Plainte de priorité {priorite} concernant "
        if mots_cles:
            resume += ", ".join(mots_cles[:3]) + "."
        else:
            resume += "la qualité des soins."
        
        # Risques identifiés
        risques = []
        if priorite in ["URGENT", "ELEVE"]:
            risques.append("Risque juridique potentiel")
            if "médical" in prompt_lower or "soins" in prompt_lower:
                risques.append("Risque de réputation")
        
        confiance = 0.75
        
        logger.info(f"🎯 Résultat analyse: priorité={priorite}, gravité={gravite}, confiance={confiance}")
        
        return json.dumps({
            "priorite_suggeree": priorite,
            "gravite_estimee": gravite,
            "mots_cles": mots_cles,
            "resume_court": resume,
            "risques_identifies": risques,
            "confiance": confiance
        }, ensure_ascii=False, indent=2)
    
    def _generate_generic_response(self) -> str:
        """Génère une réponse générique"""
        return "Analyse effectuée avec succès."
    
    @abstractmethod
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parser une réponse JSON du LLM"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Vérifier la disponibilité du service LLM"""
        pass

class OpenAIService(BaseLLMService):
    """Service OpenAI (comme les widgets spécialisés ODYSSEE)"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo", **kwargs):
        super().__init__(api_key, model, **kwargs)
        
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=api_key)
            self.model = model
        except ImportError:
            raise ImportError("Le package 'openai' est requis pour utiliser OpenAI")
    
    async def analyze(self, prompt: str, parameters: Dict[str, Any] = None) -> str:
        """Analyser avec OpenAI"""
        try:
            params = parameters or {}
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "Vous êtes un assistant spécialisé dans l'analyse des plaintes hospitalières. Répondez toujours en JSON valide."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=params.get("max_tokens", 2000),
                temperature=params.get("temperature", 0.1),
                response_format={"type": "json_object"}
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"❌ Erreur OpenAI: {e}")
            raise
    
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parser la réponse JSON d'OpenAI"""
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erreur parsing JSON OpenAI: {e}")
            return {"erreur": "Réponse invalide", "response_brute": response}
    
    async def health_check(self) -> bool:
        """Vérifier la disponibilité d'OpenAI"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=10
            )
            return True
        except:
            return False

class AnthropicService(BaseLLMService):
    """Service Anthropic Claude"""
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307", **kwargs):
        super().__init__(api_key, model, **kwargs)
        
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
            self.model = model
        except ImportError:
            raise ImportError("Le package 'anthropic' est requis pour utiliser Claude")
    
    async def analyze(self, prompt: str, parameters: Dict[str, Any] = None) -> str:
        """Analyser avec Claude"""
        try:
            params = parameters or {}
            
            # Adapter le prompt pour Claude
            full_prompt = f"""Vous êtes un assistant spécialisé dans l'analyse des plaintes hospitalières.
            
{prompt}

Répondez uniquement avec un JSON valide, sans texte supplémentaire."""
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=params.get("max_tokens", 2000),
                temperature=params.get("temperature", 0.1),
                messages=[{"role": "user", "content": full_prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"❌ Erreur Anthropic: {e}")
            raise
    
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parser la réponse JSON de Claude"""
        try:
            # Claude peut parfois ajouter du texte avant/après le JSON
            response = response.strip()
            
            # Extraire le JSON s'il y a du texte supplémentaire
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start != -1 and end != 0:
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                return json.loads(response)
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erreur parsing JSON Claude: {e}")
            return {"erreur": "Réponse invalide", "response_brute": response}
    
    async def health_check(self) -> bool:
        """Vérifier la disponibilité de Claude"""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Test"}]
            )
            return True
        except:
            return False

class OllamaService(BaseLLMService):
    """Service Ollama (local)"""
    
    # 🚀 Modèle par défaut optimisé pour la rapidité (qwen2.5:3b au lieu de 7b)
    def __init__(self, model: str = "qwen2.5:3b", base_url: str = "http://localhost:11434", **kwargs):
        super().__init__(None, model, **kwargs)
        self.base_url = base_url
        self.sync_client = None
        
        try:
            import httpx
            self.client = httpx.AsyncClient()
            self.sync_client = httpx.Client(timeout=120.0)
        except ImportError:
            raise ImportError("Le package 'httpx' est requis pour utiliser Ollama")
    
    def generate_response(self, prompt: str, parameters: Dict[str, Any] = None) -> str:
        """
        Version SYNCHRONE pour appeler Ollama - utilisée par ComplaintAnalysisService
        """
        try:
            params = parameters or {}
            
            full_prompt = f"""Tu es un assistant expert en analyse de documents de plaintes hospitalières françaises.

{prompt}

IMPORTANT: Réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après. Pas de commentaires, pas d'explications."""
            
            payload = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": params.get("temperature", 0.1),
                    "num_predict": params.get("max_tokens", 4000)
                }
            }
            
            logger.info(f"🤖 Appel Ollama synchrone - Modèle: {self.model}")
            
            response = self.sync_client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            
            response.raise_for_status()
            result = response.json()
            
            raw_response = result.get("response", "")
            logger.info(f"✅ Réponse Ollama reçue ({len(raw_response)} caractères)")
            
            # Extraire le JSON de la réponse
            return self._extract_json_from_response(raw_response)
            
        except Exception as e:
            logger.error(f"❌ Erreur Ollama synchrone: {e}")
            # Fallback vers la simulation
            return super().generate_response(prompt, parameters)
    
    def _extract_json_from_response(self, response: str) -> str:
        """Extrait le JSON d'une réponse qui peut contenir du texte autour"""
        response = response.strip()
        
        # Chercher le premier { et le dernier }
        start = response.find('{')
        end = response.rfind('}')
        
        if start != -1 and end != -1 and end > start:
            json_str = response[start:end + 1]
            # Valider que c'est du JSON valide
            try:
                json.loads(json_str)
                return json_str
            except json.JSONDecodeError:
                logger.warning("⚠️ JSON extrait invalide, retour de la réponse brute")
                return response
        
        return response
    
    async def analyze(self, prompt: str, parameters: Dict[str, Any] = None) -> str:
        """Analyser avec Ollama"""
        try:
            params = parameters or {}
            
            full_prompt = f"""Vous êtes un assistant spécialisé dans l'analyse des plaintes hospitalières.
            
{prompt}

Répondez uniquement avec un JSON valide."""
            
            payload = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": params.get("temperature", 0.1),
                    "num_predict": params.get("max_tokens", 2000)
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120
            )
            
            response.raise_for_status()
            result = response.json()
            
            return result.get("response", "")
            
        except Exception as e:
            logger.error(f"❌ Erreur Ollama: {e}")
            raise
    
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parser la réponse JSON d'Ollama"""
        try:
            # Ollama peut retourner du texte avant/après le JSON
            response = response.strip()
            
            # Extraire le JSON
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start != -1 and end != 0:
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                # Fallback si pas de JSON détecté
                return {"erreur": "Pas de JSON trouvé", "response_brute": response}
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erreur parsing JSON Ollama: {e}")
            return {"erreur": "Réponse invalide", "response_brute": response}
    
    async def health_check(self) -> bool:
        """Vérifier la disponibilité d'Ollama"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except:
            return False

class FallbackService(BaseLLMService):
    """Service de fallback quand aucun LLM n'est disponible"""
    
    def __init__(self):
        super().__init__()
    
    async def analyze(self, prompt: str, parameters: Dict[str, Any] = None) -> str:
        """Retourner une réponse de fallback"""
        logger.warning("🔄 Utilisation du service de fallback LLM")
        
        # Analyser le prompt pour donner une réponse basique
        if "sentiment" in prompt.lower():
            return json.dumps({
                "score_sentiment": 0,
                "emotion_principale": "neutre",
                "intensite": "modérée",
                "resume": "Analyse de fallback - service LLM indisponible"
            })
        
        elif "classif" in prompt.lower():
            return json.dumps({
                "categorie_principale": "Autre",
                "sous_categorie": "Non spécifié",
                "confidence": 0.1,
                "justification": "Classification de fallback"
            })
        
        elif "priorite" in prompt.lower():
            return json.dumps({
                "priorite": "NORMALE",
                "score_urgence": 0.4,
                "delai_reponse_recommande": 7,
                "justification": "Priorité de fallback"
            })
        
        else:
            return json.dumps({
                "resultat": "Service LLM indisponible",
                "methode": "fallback"
            })
    
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parser directement (déjà en JSON)"""
        return json.loads(response)
    
    async def health_check(self) -> bool:
        """Toujours disponible"""
        return True

# Factory pattern pour créer le service LLM approprié
def create_llm_service(provider: str = None) -> BaseLLMService:
    """
    Factory pour créer le service LLM (pattern Factory comme ODYSSEE)
    """
    if provider is None:
        provider = os.getenv("LLM_PROVIDER", "ollama")
    
    try:
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY manquante")
            
            model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
            return OpenAIService(api_key=api_key, model=model)
        
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY manquante")
            
            model = os.getenv("LLM_MODEL", "claude-3-haiku-20240307")
            return AnthropicService(api_key=api_key, model=model)
        
        elif provider == "ollama":
            # 🚀 Modèle par défaut: qwen2.5:3b (plus rapide que 7b, bon compromis qualité/vitesse)
            model = os.getenv("LLM_MODEL", "qwen2.5:3b")
            base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
            return OllamaService(model=model, base_url=base_url)
        
        else:
            raise ValueError(f"Provider LLM non supporté: {provider}")
    
    except Exception as e:
        logger.error(f"❌ Erreur création service LLM {provider}: {e}")
        logger.info("🔄 Utilisation du service de fallback")
        return FallbackService()

# Instance globale (singleton pattern comme ODYSSEE)
_llm_service_instance = None

def get_llm_service() -> BaseLLMService:
    """
    Récupérer l'instance singleton du service LLM
    """
    global _llm_service_instance
    
    if _llm_service_instance is None:
        _llm_service_instance = create_llm_service()
        logger.info(f"✅ Service LLM initialisé: {type(_llm_service_instance).__name__}")
    
    return _llm_service_instance

async def test_llm_services():
    """
    Tester tous les services LLM disponibles
    """
    providers = ["openai", "anthropic", "ollama"]
    results = {}
    
    for provider in providers:
        try:
            service = create_llm_service(provider)
            is_healthy = await service.health_check()
            results[provider] = {
                "available": True,
                "healthy": is_healthy,
                "service": type(service).__name__
            }
        except Exception as e:
            results[provider] = {
                "available": False,
                "error": str(e)
            }
    
    return results