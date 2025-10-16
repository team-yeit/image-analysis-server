from rest_framework import serializers
from .models import ImageAnalysis, Detection


class DetectionSerializer(serializers.ModelSerializer):
    bbox = serializers.SerializerMethodField()

    class Meta:
        model = Detection
        fields = ['id', 'class_name', 'confidence', 'bbox', 'ocr_text']

    def get_bbox(self, obj):
        return {
            'x1': round(obj.bbox_x1, 1),
            'y1': round(obj.bbox_y1, 1),
            'x2': round(obj.bbox_x2, 1),
            'y2': round(obj.bbox_y2, 1),
            'width': round(obj.bbox_width, 1),
            'height': round(obj.bbox_height, 1)
        }


class ImageAnalysisSerializer(serializers.ModelSerializer):
    detections = DetectionSerializer(many=True, read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ImageAnalysis
        fields = ['id', 'image', 'image_url', 'uploaded_at', 'analyzed_at', 'detections']

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
        return None


class ImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()