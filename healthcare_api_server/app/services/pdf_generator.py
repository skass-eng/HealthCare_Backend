#!/usr/bin/env python3
"""
SERVICE DE GÉNÉRATION PDF - HealthCare AI
Génération robuste et fiable de rapports PDF pour les plaintes
Version: 2.0.0 - Architecture ODYSSEE
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

logger = logging.getLogger(__name__)


class PDFGenerator:
    """
    Générateur PDF robuste pour les plaintes
    """
    
    def __init__(self, output_dir: str = None):
        """
        Initialiser le générateur PDF
        
        Args:
            output_dir: Répertoire de sortie pour les PDFs
        """
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            # Chemin par défaut relatif au projet
            self.output_dir = Path(__file__).parent.parent.parent.parent / "data" / "pdf_reports"
        
        # Créer le répertoire s'il n'existe pas
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Styles de base
        self._init_styles()
        
        logger.info(f"📁 PDFGenerator initialisé - Output: {self.output_dir}")
    
    def _init_styles(self):
        """Initialiser les styles PDF"""
        self.styles = getSampleStyleSheet()
        
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1e40af')
        )
        
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.HexColor('#1e40af')
        )
        
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            leading=14
        )
        
        self.footer_style = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
    
    def _safe_text(self, text: Any) -> str:
        """Convertir et sécuriser le texte pour le PDF"""
        if text is None:
            return "N/A"
        text_str = str(text)
        # Échapper les caractères spéciaux XML
        return text_str.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    def _format_date(self, date_obj: Any, format_str: str = "%d/%m/%Y %H:%M") -> str:
        """Formater une date de manière sécurisée"""
        if date_obj is None:
            return "N/A"
        try:
            if hasattr(date_obj, 'strftime'):
                return date_obj.strftime(format_str)
            return str(date_obj)
        except Exception:
            return "N/A"
    
    def _create_info_table(self, data: list, header_color: colors.Color = colors.HexColor('#e5e7eb')) -> Table:
        """Créer un tableau d'informations formaté"""
        table = Table(data, colWidths=[2.2*inch, 4.3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), header_color),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        return table
    
    def generate_plainte_pdf(self, plainte_data: Dict[str, Any], 
                             service_data: Dict[str, Any] = None,
                             user_data: Dict[str, Any] = None,
                             analyse_ia_data: Dict[str, Any] = None) -> str:
        """
        Générer un PDF complet pour une plainte
        
        Args:
            plainte_data: Données de la plainte (dict ou objet SQLAlchemy)
            service_data: Données du service (optionnel)
            user_data: Données de l'utilisateur assigné (optionnel)
            analyse_ia_data: Données de l'analyse IA (optionnel)
        
        Returns:
            str: Chemin du PDF généré
        """
        try:
            # Extraire l'ID de la plainte
            plainte_id = self._get_attr(plainte_data, 'id', 'unknown')
            numero_plainte = self._get_attr(plainte_data, 'numero_plainte', f'PL_{plainte_id}')
            
            # Nom du fichier PDF
            pdf_filename = f"plainte_{plainte_id}_rapport_complet.pdf"
            pdf_path = self.output_dir / pdf_filename
            
            logger.info(f"📄 Génération PDF pour plainte {plainte_id}...")
            
            # Créer le document
            doc = SimpleDocTemplate(
                str(pdf_path), 
                pagesize=A4,
                rightMargin=50,
                leftMargin=50,
                topMargin=50,
                bottomMargin=50
            )
            
            story = []
            
            # === EN-TÊTE ===
            story.append(Paragraph("RAPPORT DE PLAINTE", self.title_style))
            story.append(Paragraph(f"Référence: {self._safe_text(numero_plainte)}", self.styles['Heading3']))
            story.append(Spacer(1, 20))
            
            # === INFORMATIONS GÉNÉRALES ===
            story.append(Paragraph("📋 INFORMATIONS GÉNÉRALES", self.heading_style))
            
            info_data = [
                ['Numéro de plainte:', self._safe_text(numero_plainte)],
                ['Titre:', self._safe_text(self._get_attr(plainte_data, 'titre'))],
                ['Date de création:', self._format_date(self._get_attr(plainte_data, 'date_creation'))],
                ['Statut:', self._safe_text(self._get_enum_value(plainte_data, 'statut'))],
                ['Priorité:', self._safe_text(self._get_enum_value(plainte_data, 'priorite'))],
                ['Service:', self._safe_text(self._get_attr(service_data, 'nom') if service_data else 'N/A')],
                ['Mode de réception:', self._safe_text(self._get_attr(plainte_data, 'mode_reception'))],
            ]
            
            date_incident = self._get_attr(plainte_data, 'date_incident')
            if date_incident:
                info_data.append(['Date d\'incident:', self._format_date(date_incident, "%d/%m/%Y")])
            
            story.append(self._create_info_table(info_data))
            story.append(Spacer(1, 15))
            
            # === INFORMATIONS DU PLAIGNANT ===
            story.append(Paragraph("👤 INFORMATIONS DU PLAIGNANT", self.heading_style))
            
            nom = self._get_attr(plainte_data, 'nom_plaignant')
            prenom = self._get_attr(plainte_data, 'prenom_plaignant')
            
            plaignant_data = [
                ['Nom complet:', f"{self._safe_text(prenom)} {self._safe_text(nom)}".strip() or 'N/A'],
                ['Email:', self._safe_text(self._get_attr(plainte_data, 'email_plaignant'))],
                ['Téléphone:', self._safe_text(self._get_attr(plainte_data, 'telephone_plaignant'))],
            ]
            
            story.append(self._create_info_table(plaignant_data, colors.HexColor('#dbeafe')))
            story.append(Spacer(1, 15))
            
            # === DESCRIPTION DE LA PLAINTE ===
            story.append(Paragraph("📝 DESCRIPTION DE LA PLAINTE", self.heading_style))
            description = self._get_attr(plainte_data, 'description')
            if description:
                story.append(Paragraph(self._safe_text(description), self.normal_style))
            else:
                story.append(Paragraph("Aucune description fournie.", self.normal_style))
            story.append(Spacer(1, 15))
            
            # === CIRCONSTANCES (si disponible) ===
            circonstances = self._get_attr(plainte_data, 'circonstances')
            if circonstances:
                story.append(Paragraph("📋 CIRCONSTANCES", self.heading_style))
                story.append(Paragraph(self._safe_text(circonstances), self.normal_style))
                story.append(Spacer(1, 15))
            
            # === CONSÉQUENCES (si disponible) ===
            consequences = self._get_attr(plainte_data, 'consequences')
            if consequences:
                story.append(Paragraph("⚠️ CONSÉQUENCES", self.heading_style))
                story.append(Paragraph(self._safe_text(consequences), self.normal_style))
                story.append(Spacer(1, 15))
            
            # === DEMANDE DU PLAIGNANT (si disponible) ===
            demande = self._get_attr(plainte_data, 'demande_plaignant')
            if demande:
                story.append(Paragraph("🎯 DEMANDE DU PLAIGNANT", self.heading_style))
                story.append(Paragraph(self._safe_text(demande), self.normal_style))
                story.append(Spacer(1, 15))
            
            # === ANALYSE IA (si disponible) ===
            if analyse_ia_data:
                story.append(Paragraph("🤖 ANALYSE AUTOMATIQUE (IA)", self.heading_style))
                
                analyse_info = [
                    ['Sentiment détecté:', self._safe_text(self._get_attr(analyse_ia_data, 'sentiment'))],
                    ['Service suggéré:', self._safe_text(self._get_attr(analyse_ia_data, 'service_suggere'))],
                    ['Priorité IA:', self._safe_text(self._get_attr(analyse_ia_data, 'priorite_ia'))],
                    ['Statut analyse:', self._safe_text(self._get_attr(analyse_ia_data, 'statut_analyse'))],
                    ['Date analyse:', self._format_date(self._get_attr(analyse_ia_data, 'date_analyse'))],
                ]
                
                story.append(self._create_info_table(analyse_info, colors.HexColor('#fef3c7')))
                story.append(Spacer(1, 10))
                
                # Résumé IA
                resume_ia = self._get_attr(analyse_ia_data, 'resume_ia')
                if resume_ia:
                    story.append(Paragraph("📊 Résumé automatique:", self.styles['Heading4']))
                    story.append(Paragraph(self._safe_text(resume_ia), self.normal_style))
                    story.append(Spacer(1, 10))
                
                # Réponse suggérée
                reponse = self._get_attr(analyse_ia_data, 'reponse_suggeree')
                if reponse:
                    story.append(Paragraph("💬 Réponse suggérée:", self.styles['Heading4']))
                    story.append(Paragraph(self._safe_text(reponse), self.normal_style))
                    story.append(Spacer(1, 15))
            
            # === INFORMATIONS DE TRAITEMENT ===
            story.append(Paragraph("⚙️ INFORMATIONS DE TRAITEMENT", self.heading_style))
            
            traitement_data = [
                ['Assigné à:', self._safe_text(self._get_attr(user_data, 'nom') if user_data else 'Non assigné')],
                ['Dernière modification:', self._format_date(self._get_attr(plainte_data, 'date_modification'))],
            ]
            
            date_resolution = self._get_attr(plainte_data, 'date_resolution')
            if date_resolution:
                traitement_data.append(['Date de résolution:', self._format_date(date_resolution)])
            
            story.append(self._create_info_table(traitement_data, colors.HexColor('#dcfce7')))
            story.append(Spacer(1, 30))
            
            # === PIED DE PAGE ===
            story.append(Paragraph("─" * 80, self.normal_style))
            story.append(Paragraph(
                f"Document généré automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
                self.footer_style
            ))
            story.append(Paragraph(
                "Système HealthCare AI - Architecture ODYSSEE",
                self.footer_style
            ))
            
            # Construire le PDF
            doc.build(story)
            
            logger.info(f"✅ PDF généré avec succès: {pdf_path}")
            return str(pdf_path)
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la génération PDF: {e}")
            raise
    
    def _get_attr(self, obj: Any, attr: str, default: Any = None) -> Any:
        """Obtenir un attribut de manière sécurisée (dict ou objet)"""
        if obj is None:
            return default
        
        # Si c'est un dictionnaire
        if isinstance(obj, dict):
            return obj.get(attr, default)
        
        # Si c'est un objet
        return getattr(obj, attr, default)
    
    def _get_enum_value(self, obj: Any, attr: str, default: str = 'N/A') -> str:
        """Obtenir la valeur d'un enum de manière sécurisée"""
        value = self._get_attr(obj, attr)
        if value is None:
            return default
        
        # Si c'est un enum
        if hasattr(value, 'value'):
            return value.value
        
        return str(value)


def generate_pdf_for_plainte(plainte_id: int, db_session=None) -> str:
    """
    Fonction utilitaire pour générer un PDF pour une plainte
    
    Args:
        plainte_id: ID de la plainte
        db_session: Session SQLAlchemy (optionnel)
    
    Returns:
        str: Chemin du PDF généré
    """
    from sqlalchemy.orm import Session
    from healthcare_api_server.app.db.database import SessionLocal
    from shared.models import Plainte, Service, User, AnalyseIA
    
    # Utiliser la session fournie ou en créer une nouvelle
    close_session = False
    if db_session is None:
        db_session = SessionLocal()
        close_session = True
    
    try:
        # Récupérer les données
        plainte = db_session.query(Plainte).filter(Plainte.id == plainte_id).first()
        if not plainte:
            raise ValueError(f"Plainte {plainte_id} non trouvée")
        
        service = None
        if plainte.service_id:
            service = db_session.query(Service).filter(Service.id == plainte.service_id).first()
        
        user = None
        if plainte.assignee_a_id:
            user = db_session.query(User).filter(User.id == plainte.assignee_a_id).first()
        
        analyse_ia = db_session.query(AnalyseIA).filter(AnalyseIA.plainte_id == plainte_id).first()
        
        # Générer le PDF
        generator = PDFGenerator()
        return generator.generate_plainte_pdf(plainte, service, user, analyse_ia)
        
    finally:
        if close_session:
            db_session.close()
