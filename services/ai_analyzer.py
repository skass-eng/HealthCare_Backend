"""
Service d'analyse IA pour analyser le contenu des plaintes
Détermine automatiquement le service, priorité, sentiment, etc.
"""

import re
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from models import ServiceEnum, PrioriteEnum

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIAnalyzer:
    """Analyseur IA pour les plaintes médicales"""
    
    def __init__(self):
        # Mots-clés pour détecter les services
        self.service_keywords = {
            ServiceEnum.CARDIOLOGIE: [
                'cardiologie', 'cardiologue', 'cœur', 'cardiaque', 'cardiovasculaire',
                'infarctus', 'angine', 'arythmie', 'pression artérielle', 'hypertension',
                'électrocardiogramme', 'ecg', 'angioplastie', 'pace maker', 'stent'
            ],
            ServiceEnum.URGENCES: [
                'urgences', 'urgence', 'samu', 'accident', 'trauma', 'chute',
                'fracture', 'hémorragie', 'overdose', 'empoisonnement', 'brûlure',
                'ambulance', 'réanimation', 'service d\'urgence', 'aux urgences'
            ],
            ServiceEnum.PEDIATRIE: [
                'pédiatrie', 'pédiatre', 'enfant', 'bébé', 'nourrisson', 'adolescent',
                'vaccination', 'croissance', 'développement', 'pédiatrique',
                'nouveau-né', 'enfance', 'jeune patient', 'mineur'
            ],
            ServiceEnum.CHIRURGIE: [
                'chirurgie', 'chirurgien', 'opération', 'intervention', 'bloc opératoire',
                'anesthésie', 'post-opératoire', 'cicatrice', 'suture', 'incision',
                'ablation', 'greffe', 'transplantation', 'prothèse'
            ],
            ServiceEnum.RADIOLOGIE: [
                'radiologie', 'radiologue', 'radio', 'scanner', 'irm', 'échographie',
                'mammographie', 'tomodensitométrie', 'imagerie', 'contraste',
                'rayons x', 'fibroscopie', 'endoscopie'
            ],
            ServiceEnum.ONCOLOGIE: [
                'oncologie', 'oncologue', 'cancer', 'tumeur', 'chimiothérapie',
                'radiothérapie', 'métastase', 'biopsie', 'carcinome', 'lymphome',
                'leucémie', 'néoplasie', 'malin', 'benin'
            ],
            ServiceEnum.NEUROLOGIE: [
                'neurologie', 'neurologue', 'cerveau', 'neurologique', 'epilepsie',
                'parkinson', 'alzheimer', 'avc', 'migraine', 'sclérose', 'paralysie',
                'nerf', 'moelle épinière', 'système nerveux'
            ],
            ServiceEnum.ORTHOPEDIE: [
                'orthopédie', 'orthopédiste', 'os', 'articulation', 'genou', 'hanche',
                'épaule', 'poignet', 'cheville', 'rhumatologie', 'arthrose', 'arthrite',
                'tendon', 'ligament', 'muscle', 'squelette'
            ]
        }
        
        # Mots-clés pour détecter la priorité
        self.priority_keywords = {
            PrioriteEnum.URGENT: [
                'urgent', 'grave', 'critique', 'immédiat', 'vital', 'danger',
                'risque de mort', 'hémorragie', 'arrêt cardiaque', 'coma',
                'choc', 'détresse', 'agonie', 'mortel', 'fatale'
            ],
            PrioriteEnum.ELEVE: [
                'important', 'sérieux', 'préoccupant', 'inquiétant', 'douleur intense',
                'infection', 'complications', 'détérioration', 'aggravation',
                'nécessite attention', 'rapidement'
            ],
            PrioriteEnum.MOYEN: [
                'moyen', 'modéré', 'normal', 'standard', 'habituel', 'courant',
                'gêne', 'inconfort', 'léger problème'
            ],
            PrioriteEnum.BAS: [
                'léger', 'mineur', 'faible', 'peu important', 'bénin',
                'sans gravité', 'consultation de routine', 'contrôle'
            ]
        }
        
        # Mots-clés pour détecter le sentiment négatif
        self.negative_sentiment_keywords = [
            'insatisfait', 'mécontent', 'déçu', 'furieux', 'colère', 'inacceptable',
            'scandaleux', 'incompétent', 'négligent', 'irresponsable', 'inadmissible',
            'honteux', 'révoltant', 'désagréable', 'impoli', 'irrespectueux',
            'mauvais', 'horrible', 'catastrophique', 'décevant', 'problème',
            'erreur', 'faute', 'manquement', 'défaillance'
        ]
        
        # Mots-clés pour détecter le sentiment positif
        self.positive_sentiment_keywords = [
            'satisfait', 'content', 'heureux', 'reconnaissant', 'merci',
            'excellent', 'parfait', 'formidable', 'professionnel', 'compétent',
            'aimable', 'attentionné', 'bienveillant', 'efficace', 'rapide',
            'qualité', 'remerciements', 'félicitations'
        ]
    
    def detect_service(self, text: str) -> Tuple[Optional[ServiceEnum], float]:
        """Détecter le service médical à partir du texte"""
        text_lower = text.lower()
        service_scores = {}
        
        for service, keywords in self.service_keywords.items():
            score = 0
            for keyword in keywords:
                # Compter les occurrences de chaque mot-clé
                count = text_lower.count(keyword.lower())
                score += count
            
            if score > 0:
                service_scores[service] = score
        
        if not service_scores:
            return None, 0.0
        
        # Prendre le service avec le score le plus élevé
        best_service = max(service_scores, key=service_scores.get)
        max_score = service_scores[best_service]
        
        # Calculer la confiance (normalisée)
        total_words = len(text.split())
        confidence = min(max_score / max(total_words * 0.1, 1), 1.0)
        
        return best_service, confidence
    
    def detect_priority(self, text: str) -> Tuple[PrioriteEnum, float]:
        """Détecter la priorité à partir du texte"""
        text_lower = text.lower()
        priority_scores = {}
        
        for priority, keywords in self.priority_keywords.items():
            score = 0
            for keyword in keywords:
                count = text_lower.count(keyword.lower())
                score += count * 2 if priority == PrioriteEnum.URGENT else count
            
            if score > 0:
                priority_scores[priority] = score
        
        if not priority_scores:
            return PrioriteEnum.MOYEN, 0.5  # Priorité par défaut
        
        best_priority = max(priority_scores, key=priority_scores.get)
        max_score = priority_scores[best_priority]
        
        # Calculer la confiance
        total_words = len(text.split())
        confidence = min(max_score / max(total_words * 0.05, 1), 1.0)
        
        return best_priority, confidence
    
    def analyze_sentiment(self, text: str) -> Tuple[float, float]:
        """Analyser le sentiment du texte (-1 = négatif, 1 = positif)"""
        text_lower = text.lower()
        
        negative_score = 0
        for keyword in self.negative_sentiment_keywords:
            negative_score += text_lower.count(keyword.lower())
        
        positive_score = 0
        for keyword in self.positive_sentiment_keywords:
            positive_score += text_lower.count(keyword.lower())
        
        total_sentiment_words = negative_score + positive_score
        
        if total_sentiment_words == 0:
            return 0.0, 0.3  # Neutre avec faible confiance
        
        # Score de sentiment entre -1 et 1
        sentiment_score = (positive_score - negative_score) / total_sentiment_words
        
        # Confiance basée sur le nombre de mots de sentiment trouvés
        total_words = len(text.split())
        confidence = min(total_sentiment_words / max(total_words * 0.1, 1), 1.0)
        
        return sentiment_score, confidence
    
    def extract_dates(self, text: str) -> List[str]:
        """Extraire les dates du texte"""
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',  # DD/MM/YYYY
            r'\d{1,2}-\d{1,2}-\d{4}',  # DD-MM-YYYY
            r'\d{4}-\d{1,2}-\d{1,2}',  # YYYY-MM-DD
            r'\d{1,2}\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}',
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        
        return dates
    
    def extract_contact_info(self, text: str) -> Dict[str, str]:
        """Extraire les informations de contact"""
        # Email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        # Téléphone
        phone_pattern = r'\b(?:\+33|0)[1-9](?:[0-9]{8})\b'
        phones = re.findall(phone_pattern, text)
        
        # Nom (patterns simples)
        name_patterns = [
            r'(?:M\.|Mme|Monsieur|Madame|Mr|Mrs)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'Je\s+suis\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'Mon\s+nom\s+est\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ]
        
        names = []
        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            names.extend(matches)
        
        return {
            'emails': emails,
            'phones': phones,
            'names': names
        }
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extraire les mots-clés importants"""
        # Mots vides français
        stop_words = {
            'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou', 'mais',
            'donc', 'car', 'ni', 'or', 'je', 'tu', 'il', 'elle', 'nous', 'vous',
            'ils', 'elles', 'ce', 'cet', 'cette', 'ces', 'mon', 'ma', 'mes',
            'ton', 'ta', 'tes', 'son', 'sa', 'ses', 'notre', 'votre', 'leur',
            'leurs', 'qui', 'que', 'quoi', 'dont', 'où', 'par', 'pour', 'avec',
            'sans', 'sous', 'sur', 'dans', 'entre', 'vers', 'chez', 'depuis',
            'pendant', 'avant', 'après', 'avoir', 'être', 'faire', 'aller',
            'voir', 'savoir', 'pouvoir', 'vouloir', 'venir', 'dire', 'prendre'
        }
        
        # Nettoyer et extraire les mots
        words = re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', text.lower())
        
        # Filtrer les mots vides et compter les occurrences
        word_count = {}
        for word in words:
            if word not in stop_words and len(word) > 2:
                word_count[word] = word_count.get(word, 0) + 1
        
        # Trier par fréquence et prendre les plus fréquents
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, count in sorted_words[:max_keywords]]
        
        return keywords
    
    def generate_summary(self, text: str, max_length: int = 200) -> str:
        """Générer un résumé du texte"""
        sentences = re.split(r'[.!?]+', text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return ""
        
        # Prendre les premières phrases jusqu'à la limite
        summary = ""
        for sentence in sentences:
            if len(summary + sentence) <= max_length:
                summary += sentence + ". "
            else:
                break
        
        return summary.strip()
    
    def analyze_complaint(self, text: str) -> Dict[str, any]:
        """Analyser complètement une plainte"""
        logger.info(f"🧠 Analyse IA du texte ({len(text)} caractères)")
        
        # Service détecté
        service, service_confidence = self.detect_service(text)
        
        # Priorité détectée
        priority, priority_confidence = self.detect_priority(text)
        
        # Sentiment
        sentiment_score, sentiment_confidence = self.analyze_sentiment(text)
        
        # Informations de contact
        contact_info = self.extract_contact_info(text)
        
        # Dates
        dates = self.extract_dates(text)
        
        # Mots-clés
        keywords = self.extract_keywords(text)
        
        # Résumé
        summary = self.generate_summary(text)
        
        # Suggestions d'actions
        suggestions = self.generate_suggestions(service, priority, sentiment_score)
        
        result = {
            'service_detecte': service.value if service else None,
            'service_confidence': service_confidence,
            'priorite_detectee': priority.value,
            'priorite_confidence': priority_confidence,
            'score_sentiment': sentiment_score,
            'sentiment_confidence': sentiment_confidence,
            'sentiment_label': self.get_sentiment_label(sentiment_score),
            'contact_info': contact_info,
            'dates_detectees': dates,
            'mots_cles': keywords,
            'resume_automatique': summary,
            'suggestions_actions': suggestions,
            'analyse_timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Analyse terminée - Service: {service}, Priorité: {priority}, Sentiment: {result['sentiment_label']}")
        
        return result
    
    def get_sentiment_label(self, score: float) -> str:
        """Convertir le score de sentiment en label"""
        if score > 0.3:
            return "Positif"
        elif score < -0.3:
            return "Négatif"
        else:
            return "Neutre"
    
    def generate_suggestions(self, service: Optional[ServiceEnum], priority: PrioriteEnum, sentiment: float) -> List[str]:
        """Générer des suggestions d'actions"""
        suggestions = []
        
        # Suggestions basées sur la priorité
        if priority == PrioriteEnum.URGENT:
            suggestions.append("Traiter en priorité absolue - contact immédiat requis")
            suggestions.append("Escalader vers la direction médicale")
        elif priority == PrioriteEnum.ELEVE:
            suggestions.append("Réponse requise sous 48h")
            suggestions.append("Investigation approfondie recommandée")
        
        # Suggestions basées sur le sentiment
        if sentiment < -0.5:
            suggestions.append("Réponse empathique et excuses personnalisées recommandées")
            suggestions.append("Suivi post-réponse nécessaire")
        elif sentiment > 0.3:
            suggestions.append("Remercier le patient pour ses commentaires positifs")
        
        # Suggestions basées sur le service
        if service:
            suggestions.append(f"Transmettre au responsable du service {service.value}")
        
        return suggestions

# Instance globale
ai_analyzer = AIAnalyzer() 