from django.shortcuts import render
from rest_framework import viewsets, permissions
from .models import MonthlySubmission, PointTemplate, Entry
from .serializers import PointTemplateSerializer, EntrySerializer, RegisterSerializer
import cloudinary.uploader
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from openpyxl import Workbook
from .models import Entry
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from rest_framework.views import APIView
import requests
from io import BytesIO
from openpyxl.drawing.image import Image as XLImage
from rest_framework.permissions import AllowAny
from .utils import get_current_academic_year


class PointTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PointTemplate.objects.all()
    serializer_class = PointTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        point = self.get_object()
        school = request.user.school
        entries = Entry.objects.filter(point=point, school=school)
        num_cols = len(point.columns)

        wb = Workbook()
        ws = wb.active
        ws.title = f"Point {point.point_no}"

        thin_border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        )
        center_wrap = Alignment(horizontal='center', vertical='center', wrap_text=True)

        ws.append([f"{point.point_no}) {point.title_kn}"])
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
        ws.cell(row=1, column=1).font = Font(bold=True, size=14)
        ws.cell(row=1, column=1).alignment = center_wrap

        ws.append([f"ಶಾಲೆ: {school.name}", f"ಜಿಲ್ಲೆ: {school.district}", f"ತಾಲೂಕು: {school.taluk}"])
        for cell in ws[2]:
            cell.font = Font(bold=True)

        ws.append([])

        headers = [col['label_kn'] for col in point.columns]
        ws.append(headers)
        header_row_num = 4
        for cell in ws[header_row_num]:
            cell.font = Font(bold=True)
            cell.alignment = center_wrap
            cell.border = thin_border
            cell.fill = PatternFill(start_color='D9D9D9', end_color='D9D9D9', fill_type='solid')

        row_num = header_row_num
        for entry in entries:
            row_num += 1
            ws.append(['' for _ in point.columns])  # placeholder row, filled cell-by-cell below

            for col_idx, col in enumerate(point.columns, start=1):
                cell = ws.cell(row=row_num, column=col_idx)
                cell.border = thin_border
                cell.alignment = Alignment(vertical='center', wrap_text=True)

                if col['type'] == 'photo':
                    photo_url = entry.data.get(col['id'])
                    if photo_url:
                        try:
                            response = requests.get(photo_url, timeout=10)
                            img = XLImage(BytesIO(response.content))
                            img.width = 80
                            img.height = 80
                            col_letter = get_column_letter(col_idx)
                            img.anchor = f"{col_letter}{row_num}"
                            ws.add_image(img)
                            ws.row_dimensions[row_num].height = 65
                        except Exception:
                            cell.value = 'Photo unavailable'
                else:
                    cell.value = entry.data.get(col['id'], '')

        for col_idx in range(1, num_cols + 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = 25

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="point_{point.point_no}.xlsx"'
        wb.save(response)
        return response


class EntryViewSet(viewsets.ModelViewSet):
    serializer_class = EntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Entry.objects.filter(school=self.request.user.school)
        point_id = self.request.query_params.get('point')
        if point_id:
            queryset = queryset.filter(point_id=point_id)
        return queryset

    def perform_create(self, serializer):
        # Force the school to be the logged-in user's school - never trust the frontend for this
        serializer.save(school=self.request.user.school,academic_year = get_current_academic_year())




@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_photo(request):
    file = request.FILES.get('photo')
    if not file:
        return Response({'error': 'No photo provided'}, status=400)
    
    result = cloudinary.uploader.upload(file)
    return Response({'url': result['secure_url']})




class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'username': user.username,
            'first_name': user.first_name,
            'school': {
                'name': user.school.name if user.school else None,
                'district': user.school.district if user.school else None,
            }
        })



class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'message': 'Registration submitted. Please wait for approval before logging in.'},
            status=201
        )


class MonthStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .utils import get_current_academic_year
        school = request.user.school
        month = request.query_params.get('month')
        academic_year = get_current_academic_year()

        all_points = PointTemplate.objects.values_list('id', flat=True)
        completed_point_ids = Entry.objects.filter(
            school=school, month=month, academic_year=academic_year
        ).values_list('point_id', flat=True)

        is_locked = MonthlySubmission.objects.filter(
            school=school, month=month, academic_year=academic_year
        ).exists()

        return Response({
            'month': month,
            'academic_year': academic_year,
            'total_points': len(all_points),
            'completed_point_ids': list(completed_point_ids),
            'all_complete': set(all_points) == set(completed_point_ids),
            'is_locked': is_locked,
        })