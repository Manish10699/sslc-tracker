from rest_framework import serializers
from .models import *
from .models import MonthlySubmission
from .utils import get_current_academic_year

class PointTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointTemplate
        fields = ['id', 'point_no', 'group', 'title_kn', 'title_en', 'columns']



class EntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Entry
        fields = ['id', 'point', 'month', 'academic_year', 'data', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'academic_year']

    def validate(self, attrs):
        request = self.context['request']
        school = request.user.school

        # Figure out the final month/academic_year — for updates, fall back to the existing values
        month = attrs.get('month', getattr(self.instance, 'month', None))
        academic_year = get_current_academic_year()
        point = attrs.get('point', getattr(self.instance, 'point', None))

        # Rule 1: block edits/creates if this month is already submitted/locked
        if MonthlySubmission.objects.filter(school=school, month=month, academic_year=academic_year).exists():
            raise serializers.ValidationError(
                f"{month} {academic_year} has already been submitted and is locked."
            )

        # Rule 2: block a duplicate month for this point (only relevant when creating, not editing the same row)
        if self.instance is None:  # this is a create, not an update
            if Entry.objects.filter(school=school, point=point, month=month, academic_year=academic_year).exists():
                raise serializers.ValidationError(
                    f"An entry for {month} {academic_year} already exists for this point."
                )

        return attrs

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


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'is_read', 'created_at']
        read_only_fields = ['id', 'message', 'created_at']