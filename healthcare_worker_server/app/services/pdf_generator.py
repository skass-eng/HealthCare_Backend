"""
Service de génération de rapports PDF pour les plaintes
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
import json

logger = logging.getLogger(__name__)

class PDFReportService:
    """Service de génération de rapports PDF pour les plaintes"""
    
    def __init__(self):
        """Initialise le service de génération PDF"""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Configure les styles personnalisés pour le PDF"""
        # Style pour le titre principal
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        ))
        
        # Style pour les sous-titres
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=12,
            textColor=colors.darkblue
        ))
        
        # Style pour le contenu
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            alignment=TA_JUSTIFY
        ))
        
        # Style pour les métadonnées
        self.styles.add(ParagraphStyle(
            name='Metadata',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            spaceAfter=4
        ))
    
    def generate_complaint_report(self, plainte_data: Dict[str, Any], 
                                analysis_results: Dict[str, Any],
                                output_path: str) -> Dict[str, Any]:
        """
        Génère un rapport PDF complet pour une plainte
        
        Args:
            plainte_data: Données de la plainte
            analysis_results: Résultats de l'analyse IA
            output_path: Chemin de sortie du fichier PDF
            
        Returns:
            Dict avec le statut de génération et les métadonnées
        """
        logger.info(f"Génération du rapport PDF pour plainte ID: {plainte_data.get('id', 'N/A')}")
        
        try:
            # Créer le répertoire de sortie si nécessaire
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Créer le document PDF
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            # Construire le contenu
            story = []
            
            # En-tête du rapport
            story.extend(self._build_header(plainte_data))
            
            # Informations sur la plainte
            story.extend(self._build_complaint_info(plainte_data))
            
            # Résultats de l'analyse
            story.extend(self._build_analysis_section(analysis_results))
            
            # Pied de page avec métadonnées
            story.extend(self._build_footer())
            
            # Générer le PDF
            doc.build(story)
            
            logger.info(f"Rapport PDF généré avec succès: {output_path}")
            return {
                "success": True,
                "file_path": output_path,
                "file_size": os.path.getsize(output_path),
                "generation_time": datetime.now().isoformat(),
                "pages_count": self._estimate_pages(story)
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du PDF: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "file_path": output_path
            }
    
    def _build_header(self, plainte_data: Dict[str, Any]) -> list:
        """Construit l'en-tête du rapport"""
        story = []
        
        # Titre principal
        title = f"RAPPORT D'ANALYSE - PLAINTE #{plainte_data.get('id', 'N/A')}"
        story.append(Paragraph(title, self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Informations générales
        date_creation = plainte_data.get('date_creation', 'N/A')
        if date_creation != 'N/A':
            try:
                date_obj = datetime.fromisoformat(date_creation.replace('Z', '+00:00'))
                date_creation = date_obj.strftime('%d/%m/%Y à %H:%M')
            except:
                pass
        
        header_data = [
            ['Date de création:', date_creation],
            ['Statut:', plainte_data.get('statut', 'N/A')],
            ['Service concerné:', plainte_data.get('service_concerne', 'N/A')],
            ['Gravité perçue:', plainte_data.get('gravite_percue', 'N/A')]
        ]
        
        header_table = Table(header_data, colWidths=[4*cm, 10*cm])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(header_table)
        story.append(Spacer(1, 20))
        
        return story
    
    def _build_complaint_info(self, plainte_data: Dict[str, Any]) -> list:
        """Construit la section d'informations sur la plainte"""
        story = []
        
        story.append(Paragraph("INFORMATIONS SUR LA PLAINTE", self.styles['CustomHeading']))
        
        # Informations du plaignant
        story.append(Paragraph("Plaignant:", self.styles['Heading3']))
        plaignant_info = f"""
        <b>Nom:</b> {plainte_data.get('nom_plaignant', 'N/A')} {plainte_data.get('prenom_plaignant', '')}<br/>
        <b>Téléphone:</b> {plainte_data.get('telephone_plaignant', 'N/A')}<br/>
        <b>Email:</b> {plainte_data.get('email_plaignant', 'N/A')}<br/>
        <b>Adresse:</b> {plainte_data.get('adresse_plaignant', 'N/A')}
        """
        story.append(Paragraph(plaignant_info, self.styles['CustomBody']))
        story.append(Spacer(1, 10))
        
        # Description du problème
        story.append(Paragraph("Description du problème:", self.styles['Heading3']))
        description = plainte_data.get('description_probleme', 'Aucune description fournie')
        story.append(Paragraph(description, self.styles['CustomBody']))
        story.append(Spacer(1, 15))
        
        return story
    
    def _build_analysis_section(self, analysis_results: Dict[str, Any]) -> list:
        """Construit la section des résultats d'analyse"""
        story = []
        
        story.append(Paragraph("RÉSULTATS DE L'ANALYSE IA", self.styles['CustomHeading']))
        
        # Analyse de sentiment
        if 'sentiment' in analysis_results:
            story.extend(self._build_sentiment_analysis(analysis_results['sentiment']))
        
        # Résumé
        if 'summary' in analysis_results:
            story.extend(self._build_summary_analysis(analysis_results['summary']))
        
        # Contacts
        if 'contacts' in analysis_results:
            story.extend(self._build_contacts_analysis(analysis_results['contacts']))
        
        # Réponse juridique
        if 'legal_response' in analysis_results:
            story.extend(self._build_legal_response(analysis_results['legal_response']))
        
        return story
    
    def _build_sentiment_analysis(self, sentiment_data: Dict[str, Any]) -> list:
        """Construit la section d'analyse de sentiment"""
        story = []
        
        story.append(Paragraph("Analyse de sentiment:", self.styles['Heading3']))
        
        if sentiment_data.get('success', False):
            try:
                content = json.loads(sentiment_data.get('content', '{}'))
                sentiment_text = f"""
                <b>Sentiment principal:</b> {content.get('sentiment_principal', 'N/A')}<br/>
                <b>Intensité émotionnelle:</b> {content.get('intensite_emotionnelle', 'N/A')}<br/>
                <b>Score:</b> {content.get('score_sentiment', 'N/A')}<br/>
                <b>Recommandations:</b> {content.get('recommandations_reponse', 'N/A')}
                """
                story.append(Paragraph(sentiment_text, self.styles['CustomBody']))
            except json.JSONDecodeError:
                story.append(Paragraph(sentiment_data.get('content', 'Erreur de parsing'), self.styles['CustomBody']))
        else:
            story.append(Paragraph(f"Erreur: {sentiment_data.get('error', 'Analyse échouée')}", self.styles['CustomBody']))
        
        story.append(Spacer(1, 10))
        return story
    
    def _build_summary_analysis(self, summary_data: Dict[str, Any]) -> list:
        """Construit la section de résumé"""
        story = []
        
        story.append(Paragraph("Résumé exécutif:", self.styles['Heading3']))
        
        if summary_data.get('success', False):
            try:
                content = json.loads(summary_data.get('content', '{}'))
                summary_text = f"""
                <b>Résumé:</b> {content.get('resume_executif', 'N/A')}<br/>
                <b>Nature du problème:</b> {content.get('nature_probleme', 'N/A')}<br/>
                <b>Demande du plaignant:</b> {content.get('demande_plaignant', 'N/A')}<br/>
                <b>Gravité estimée:</b> {content.get('gravite_estimee', 'N/A')}
                """
                story.append(Paragraph(summary_text, self.styles['CustomBody']))
            except json.JSONDecodeError:
                story.append(Paragraph(summary_data.get('content', 'Erreur de parsing'), self.styles['CustomBody']))
        else:
            story.append(Paragraph(f"Erreur: {summary_data.get('error', 'Résumé échoué')}", self.styles['CustomBody']))
        
        story.append(Spacer(1, 10))
        return story
    
    def _build_contacts_analysis(self, contacts_data: Dict[str, Any]) -> list:
        """Construit la section des contacts"""
        story = []
        
        story.append(Paragraph("Contacts identifiés:", self.styles['Heading3']))
        
        if contacts_data.get('success', False):
            try:
                content = json.loads(contacts_data.get('content', '{}'))
                
                # Personnes mentionnées
                personnes = content.get('personnes_mentionnees', [])
                if personnes:
                    story.append(Paragraph("<b>Personnes mentionnées:</b>", self.styles['CustomBody']))
                    for personne in personnes:
                        person_text = f"• {personne.get('nom', 'N/A')} ({personne.get('fonction', 'N/A')})"
                        story.append(Paragraph(person_text, self.styles['CustomBody']))
                
                # Services
                services = content.get('services_departements', [])
                if services:
                    story.append(Paragraph("<b>Services/Départements:</b>", self.styles['CustomBody']))
                    for service in services:
                        service_text = f"• {service.get('nom', 'N/A')}"
                        story.append(Paragraph(service_text, self.styles['CustomBody']))
                        
            except json.JSONDecodeError:
                story.append(Paragraph(contacts_data.get('content', 'Erreur de parsing'), self.styles['CustomBody']))
        else:
            story.append(Paragraph(f"Erreur: {contacts_data.get('error', 'Extraction échouée')}", self.styles['CustomBody']))
        
        story.append(Spacer(1, 10))
        return story
    
    def _build_legal_response(self, legal_data: Dict[str, Any]) -> list:
        """Construit la section de réponse juridique"""
        story = []
        
        story.append(Paragraph("RÉPONSE JURIDIQUE OFFICIELLE", self.styles['CustomHeading']))
        
        if legal_data.get('success', False):
            try:
                content = json.loads(legal_data.get('content', '{}'))
                response_text = content.get('reponse_officielle', 'Aucune réponse générée')
                story.append(Paragraph(response_text, self.styles['CustomBody']))
                
                # Actions proposées
                actions = content.get('actions_proposees', [])
                if actions:
                    story.append(Spacer(1, 10))
                    story.append(Paragraph("<b>Actions proposées:</b>", self.styles['CustomBody']))
                    for action in actions:
                        story.append(Paragraph(f"• {action}", self.styles['CustomBody']))
                        
            except json.JSONDecodeError:
                story.append(Paragraph(legal_data.get('content', 'Erreur de parsing'), self.styles['CustomBody']))
        else:
            story.append(Paragraph(f"Erreur: {legal_data.get('error', 'Réponse échouée')}", self.styles['CustomBody']))
        
        return story
    
    def _build_footer(self) -> list:
        """Construit le pied de page"""
        story = []
        
        story.append(Spacer(1, 30))
        footer_text = f"""
        <i>Rapport généré automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M')}<br/>
        Système de Gestion des Plaintes - Architecture ODYSSEE</i>
        """
        story.append(Paragraph(footer_text, self.styles['Metadata']))
        
        return story
    
    def _estimate_pages(self, story) -> int:
        """Estime le nombre de pages du document"""
        # Estimation basique - peut être améliorée
        return max(1, len(story) // 10)
