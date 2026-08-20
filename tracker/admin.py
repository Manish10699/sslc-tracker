
from django.contrib import admin
from .models import School, User, PointTemplate, Entry

admin.site.register(School)
admin.site.register(User)
admin.site.register(PointTemplate)
admin.site.register(Entry)