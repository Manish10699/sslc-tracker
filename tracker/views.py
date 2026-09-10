from datetime import date

from django.utils import timezone
import os

from django.shortcuts import render
from rest_framework import viewsets, permissions
from .models import MonthlySubmission, Notification, PointTemplate, Entry, School
from .serializers import NotificationSerializer, PointTemplateSerializer, EntrySerializer, RegisterSerializer
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
from .utils import send_report_email
from rest_framework.permissions import BasePermission
from .utils import get_current_academic_year



class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'

class PointTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PointTemplate.objects.all()
    serializer_class = PointTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        point = self.get_object()
        school = request.user.school
        month = request.query_params.get('month')
        entries = Entry.objects.filter(point=point, school=school)
        if month:
            entries = entries.filter(month=month)
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
                elif col['type'] == 'month_select':
                    cell.value = entry.month
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
        month = self.request.query_params.get('month')
        if month:
            queryset = queryset.filter(month=month)
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
            'role': user.role,
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


class SubmitMonthView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from .utils import get_current_academic_year
        school = request.user.school
        month = request.data.get('month')
        academic_year = get_current_academic_year()

        if not month:
            return Response({'error': 'month is required'}, status=400)

        # Re-check completion server-side — never trust the frontend's "all_complete" alone
        all_points = PointTemplate.objects.all()
        completed_ids = set(Entry.objects.filter(
            school=school, month=month, academic_year=academic_year
        ).values_list('point_id', flat=True))

        if set(p.id for p in all_points) != completed_ids:
            return Response({'error': 'Not all points are complete for this month.'}, status=400)

        if MonthlySubmission.objects.filter(school=school, month=month, academic_year=academic_year).exists():
            return Response({'error': 'This month has already been submitted.'}, status=400)

        # Build the combined workbook
        wb = Workbook()
        wb.remove(wb.active)  # remove the default blank sheet

        thin_border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        )
        center_wrap = Alignment(horizontal='center', vertical='center', wrap_text=True)

        for point in all_points.order_by('point_no'):
            ws = wb.create_sheet(title=f"Point {point.point_no}")
            num_cols = len(point.columns)
            entry = Entry.objects.get(school=school, point=point, month=month, academic_year=academic_year)

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
            for cell in ws[4]:
                cell.font = Font(bold=True)
                cell.alignment = center_wrap
                cell.border = thin_border
                cell.fill = PatternFill(start_color='D9D9D9', end_color='D9D9D9', fill_type='solid')

            row_num = 5
            ws.append(['' for _ in point.columns])
            for col_idx, col in enumerate(point.columns, start=1):
                cell = ws.cell(row=row_num, column=col_idx)
                cell.border = thin_border
                cell.alignment = Alignment(vertical='center', wrap_text=True)
                if col['type'] == 'photo':
                    photo_url = entry.data.get(col['id'])
                    if photo_url:
                        try:
                            resp = requests.get(photo_url, timeout=10)
                            img = XLImage(BytesIO(resp.content))
                            img.width, img.height = 80, 80
                            img.anchor = f"{get_column_letter(col_idx)}{row_num}"
                            ws.add_image(img)
                            ws.row_dimensions[row_num].height = 65
                        except Exception:
                            cell.value = 'Photo unavailable'

                elif col['type'] == 'month_select':
                    cell.value = entry.month
                else:
                    cell.value = entry.data.get(col['id'], '')

            for col_idx in range(1, num_cols + 1):
                ws.column_dimensions[get_column_letter(col_idx)].width = 25

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        # Lock the month
        MonthlySubmission.objects.create(school=school, month=month, academic_year=academic_year)

        # (email sending goes here next — placeholder for now)
        excel_data = buffer.getvalue()

        send_report_email(
            to_email=os.getenv("OFFICER_EMAIL"),
            file_data=excel_data,
            filename=f"{school.name}_{month}_{academic_year}.xlsx",
            school_name=school.name,
            month=month,
            academic_year=academic_year,
        )
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{school.name}_{month}_{academic_year}.xlsx"'
        return response

class AdminSchoolsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        from .utils import get_current_academic_year
        month = request.query_params.get('month')
        academic_year = get_current_academic_year()
        total_points = PointTemplate.objects.count()

        schools_data = []
        submitted_count = 0

        for school in School.objects.all():
            submission = MonthlySubmission.objects.filter(
                school=school, month=month, academic_year=academic_year
            ).first()
            completed = Entry.objects.filter(
                school=school, month=month, academic_year=academic_year
            ).count()

            is_submitted = submission is not None
            if is_submitted:
                submitted_count += 1

            schools_data.append({
                'id': school.id,
                'name': school.name,
                'district': school.district,
                'taluk': school.taluk,
                'completed_points': completed,
                'total_points': total_points,
                'is_submitted': is_submitted,
                'submitted_at': submission.submitted_at if submission else None,
                'is_verified': submission.verified_at is not None if submission else False,
            })

        total_schools = len(schools_data)
        return Response({
            'month': month,
            'academic_year': academic_year,
            'total_schools': total_schools,
            'submitted_count': submitted_count,
            'pending_count': total_schools - submitted_count,
            'schools': schools_data,
        })

class VerifySubmissionView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, school_id):
        month = request.data.get('month')
        from .utils import get_current_academic_year
        academic_year = get_current_academic_year()

        submission = MonthlySubmission.objects.filter(
            school_id=school_id, month=month, academic_year=academic_year
        ).first()

        if not submission:
            return Response({'error': 'This month has not been submitted yet.'}, status=400)

        submission.verified_at = timezone.now()
        submission.verified_by = request.user
        submission.save()

        Notification.objects.create(
            school_id=school_id,
            message=f"Your {month} {academic_year} report has been verified by the officer."
        )

        return Response({'message': 'Verified successfully.'})


class AdminSchoolDetailView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, school_id):
        month = request.query_params.get('month')
        from .utils import get_current_academic_year
        academic_year = get_current_academic_year()
        school = School.objects.get(id=school_id)

        entries = Entry.objects.filter(school=school, month=month, academic_year=academic_year)
        entries_by_point = {e.point_id: EntrySerializer(e).data for e in entries}

        points_data = []
        for point in PointTemplate.objects.all().order_by('point_no'):
            points_data.append({
                'id': point.id,
                'point_no': point.point_no,
                'title_kn': point.title_kn,
                'title_en': point.title_en,
                'columns': point.columns,
                'entry': entries_by_point.get(point.id),
            })

        submission = MonthlySubmission.objects.filter(
            school=school, month=month, academic_year=academic_year
        ).first()

        return Response({
            'school': {'name': school.name, 'district': school.district, 'taluk': school.taluk},
            'points': points_data,
            'is_submitted': submission is not None,
            'is_verified': submission.verified_at is not None if submission else False,
        })

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'patch']  # no create/delete from the client side

    def get_queryset(self):
        return Notification.objects.filter(school=self.request.user.school)


class AdminSchoolExportView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, school_id):
        from .utils import get_current_academic_year
        month = request.query_params.get('month')
        academic_year = get_current_academic_year()
        school = School.objects.get(id=school_id)
        all_points = PointTemplate.objects.all().order_by('point_no')

        wb = Workbook()
        wb.remove(wb.active)
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                              top=Side(style='thin'), bottom=Side(style='thin'))
        center_wrap = Alignment(horizontal='center', vertical='center', wrap_text=True)

        for point in all_points:
            ws = wb.create_sheet(title=f"Point {point.point_no}")
            num_cols = len(point.columns)
            entry = Entry.objects.filter(school=school, point=point, month=month, academic_year=academic_year).first()

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
            for cell in ws[4]:
                cell.font = Font(bold=True)
                cell.alignment = center_wrap
                cell.border = thin_border
                cell.fill = PatternFill(start_color='D9D9D9', end_color='D9D9D9', fill_type='solid')

            row_num = 5
            ws.append(['' for _ in point.columns])
            if entry:
                for col_idx, col in enumerate(point.columns, start=1):
                    cell = ws.cell(row=row_num, column=col_idx)
                    cell.border = thin_border
                    cell.alignment = Alignment(vertical='center', wrap_text=True)
                    if col['type'] == 'photo':
                        photo_url = entry.data.get(col['id'])
                        if photo_url:
                            try:
                                resp = requests.get(photo_url, timeout=10)
                                img = XLImage(BytesIO(resp.content))
                                img.width, img.height = 80, 80
                                img.anchor = f"{get_column_letter(col_idx)}{row_num}"
                                ws.add_image(img)
                                ws.row_dimensions[row_num].height = 65
                            except Exception:
                                cell.value = 'Photo unavailable'
                    elif col['type'] == 'month_select':
                        cell.value = entry.month
                    else:
                        cell.value = entry.data.get(col['id'], '')

            for col_idx in range(1, num_cols + 1):
                ws.column_dimensions[get_column_letter(col_idx)].width = 25

        buffer = BytesIO()
        wb.save(buffer)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{school.name}_{month}_{academic_year}.xlsx"'
        return response


class RunReminderCheckView(APIView):
    permission_classes = [AllowAny]  # protected by a secret key instead of login

    def post(self, request):
        secret = request.headers.get('X-Cron-Secret')
        if secret != os.environ.get('CRON_SECRET'):
            return Response({'error': 'Unauthorized'}, status=401)


        today = date.today()
        # if today.day < 25:
        #     return Response({'message': 'Not yet the 25th, skipping.'})

        month = today.strftime('%B')
        academic_year = get_current_academic_year()
        created = 0

        for school in School.objects.all():
            already_submitted = MonthlySubmission.objects.filter(
                school=school, month=month, academic_year=academic_year
            ).exists()
            already_reminded = Notification.objects.filter(
                school=school, message__icontains=f"reminder for {month}"
            ).exists()

            if not already_submitted and not already_reminded:
                Notification.objects.create(
                    school=school,
                    message=f"Reminder for {month} {academic_year}: please complete and submit your report."
                )
                created += 1

        return Response({'message': f'Created {created} reminder(s).'})