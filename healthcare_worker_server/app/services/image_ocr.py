"""
Service OCR pour l'extraction de texte depuis les images
Supporte les photos de documents, lettres manuscrites, captures d'écran
"""
import logging
import io
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

logger = logging.getLogger(__name__)


class ImageOCRService:
    """Service spécialisé pour l'OCR sur images de documents"""
    
    def __init__(self):
        """Initialise le service OCR"""
        self.supported_extensions = ['.png', '.jpg', '.jpeg', '.webp', '.tiff', '.bmp', '.gif']
        # Configuration Tesseract optimisée pour documents français
        self.tesseract_config = r'--oem 3 --psm 6 -l fra+eng'
        
    def extract_text_from_image(self, image_bytes: bytes, filename: str = "image.jpg") -> Dict[str, Any]:
        """
        Extrait le texte d'une image via OCR avec prétraitement
        
        Args:
            image_bytes: Contenu binaire de l'image
            filename: Nom du fichier pour déterminer le type
            
        Returns:
            Dict contenant le texte extrait, la confiance et les métadonnées
        """
        try:
            logger.info(f"🔍 Début OCR sur image: {filename} ({len(image_bytes)} octets)")
            
            # Charger l'image depuis les bytes
            image = Image.open(io.BytesIO(image_bytes))
            
            # Métadonnées de l'image
            metadata = {
                "file_type": "image",
                "original_size": image.size,
                "original_mode": image.mode,
                "format": image.format,
                "extraction_method": "Tesseract OCR"
            }
            
            # Prétraitement de l'image pour améliorer l'OCR
            processed_image, preprocessing_info = self._preprocess_image(image)
            metadata["preprocessing"] = preprocessing_info
            
            # Extraction du texte avec données de confiance
            ocr_result = self._perform_ocr_with_confidence(processed_image)
            
            text_content = ocr_result["text"]
            confidence_score = ocr_result["confidence"]
            
            if not text_content.strip():
                logger.warning("⚠️ Aucun texte détecté dans l'image")
                return {
                    "success": False,
                    "error": "Aucun texte détecté dans l'image. Vérifiez la qualité de l'image.",
                    "text": "",
                    "confidence": 0.0,
                    "metadata": metadata
                }
            
            # Évaluation de la qualité OCR
            quality_assessment = self._assess_ocr_quality(text_content, confidence_score)
            metadata["quality_assessment"] = quality_assessment
            
            logger.info(f"✅ OCR réussi: {len(text_content)} caractères, confiance: {confidence_score:.2f}")
            
            return {
                "success": True,
                "text": text_content.strip(),
                "confidence": confidence_score,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur OCR: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Erreur lors de l'OCR: {str(e)}",
                "text": "",
                "confidence": 0.0,
                "metadata": {"file_type": "image", "extraction_method": "Tesseract OCR"}
            }
    
    def extract_text_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Extrait le texte d'un fichier image via OCR
        
        Args:
            file_path: Chemin vers le fichier image
            
        Returns:
            Dict contenant le texte extrait et les métadonnées
        """
        path = Path(file_path)
        
        if not path.exists():
            return {
                "success": False,
                "error": "Fichier non trouvé",
                "text": "",
                "confidence": 0.0,
                "metadata": {}
            }
        
        if path.suffix.lower() not in self.supported_extensions:
            return {
                "success": False,
                "error": f"Type de fichier non supporté: {path.suffix}",
                "text": "",
                "confidence": 0.0,
                "metadata": {}
            }
        
        with open(file_path, 'rb') as f:
            image_bytes = f.read()
        
        return self.extract_text_from_image(image_bytes, path.name)
    
    def _preprocess_image(self, image: Image.Image, fast_mode: bool = True) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Prétraite l'image pour améliorer la qualité OCR
        
        🚀 OPTIMISÉ: Mode rapide par défaut (moins d'étapes de traitement)
        
        Args:
            image: Image PIL à traiter
            fast_mode: Si True, applique seulement les traitements essentiels (plus rapide)
            
        Returns:
            Tuple (image traitée, informations de prétraitement)
        """
        preprocessing_info = {
            "steps_applied": [],
            "original_size": image.size,
            "fast_mode": fast_mode
        }
        
        try:
            # 1. Conversion en RGB si nécessaire (toujours appliqué)
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
                preprocessing_info["steps_applied"].append("convert_to_rgb")
            
            # 2. Redimensionnement si l'image est trop petite (toujours appliqué)
            min_dimension = 800  # 🚀 Réduit de 1000 à 800 pour plus de rapidité
            width, height = image.size
            if width < min_dimension or height < min_dimension:
                scale_factor = max(min_dimension / width, min_dimension / height)
                new_size = (int(width * scale_factor), int(height * scale_factor))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                preprocessing_info["steps_applied"].append(f"resize_to_{new_size}")
            
            # 3. Conversion en niveaux de gris (toujours appliqué)
            if image.mode != 'L':
                image = image.convert('L')
                preprocessing_info["steps_applied"].append("convert_to_grayscale")
            
            # 🚀 Les étapes suivantes sont optionnelles en mode rapide
            if not fast_mode:
                # 4. Amélioration du contraste (mode complet seulement)
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.5)
                preprocessing_info["steps_applied"].append("enhance_contrast")
                
                # 5. Netteté (mode complet seulement)
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(1.2)
                preprocessing_info["steps_applied"].append("enhance_sharpness")
                
                # 6. Filtre de netteté (mode complet seulement)
                image = image.filter(ImageFilter.SHARPEN)
                preprocessing_info["steps_applied"].append("sharpen_filter")
            
            preprocessing_info["final_size"] = image.size
            preprocessing_info["success"] = True
            
        except Exception as e:
            logger.warning(f"⚠️ Prétraitement partiel: {e}")
            preprocessing_info["error"] = str(e)
            preprocessing_info["success"] = False
        
        return image, preprocessing_info
    
    def _perform_ocr_with_confidence(self, image: Image.Image) -> Dict[str, Any]:
        """
        Effectue l'OCR et calcule un score de confiance
        
        🚀 OPTIMISÉ: UN SEUL appel Tesseract (image_to_data) au lieu de deux.
        Le texte est reconstruit à partir des données détaillées.
        
        Args:
            image: Image PIL prétraitée
            
        Returns:
            Dict avec texte et score de confiance
        """
        try:
            # 🚀 UN SEUL appel Tesseract qui retourne tout (texte + confiance)
            data = pytesseract.image_to_data(image, config=self.tesseract_config, output_type=pytesseract.Output.DICT)
            
            # Reconstruire le texte à partir des données (évite le 2ème appel)
            words = []
            confidences = []
            current_line = -1
            
            for i, word in enumerate(data['text']):
                if word.strip():
                    # Ajouter un saut de ligne si on change de ligne
                    if data['line_num'][i] != current_line and current_line != -1:
                        words.append('\n')
                    current_line = data['line_num'][i]
                    words.append(word)
                    
                    # Collecter les confiances valides
                    conf = data['conf'][i]
                    if conf != '-1' and int(conf) > 0:
                        confidences.append(int(conf))
            
            text = ' '.join(words)
            
            # Calcul du score de confiance moyen
            if confidences:
                avg_confidence = sum(confidences) / len(confidences) / 100.0
            else:
                avg_confidence = 0.0
            
            return {
                "text": text,
                "confidence": avg_confidence,
                "word_count": len([w for w in words if w.strip() and w != '\n']),
                "details": {
                    "total_words_detected": len(confidences),
                    "min_confidence": min(confidences) / 100.0 if confidences else 0,
                    "max_confidence": max(confidences) / 100.0 if confidences else 0
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur OCR: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "word_count": 0,
                "details": {"error": str(e)}
            }
    
    def _assess_ocr_quality(self, text: str, confidence: float) -> Dict[str, Any]:
        """
        Évalue la qualité de l'extraction OCR
        
        Args:
            text: Texte extrait
            confidence: Score de confiance OCR
            
        Returns:
            Dict avec l'évaluation de qualité
        """
        assessment = {
            "confidence_score": confidence,
            "quality_level": "unknown",
            "recommendations": []
        }
        
        # Analyse du texte
        word_count = len(text.split())
        char_count = len(text)
        
        # Détection de problèmes courants
        has_many_special_chars = sum(1 for c in text if not c.isalnum() and c not in ' \n\t.,;:!?-\'\"()') > len(text) * 0.2
        has_very_short_words = sum(1 for w in text.split() if len(w) == 1 and w.lower() not in 'aàâäeéèêëiîïoôöuùûüy') > word_count * 0.3 if word_count > 0 else False
        
        # Évaluation du niveau de qualité
        if confidence >= 0.8 and not has_many_special_chars:
            assessment["quality_level"] = "excellent"
        elif confidence >= 0.6:
            assessment["quality_level"] = "bon"
        elif confidence >= 0.4:
            assessment["quality_level"] = "moyen"
            assessment["recommendations"].append("L'image pourrait être de meilleure qualité")
        else:
            assessment["quality_level"] = "faible"
            assessment["recommendations"].append("Qualité d'image insuffisante pour une extraction fiable")
        
        if has_many_special_chars:
            assessment["recommendations"].append("Beaucoup de caractères spéciaux détectés - vérifiez le texte")
        
        if has_very_short_words:
            assessment["recommendations"].append("Certains mots semblent mal reconnus")
        
        if word_count < 10:
            assessment["recommendations"].append("Peu de texte détecté - l'image contient-elle du texte lisible?")
        
        assessment["stats"] = {
            "word_count": word_count,
            "char_count": char_count
        }
        
        return assessment
    
    def is_image_supported(self, filename: str) -> bool:
        """Vérifie si le type d'image est supporté"""
        ext = Path(filename).suffix.lower()
        return ext in self.supported_extensions
    
    def get_supported_formats(self) -> list:
        """Retourne la liste des formats supportés"""
        return self.supported_extensions.copy()


# Instance singleton pour faciliter l'import
_ocr_service_instance: Optional[ImageOCRService] = None

def get_ocr_service() -> ImageOCRService:
    """Retourne l'instance singleton du service OCR"""
    global _ocr_service_instance
    if _ocr_service_instance is None:
        _ocr_service_instance = ImageOCRService()
    return _ocr_service_instance
