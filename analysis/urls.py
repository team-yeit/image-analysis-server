from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ImageAnalysisViewSet

router = DefaultRouter()
router.register(r'images', ImageAnalysisViewSet, basename='image-analysis')

urlpatterns = [
    path('', include(router.urls)),
]