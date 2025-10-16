from django.db import models
import json


class ImageAnalysis(models.Model):
    image = models.ImageField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    analyzed_at = models.DateTimeField(null=True, blank=True)
    result_json = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Analysis {self.id} - {self.uploaded_at}"

    def get_detections(self):
        if self.result_json:
            return json.loads(self.result_json)
        return []

    def set_detections(self, detections):
        self.result_json = json.dumps(detections, ensure_ascii=False)


class Detection(models.Model):
    analysis = models.ForeignKey(ImageAnalysis, on_delete=models.CASCADE, related_name='detections')
    class_name = models.CharField(max_length=100)
    confidence = models.FloatField()
    bbox_x1 = models.FloatField()
    bbox_y1 = models.FloatField()
    bbox_x2 = models.FloatField()
    bbox_y2 = models.FloatField()
    bbox_width = models.FloatField()
    bbox_height = models.FloatField()
    ocr_text = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.class_name} ({self.confidence:.2f})"