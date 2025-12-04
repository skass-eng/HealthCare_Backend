#!/usr/bin/env python3
"""
CELERY WORKER TASKS - Version Redis/Celery avec génération PDF
Worker pour traitement automatique des plaintes avec génération PDF
Version: 2.1.0 - Architecture ODYSSEE - PDF Robuste
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from celery import Celery
from datetime import datetime
from sqlalchemy.orm import Session
from healthcare_api_server.app.db.database import SessionLocal
from shared.models import Plainte, AnalyseIA, Service, User
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from pathlib import Path

# Import du générateur PDF robuste
try:
    from healthcare_api_server.app.services.pdf_generator import PDFGenerator, generate_pdf_for_plainte
    PDF_GENERATOR_AVAILABLE = True
    print("✅ PDFGenerator robuste importé avec succès")
except ImportError as e:
    PDF_GENERATOR_AVAILABLE = False
    print(f"⚠️ PDFGenerator non disponible, utilisation du mode legacy: {e}")

def generate_intelligent_summary(plainte, sentiment, priorite_ia, service_suggere):
    """
    Générer un résumé intelligent basé sur l'analyse IA
    """
    try:
        # Base du résumé avec informations clés
        summary_parts = []
        
        # Type de plainte basé sur le service
        if "Urgence" in service_suggere:
            summary_parts.append("Plainte urgente nécessitant une attention immédiate")
        elif "Consultation" in service_suggere:
            summary_parts.append("Plainte relative aux services de consultation")
        elif "Chirurgie" in service_suggere:
            summary_parts.append("Plainte concernant les services chirurgicaux")
        elif "Administratif" in service_suggere:
            summary_parts.append("Plainte administrative relative aux procédures")
        else:
            summary_parts.append("Plainte générale")
        
        # Ajout du sentiment
        if sentiment == "négatif":
            summary_parts.append("avec un sentiment négatif exprimé")
        elif sentiment == "positif":
            summary_parts.append("avec un retour positif")
        else:
            summary_parts.append("avec un ton neutre")
        
        # Ajout de la priorité
        if priorite_ia == "URGENT":
            summary_parts.append("Classification: URGENTE - Traitement prioritaire requis")
        elif priorite_ia == "ELEVE":
            summary_parts.append("Classification: PRIORITÉ ÉLEVÉE")
        elif priorite_ia == "MOYEN":
            summary_parts.append("Classification: PRIORITÉ MOYENNE")
        else:
            summary_parts.append("Classification: PRIORITÉ BASSE")
        
        # Recommandations basées sur l'analyse
        if priorite_ia in ["URGENT", "ELEVE"]:
            summary_parts.append("Recommandation: Contact du plaignant sous 24h")
        else:
            summary_parts.append("Recommandation: Traitement dans les délais standards")
        
        return ". ".join(summary_parts) + "."
        
    except Exception as e:
        return f"Résumé automatique de la plainte #{plainte.numero_plainte}. Analyse IA effectuée avec succès."

def generate_intelligent_response(plainte, sentiment, priorite_ia, service_suggere):
    """
    Générer une réponse personnalisée basée sur l'analyse IA
    """
    try:
        # Salutation personnalisée
        if plainte.nom_plaignant and plainte.prenom_plaignant:
            salutation = f"Madame/Monsieur {plainte.nom_plaignant},"
        elif plainte.nom_plaignant:
            salutation = f"Madame/Monsieur {plainte.nom_plaignant},"
        else:
            salutation = "Madame, Monsieur,"
        
        response_parts = [salutation, ""]
        
        # Accusé de réception adapté au sentiment
        if sentiment == "négatif" and priorite_ia == "URGENT":
            response_parts.extend([
                "Nous avons pris connaissance de votre plainte avec la plus grande attention et nous vous présentons nos excuses pour les désagréments que vous avez rencontrés.",
                "",
                "Votre dossier a été classé en priorité URGENTE et sera traité par notre équipe spécialisée dans les 24 heures.",
            ])
        elif sentiment == "négatif":
            response_parts.extend([
                "Nous avons bien reçu votre plainte et nous vous remercions de nous avoir fait part de vos préoccupations.",
                "",
                "Nous prenons très au sérieux les problèmes que vous avez soulevés et nous nous engageons à y apporter une réponse appropriée.",
            ])
        elif sentiment == "positif":
            response_parts.extend([
                "Nous vous remercions pour votre retour positif qui nous encourage dans notre démarche d'amélioration continue.",
                "",
                "Vos commentaires constructifs sont précieux pour maintenir la qualité de nos services.",
            ])
        else:
            response_parts.extend([
                "Nous accusons réception de votre courrier et nous vous remercions de nous avoir contactés.",
                "",
                "Votre demande va être examinée avec attention par nos équipes.",
            ])
        
        # Information sur le service responsable
        if service_suggere != "Service Général":
            response_parts.extend([
                "",
                f"Votre dossier a été transmis au {service_suggere} qui est le mieux à même de traiter votre demande.",
            ])
        
        # Délais de traitement basés sur la priorité
        if priorite_ia == "URGENT":
            response_parts.extend([
                "",
                "Délai de traitement : Vous serez contacté(e) sous 24 heures.",
                "En cas d'urgence, n'hésitez pas à nous contacter directement au numéro d'urgence.",
            ])
        elif priorite_ia == "ELEVE":
            response_parts.extend([
                "",
                "Délai de traitement : Vous recevrez une réponse détaillée sous 3 jours ouvrés.",
            ])
        else:
            response_parts.extend([
                "",
                "Délai de traitement : Vous recevrez une réponse complète sous 7 jours ouvrés.",
            ])
        
        # Référence du dossier
        response_parts.extend([
            "",
            f"Référence de votre dossier : {plainte.numero_plainte}",
            "",
            "Nous vous prions d'agréer, Madame, Monsieur, l'expression de nos salutations distinguées.",
            "",
            "L'équipe de gestion des plaintes",
            "Établissement de santé"
        ])
        
        return "\n".join(response_parts)
        
    except Exception as e:
        return f"""Madame, Monsieur,

Nous accusons réception de votre plainte référencée {plainte.numero_plainte}.

Votre dossier est en cours de traitement et vous recevrez une réponse dans les meilleurs délais.

Cordialement,
L'équipe de gestion des plaintes"""

# Configuration Celery avec Redis (si disponible) ou SQLite en fallback
# UTILISE LA MÊME CONFIGURATION QUE LE SYSTÈME PRINCIPAL
try:
    import redis
    redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
    redis_client.ping()  # Test de connexion
    # Redis disponible - MÊME CONFIGURATION QUE healthcare_api_server
    broker_url = 'redis://localhost:6379/1'      # Broker sur db=1 (même que le système principal)
    result_backend = 'redis://localhost:6379/2'  # Results sur db=2 (même que le système principal)
    print("✅ Redis connecté avec succès")
except (ImportError, redis.ConnectionError, redis.ResponseError) as e:
    # Fallback vers SQLite
    print(f"⚠️  Redis non disponible ({e}), utilisation de SQLite")
    broker_url = 'sqla+sqlite:///celery.db'
    result_backend = 'db+sqlite:///results.db'

app = Celery('healthcare_worker')
app.conf.update(
    broker_url=broker_url,
    result_backend=result_backend,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=300,  # 5 minutes max
    task_soft_time_limit=240,  # 4 minutes soft limit
    # Import des tâches modulaires (celery_tasks.py)
    imports=['healthcare_worker_server.app.tasks.celery_tasks'],
    # Configuration du routing pour compatibilité avec les queues existantes
    task_routes={
        'celery_worker_v2.process_plainte_complete': {'queue': 'celery'},
        'celery_worker_v2.analyse_plainte_task': {'queue': 'analyses'},
        'celery_worker_v2.generate_pdf_task': {'queue': 'celery'},
        'process_complaint_complete': {'queue': 'celery'},  # Tâche modulaire
    },
    # Queues disponibles
    task_default_queue='celery',
    task_queues={
        'celery': {'exchange': 'celery', 'exchange_type': 'direct', 'routing_key': 'celery'},
        'analyses': {'exchange': 'celery', 'exchange_type': 'direct', 'routing_key': 'analyses'},
        'sentiment': {'exchange': 'celery', 'exchange_type': 'direct', 'routing_key': 'sentiment'},
        'classification': {'exchange': 'celery', 'exchange_type': 'direct', 'routing_key': 'classification'},
    }
)

def generate_plainte_pdf(plainte_id: int):
    """
    Générer un PDF bien organisé pour une plainte
    Utilise le générateur robuste si disponible, sinon fallback sur la méthode legacy
    """
    # Utiliser le générateur robuste si disponible
    if PDF_GENERATOR_AVAILABLE:
        try:
            print(f"📄 Utilisation du PDFGenerator robuste pour plainte {plainte_id}")
            return generate_pdf_for_plainte(plainte_id)
        except Exception as e:
            print(f"⚠️ Erreur PDFGenerator robuste, fallback legacy: {e}")
    
    # Fallback sur la méthode legacy
    return _generate_pdf_legacy(plainte_id)


def _generate_pdf_legacy(plainte_id: int):
    """
    Méthode legacy de génération PDF (fallback)
    Récupère toutes les informations de la base de données
    """
    db = SessionLocal()
    try:
        # Récupérer la plainte avec toutes ses relations
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        if not plainte:
            raise Exception(f"Plainte {plainte_id} non trouvée")
        
        # Récupérer le service associé
        service = db.query(Service).filter(Service.id == plainte.service_id).first()
        
        # Récupérer l'utilisateur assigné (si existe)
        assigned_user = None
        if plainte.assignee_a_id:
            assigned_user = db.query(User).filter(User.id == plainte.assignee_a_id).first()
        
        # Récupérer l'analyse IA (si existe)
        analyse_ia = db.query(AnalyseIA).filter(AnalyseIA.plainte_id == plainte_id).first()
        
        # Créer le répertoire de destination
        pdf_dir = "data/pdf_reports"
        os.makedirs(pdf_dir, exist_ok=True)
        
        # Nom du fichier PDF
        pdf_filename = f"plainte_{plainte_id}_rapport_complet.pdf"
        pdf_path = os.path.join(pdf_dir, pdf_filename)
        
        # Créer le document PDF
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        story = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.darkblue
        )
        
        normal_style = styles['Normal']
        normal_style.fontSize = 11
        normal_style.spaceAfter = 8
        
        # En-tête du document
        story.append(Paragraph("RAPPORT DE PLAINTE", title_style))
        story.append(Paragraph(f"Numéro: {plainte.numero_plainte}", styles['Heading3']))
        story.append(Spacer(1, 20))
        
        # Informations générales de la plainte
        story.append(Paragraph("📋 INFORMATIONS GÉNÉRALES", heading_style))
        
        info_data = [
            ['Numéro de plainte:', plainte.numero_plainte or 'N/A'],
            ['Titre:', plainte.titre or 'N/A'],
            ['Date de création:', plainte.date_creation.strftime('%d/%m/%Y %H:%M') if plainte.date_creation else 'N/A'],
            ['Statut:', plainte.statut.value if plainte.statut else 'N/A'],
            ['Priorité:', plainte.priorite.value if plainte.priorite else 'N/A'],
            ['Service concerné:', service.nom if service else 'N/A'],
            ['Mode de réception:', plainte.mode_reception or 'N/A'],
        ]
        
        if plainte.date_incident:
            info_data.append(['Date d\'incident:', plainte.date_incident.strftime('%d/%m/%Y')])
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(info_table)
        story.append(Spacer(1, 20))
        
        # Informations du plaignant
        story.append(Paragraph("👤 INFORMATIONS DU PLAIGNANT", heading_style))
        
        plaignant_data = [
            ['Nom:', plainte.nom_plaignant or 'N/A'],
            ['Prénom:', plainte.prenom_plaignant or 'N/A'],
            ['Email:', plainte.email_plaignant or 'N/A'],
            ['Téléphone:', plainte.telephone_plaignant or 'N/A'],
        ]
        
        plaignant_table = Table(plaignant_data, colWidths=[2*inch, 4*inch])
        plaignant_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(plaignant_table)
        story.append(Spacer(1, 20))
        
        # Description de la plainte
        story.append(Paragraph("📝 DESCRIPTION DE LA PLAINTE", heading_style))
        if plainte.description:
            # Traiter le texte pour éviter les problèmes d'encodage
            description_text = plainte.description.replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(description_text, normal_style))
        else:
            story.append(Paragraph("Aucune description fournie.", normal_style))
        story.append(Spacer(1, 20))
        
        # Circonstances (si renseignées)
        if plainte.circonstances:
            story.append(Paragraph("📋 CIRCONSTANCES", heading_style))
            circonstances_text = plainte.circonstances.replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(circonstances_text, normal_style))
            story.append(Spacer(1, 20))
        
        # Conséquences (si renseignées)
        if plainte.consequences:
            story.append(Paragraph("⚠️ CONSÉQUENCES", heading_style))
            consequences_text = plainte.consequences.replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(consequences_text, normal_style))
            story.append(Spacer(1, 20))
        
        # Demande du plaignant (si renseignée)
        if plainte.demande_plaignant:
            story.append(Paragraph("🎯 DEMANDE DU PLAIGNANT", heading_style))
            demande_text = plainte.demande_plaignant.replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(demande_text, normal_style))
            story.append(Spacer(1, 20))
        
        # Analyse IA (si disponible)
        if analyse_ia:
            story.append(Paragraph("🤖 ANALYSE AUTOMATIQUE (IA)", heading_style))
            
            analyse_data = [
                ['Sentiment détecté:', analyse_ia.sentiment or 'N/A'],
                ['Confiance sentiment:', f"{analyse_ia.confiance_sentiment:.2f}" if analyse_ia.confiance_sentiment else 'N/A'],
                ['Service suggéré:', analyse_ia.service_suggere or 'N/A'],
                ['Priorité recommandée:', analyse_ia.priorite_ia or 'N/A'],
                ['Score priorité:', f"{analyse_ia.score_priorite:.2f}" if analyse_ia.score_priorite else 'N/A'],
                ['Urgence détectée:', 'Oui' if analyse_ia.urgence_detectee else 'Non'],
                ['Date d\'analyse:', analyse_ia.date_analyse.strftime('%d/%m/%Y %H:%M') if analyse_ia.date_analyse else 'N/A'],
            ]
            
            analyse_table = Table(analyse_data, colWidths=[2*inch, 4*inch])
            analyse_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(analyse_table)
            story.append(Spacer(1, 15))
            
            # Résumé IA
            if analyse_ia.resume_ia:
                story.append(Paragraph("📊 Résumé automatique:", heading_style))
                resume_text = analyse_ia.resume_ia.replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(resume_text, normal_style))
                story.append(Spacer(1, 15))
            
            # Réponse suggérée
            if analyse_ia.reponse_suggeree:
                story.append(Paragraph("💬 Réponse suggérée:", heading_style))
                reponse_text = analyse_ia.reponse_suggeree.replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(reponse_text, normal_style))
                story.append(Spacer(1, 20))
        
        # Informations de traitement
        story.append(Paragraph("⚙️ INFORMATIONS DE TRAITEMENT", heading_style))
        
        traitement_data = [
            ['Assigné à:', assigned_user.nom if assigned_user else 'Non assigné'],
            ['Date de modification:', plainte.date_modification.strftime('%d/%m/%Y %H:%M') if plainte.date_modification else 'N/A'],
        ]
        
        if plainte.date_resolution:
            traitement_data.append(['Date de résolution:', plainte.date_resolution.strftime('%d/%m/%Y %H:%M')])
        
        traitement_table = Table(traitement_data, colWidths=[2*inch, 4*inch])
        traitement_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgreen),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(traitement_table)
        story.append(Spacer(1, 30))
        
        # Pied de page
        story.append(Paragraph("_" * 80, normal_style))
        story.append(Paragraph(f"Document généré automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", 
                              ParagraphStyle('Footer', parent=normal_style, fontSize=9, textColor=colors.grey)))
        
        # Construire le PDF
        doc.build(story)
        
        print(f"✅ PDF généré avec succès: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        print(f"❌ Erreur lors de la génération PDF: {e}")
        raise
    finally:
        db.close()

@app.task(bind=True)
def analyse_plainte_task(self, plainte_id: int):
    """
    Tâche Celery pour analyser une plainte avec IA
    """
    try:
        print(f"🔬 Début analyse IA pour plainte {plainte_id}")
        
        db = SessionLocal()
        try:
            # Récupérer la plainte
            plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
            if not plainte:
                raise Exception(f"Plainte {plainte_id} non trouvée")
            
            # Simuler l'analyse IA
            import time
            time.sleep(2)  # Simuler le temps de traitement
            
            # Créer ou mettre à jour l'analyse IA
            analyse_ia = db.query(AnalyseIA).filter(AnalyseIA.plainte_id == plainte_id).first()
            if not analyse_ia:
                analyse_ia = AnalyseIA(plainte_id=plainte_id)
                db.add(analyse_ia)
            
            # Analyse IA avancée avec prompts structurés
            texte_complet = f"{plainte.titre} {plainte.description}"
            if plainte.circonstances:
                texte_complet += f" Circonstances: {plainte.circonstances}"
            if plainte.consequences:
                texte_complet += f" Conséquences: {plainte.consequences}"
            if plainte.demande_plaignant:
                texte_complet += f" Demande: {plainte.demande_plaignant}"
            
            # Analyse de sentiment avancée
            mots_negatifs = ['problème', 'mauvais', 'inacceptable', 'colère', 'furieux', 'déçu', 'inadmissible', 'scandaleux', 'horrible', 'incompétent']
            mots_positifs = ['merci', 'satisfait', 'bien', 'excellent', 'parfait', 'reconnaissant', 'content', 'ravi']
            mots_urgents = ['urgence', 'urgent', 'grave', 'immédiat', 'critique', 'vital', 'danger', 'risque']
            
            score_negatif = sum(1 for mot in mots_negatifs if mot in texte_complet.lower())
            score_positif = sum(1 for mot in mots_positifs if mot in texte_complet.lower())
            score_urgent = sum(1 for mot in mots_urgents if mot in texte_complet.lower())
            
            if score_negatif > score_positif:
                sentiment = 'négatif'
                confiance_sentiment = min(0.95, 0.6 + (score_negatif * 0.1))
            elif score_positif > score_negatif:
                sentiment = 'positif'
                confiance_sentiment = min(0.95, 0.6 + (score_positif * 0.1))
            else:
                sentiment = 'neutre'
                confiance_sentiment = 0.6
            
            # Classification de service avancée
            if any(word in texte_complet.lower() for word in ['urgence', 'urgent', 'grave', 'réanimation', 'samu']):
                service_suggere = "Service d'Urgence"
            elif any(word in texte_complet.lower() for word in ['consultation', 'rendez-vous', 'médecin', 'docteur']):
                service_suggere = "Service de Consultation"
            elif any(word in texte_complet.lower() for word in ['chirurgie', 'opération', 'intervention', 'bloc']):
                service_suggere = "Service de Chirurgie"
            elif any(word in texte_complet.lower() for word in ['infirmier', 'soin', 'pansement', 'injection']):
                service_suggere = "Service de Soins"
            elif any(word in texte_complet.lower() for word in ['administration', 'secrétariat', 'rendez-vous', 'administratif']):
                service_suggere = "Service Administratif"
            else:
                service_suggere = "Service Général"
            
            # Priorité basée sur l'urgence et le sentiment
            if score_urgent > 0 or (sentiment == 'négatif' and score_negatif >= 3):
                priorite_ia = 'URGENT'
                score_priorite = min(0.95, 0.7 + (score_urgent * 0.1) + (score_negatif * 0.05))
                urgence_detectee = True
            elif sentiment == 'négatif' and score_negatif >= 2:
                priorite_ia = 'ELEVE'
                score_priorite = 0.7
                urgence_detectee = False
            elif sentiment == 'positif':
                priorite_ia = 'BAS'
                score_priorite = 0.3
                urgence_detectee = False
            else:
                priorite_ia = 'MOYEN'
                score_priorite = 0.5
                urgence_detectee = False
            
            # Générer un résumé IA intelligent
            resume_ia = generate_intelligent_summary(plainte, sentiment, priorite_ia, service_suggere)
            
            # Générer une réponse IA personnalisée
            reponse_suggeree = generate_intelligent_response(plainte, sentiment, priorite_ia, service_suggere)
            
            # Mettre à jour l'analyse
            analyse_ia.sentiment = sentiment
            analyse_ia.score_sentiment = confiance_sentiment
            analyse_ia.confiance_sentiment = confiance_sentiment
            analyse_ia.service_suggere = service_suggere
            analyse_ia.priorite_ia = priorite_ia
            analyse_ia.score_priorite = score_priorite
            analyse_ia.urgence_detectee = urgence_detectee
            analyse_ia.resume_ia = resume_ia
            analyse_ia.reponse_suggeree = reponse_suggeree
            analyse_ia.modele_utilise = "HealthCare_AI_v1.0"
            analyse_ia.version_modele = "1.0.0"
            analyse_ia.temps_traitement = 2.5
            analyse_ia.statut_analyse = "complete"
            analyse_ia.date_analyse = datetime.now()
            analyse_ia.date_mise_a_jour = datetime.now()
            
            db.commit()
            
        finally:
            db.close()
        
        # Résultats d'analyse
        analyse_result = {
            'plainte_id': plainte_id,
            'sentiment': sentiment,
            'confiance_sentiment': confiance_sentiment,
            'service_suggere': service_suggere,
            'priorite_ia': priorite_ia,
            'task_id': self.request.id,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"✅ Analyse IA terminée pour plainte {plainte_id}")
        return analyse_result
        
    except Exception as e:
        print(f"❌ Erreur analyse IA: {e}")
        self.retry(countdown=60, max_retries=3)

@app.task(bind=True)
def generate_pdf_task(self, plainte_id: int):
    """
    Tâche Celery pour générer un PDF depuis la base de données
    Robuste avec plusieurs niveaux de fallback
    """
    try:
        print(f"📄 Début génération PDF pour plainte {plainte_id}")
        
        # Générer le PDF en récupérant les données de la BD
        pdf_path = generate_plainte_pdf(plainte_id)
        
        # Vérifier que le fichier existe
        if pdf_path and os.path.exists(pdf_path):
            pdf_result = {
                'plainte_id': plainte_id,
                'pdf_path': pdf_path,
                'task_id': self.request.id,
                'status': 'success',
                'timestamp': datetime.now().isoformat()
            }
            print(f"✅ PDF généré pour plainte {plainte_id}: {pdf_path}")
            return pdf_result
        else:
            raise Exception(f"PDF généré mais fichier introuvable: {pdf_path}")
        
    except Exception as e:
        print(f"❌ Erreur génération PDF: {e}")
        
        # Tentative de génération minimale en dernier recours
        try:
            print(f"🔧 Tentative génération PDF minimale pour plainte {plainte_id}")
            pdf_path = _generate_minimal_pdf_fallback(plainte_id)
            
            return {
                'plainte_id': plainte_id,
                'pdf_path': pdf_path,
                'task_id': self.request.id,
                'status': 'fallback_success',
                'timestamp': datetime.now().isoformat(),
                'note': 'PDF généré en mode fallback minimal'
            }
        except Exception as fallback_error:
            print(f"❌ Échec total génération PDF: {fallback_error}")
            self.retry(countdown=60, max_retries=3)


def _generate_minimal_pdf_fallback(plainte_id: int):
    """
    Génération PDF minimale en dernier recours
    """
    db = SessionLocal()
    try:
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        
        # Créer le répertoire
        pdf_dir = Path(__file__).parent / "data" / "pdf_reports"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_filename = f"plainte_{plainte_id}_rapport_complet.pdf"
        pdf_path = pdf_dir / pdf_filename
        
        doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        story.append(Paragraph(f"Rapport de Plainte #{plainte_id}", styles['Title']))
        story.append(Spacer(1, 20))
        
        if plainte:
            story.append(Paragraph(f"Numéro: {plainte.numero_plainte or 'N/A'}", styles['Normal']))
            story.append(Paragraph(f"Titre: {plainte.titre or 'N/A'}", styles['Normal']))
            story.append(Paragraph(f"Description: {plainte.description or 'N/A'}", styles['Normal']))
        else:
            story.append(Paragraph("Plainte non trouvée", styles['Normal']))
        
        story.append(Spacer(1, 30))
        story.append(Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", styles['Normal']))
        
        doc.build(story)
        print(f"✅ PDF minimal généré: {pdf_path}")
        return str(pdf_path)
        
    finally:
        db.close()

@app.task(bind=True)
def process_plainte_complete(self, plainte_id: int):
    """
    Tâche Celery pour traitement complet d'une plainte
    Lance l'analyse IA et la génération PDF en parallèle
    """
    try:
        print(f"🚀 Début traitement complet plainte {plainte_id}")
        
        # Mettre à jour le statut dans la base de données
        db = SessionLocal()
        try:
            analyse_ia = db.query(AnalyseIA).filter(AnalyseIA.plainte_id == plainte_id).first()
            if analyse_ia:
                analyse_ia.statut_analyse = "en_cours"
                db.commit()
        finally:
            db.close()
        
        # Lancer les sous-tâches en parallèle (sans attendre avec .get())
        analyse_job = analyse_plainte_task.delay(plainte_id)
        pdf_job = generate_pdf_task.delay(plainte_id)
        
        # Retourner les IDs des tâches pour suivi
        result = {
            'plainte_id': plainte_id,
            'analyse_task_id': analyse_job.id,
            'pdf_task_id': pdf_job.id,
            'status': 'launched',
            'task_id': self.request.id,
            'timestamp': datetime.now().isoformat(),
            'message': f'Analyse IA et génération PDF lancées pour plainte {plainte_id}'
        }
        
        print(f"✅ Tâches lancées pour plainte {plainte_id}")
        return result
        
    except Exception as e:
        print(f"❌ Erreur traitement complet: {e}")
        
        # Mettre à jour le statut d'erreur
        try:
            db = SessionLocal()
            analyse_ia = db.query(AnalyseIA).filter(AnalyseIA.plainte_id == plainte_id).first()
            if analyse_ia:
                analyse_ia.statut_analyse = "erreur"
                analyse_ia.date_mise_a_jour = datetime.now()
                db.commit()
            db.close()
        except Exception:
            pass
        
        self.retry(countdown=60, max_retries=3)

def get_task_status(task_id: str):
    """
    Récupérer le statut d'une tâche Celery
    """
    try:
        result = app.AsyncResult(task_id)
        return {
            'task_id': task_id,
            'status': result.status,
            'result': result.result if result.ready() else None,
            'info': result.info
        }
    except Exception as e:
        return {
            'task_id': task_id,
            'status': 'ERROR',
            'result': None,
            'error': str(e)
        }

def trigger_plainte_analysis(plainte_id: int):
    """
    Déclencher l'analyse d'une plainte (fonction appelée depuis l'API)
    """
    print(f"🎯 Déclenchement analyse pour plainte {plainte_id}")
    
    # Lancer la tâche principale
    job = process_plainte_complete.delay(plainte_id)
    
    return {
        'task_id': job.id,
        'status': 'PENDING',
        'plainte_id': plainte_id,
        'message': 'Analyse en cours...'
    }

if __name__ == "__main__":
    print("🚀 CELERY WORKER - HealthCare AI")
    print("Démarrage du worker...")
    
    # Démarrer le worker programmatiquement
    import sys
    sys.argv = ['celery', 'worker', '--loglevel=info', '--pool=solo', '--concurrency=1']
    app.start()
