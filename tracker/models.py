from django.db import models

class School(models.Model):
    name = models.CharField(max_length=255)
    district = models.CharField(max_length=100)
    taluk = models.CharField(max_length=100)
    udise_code = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='users')
    role = models.CharField(max_length=20, default='headmaster')

class PointTemplate(models.Model):
    point_no = models.IntegerField(unique=True)
    group = models.CharField(max_length=1)
    title_kn = models.CharField(max_length=500)
    title_en = models.CharField(max_length=500)
    columns = models.JSONField()

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.point_no}. {self.title_en}"


class Entry(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='entries')
    point = models.ForeignKey(PointTemplate, on_delete=models.CASCADE, related_name='entries')
    month = models.CharField(max_length=20)  # no longer blank/null — required for every point now
    academic_year = models.CharField(max_length=10)  # e.g. "2026-27"
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('school', 'point', 'month', 'academic_year')

    def __str__(self):
        return f"{self.school.name} - Point {self.point.point_no} - {self.month} {self.academic_year}"

class MonthlySubmission(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='submissions')
    month = models.CharField(max_length=20)
    academic_year = models.CharField(max_length=10)
    submitted_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verifications')

    class Meta:
        unique_together = ('school', 'month', 'academic_year')

    def __str__(self):
        return f"{self.school.name} - {self.month} {self.academic_year} submitted"

class Notification(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=500)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.school.name}: {self.message}"
    