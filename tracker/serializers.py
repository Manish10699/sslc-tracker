from rest_framework import serializers
from .models import *

class PointTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointTemplate
        fields = ['id', 'point_no', 'group', 'title_kn', 'title_en', 'columns']


class EntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Entry
        fields = ['id', 'point', 'month', 'data', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class RegisterSerializer(serializers.Serializer):
    school_name = serializers.CharField(max_length=255)
    district = serializers.CharField(max_length=100)
    taluk = serializers.CharField(max_length=100)
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=6)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def create(self, validated_data):
        school = School.objects.create(
            name=validated_data['school_name'],
            district=validated_data['district'],
            taluk=validated_data['taluk'],
        )
        user = User(
            username=validated_data['username'],
            first_name=validated_data.get('first_name', ''),
            school=school,
            is_active=False,   # the key line — blocked from logging in until approved
        )
        user.set_password(validated_data['password'])
        user.save()
        return user