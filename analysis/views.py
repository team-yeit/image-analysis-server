from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from django.utils import timezone
from .models import ImageAnalysis, Detection
from .serializers import ImageAnalysisSerializer, ImageUploadSerializer
import os
import cv2
import json
import uuid
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # GUI 없이 사용하기 위한 백엔드 설정
import matplotlib.pyplot as plt
from ultralytics import YOLO
import easyocr


class ImageAnalysisViewSet(viewsets.ModelViewSet):
    queryset = ImageAnalysis.objects.all()
    serializer_class = ImageAnalysisSerializer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = None
        self.reader = None

    def get_yolo_model(self):
        if self.model is None:
            model_path = settings.MODEL_PATH
            if os.path.exists(model_path):
                self.model = YOLO(model_path)
            else:
                raise FileNotFoundError(f"Model not found at {model_path}")
        return self.model

    def get_ocr_reader(self):
        if self.reader is None:
            self.reader = easyocr.Reader(['en', 'ko'])
        return self.reader

    @action(detail=False, methods=['post'])
    def analyze(self, request):
        serializer = ImageUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        image_file = serializer.validated_data['image']

        # 이미지 분석 객체 생성
        analysis = ImageAnalysis.objects.create(image=image_file)


        try:
            # 이미지 경로
            image_path = analysis.image.path

            # YOLO 모델 로드
            model = self.get_yolo_model()

            # 이미지 분석
            results = model(image_path)

            # 이미지 읽기 (OCR용)
            img = cv2.imread(image_path)

            # OCR 리더
            reader = self.get_ocr_reader()

            detections_data = []

            for result in results:
                if len(result.boxes) > 0:
                    for i, box in enumerate(result.boxes):
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        conf = float(box.conf[0])
                        cls = int(box.cls[0])
                        class_name = result.names[cls]

                        # ROI 추출
                        roi = img[int(y1):int(y2), int(x1):int(x2)]

                        # OCR 수행
                        ocr_text = ""
                        try:
                            if roi.size > 0:
                                results_ocr = reader.readtext(roi)
                                if results_ocr:
                                    ocr_text = ' '.join([text[1] for text in results_ocr])
                        except:
                            ocr_text = ""

                        # Detection 객체 생성
                        Detection.objects.create(
                            analysis=analysis,
                            class_name=class_name,
                            confidence=round(conf, 3),
                            bbox_x1=round(x1, 1),
                            bbox_y1=round(y1, 1),
                            bbox_x2=round(x2, 1),
                            bbox_y2=round(y2, 1),
                            bbox_width=round(x2 - x1, 1),
                            bbox_height=round(y2 - y1, 1),
                            ocr_text=ocr_text
                        )

                        detections_data.append({
                            "id": i + 1,
                            "class": class_name,
                            "confidence": round(conf, 3),
                            "bbox": {
                                "x1": round(x1, 1),
                                "y1": round(y1, 1),
                                "x2": round(x2, 1),
                                "y2": round(y2, 1),
                                "width": round(x2 - x1, 1),
                                "height": round(y2 - y1, 1)
                            },
                            "ocr_text": ocr_text
                        })

            # results 폴더에 결과 저장 (현재 시각 + UUID)
            results_base_dir = settings.RESULTS_ROOT
            os.makedirs(results_base_dir, exist_ok=True)

            # 폴더명: YYYYMMDD_HHMMSS_uuid
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            folder_name = f'{timestamp}_{unique_id}'
            result_folder = os.path.join(results_base_dir, folder_name)
            os.makedirs(result_folder, exist_ok=True)

            # JSON 파일 저장
            detection_json = {
                "analysis_id": analysis.id,
                "image": str(analysis.image),
                "uploaded_at": analysis.uploaded_at.isoformat(),
                "analyzed_at": timezone.now().isoformat(),
                "detections": detections_data
            }

            json_path = os.path.join(result_folder, 'detections.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(detection_json, f, indent=2, ensure_ascii=False)

            # 이미지에 바운딩 박스 그리기
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            for det in detections_data:
                bbox = det['bbox']
                x1, y1 = int(bbox['x1']), int(bbox['y1'])
                x2, y2 = int(bbox['x2']), int(bbox['y2'])

                cv2.rectangle(img_rgb, (x1, y1), (x2, y2), (0, 255, 0), 2)

                label = f"{det['class']}: {det['confidence']:.2f}"
                if det['ocr_text']:
                    label += f" [{det['ocr_text']}]"

                (text_width, text_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(img_rgb, (x1, y1 - text_height - 10), (x1 + text_width, y1), (0, 255, 0), -1)
                cv2.putText(img_rgb, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

            # 시각화 이미지 저장 (matplotlib)
            plt.figure(figsize=(12, 8))
            plt.imshow(img_rgb)
            plt.axis('off')
            plt.title(f'GUI Detection + OCR Results')
            plt.tight_layout()

            image_save_path = os.path.join(result_folder, 'detection_result.jpg')
            plt.savefig(image_save_path, bbox_inches='tight', dpi=150)
            plt.close()

            # 원본 이미지 복사 저장
            original_image_path = os.path.join(result_folder, 'original_image.jpg')
            cv2.imwrite(original_image_path, img)

            # 분석 완료 시간 업데이트
            analysis.analyzed_at = timezone.now()
            analysis.save()

            # 결과 반환
            serializer = ImageAnalysisSerializer(analysis, context={'request': request})
            return Response({
                'status': 'success',
                'message': f'{len(detections_data)} detections found',
                'data': serializer.data,
                'result_folder': result_folder
            }, status=status.HTTP_200_OK)

        except Exception as e:
            analysis.delete()
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def result(self, request, pk=None):
        analysis = self.get_object()
        serializer = ImageAnalysisSerializer(analysis, context={'request': request})
        return Response(serializer.data)