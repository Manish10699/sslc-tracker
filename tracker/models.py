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
    month = models.CharField(max_length=20, blank=True, null=True)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.school.name} - Point {self.point.point_no} - {self.month or 'N/A'}"