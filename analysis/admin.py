from django.contrib import admin
from .models import ImageAnalysis, Detection


@admin.register(ImageAnalysis)
class ImageAnalysisAdmin(admin.ModelAdmin):
    list_display = ['id', 'image', 'uploaded_at', 'analyzed_at']
    list_filter = ['uploaded_at', 'analyzed_at']
    search_fields = ['id']


@admin.register(Detection)
class DetectionAdmin(admin.ModelAdmin):
    list_display = ['id', 'analysis', 'class_name', 'confidence', 'ocr_text', 'created_at']
    list_filter = ['class_name', 'created_at']
    search_fields = ['class_name', 'ocr_text']
    raw_id_fields = ['analysis']