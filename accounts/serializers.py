from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework.validators import UniqueValidator

class UserRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )

    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm', 'first_name', 'last_name')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include username and password')

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'date_joined')
        read_only_fields = ('id', 'username', 'date_joined')

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs






from rest_framework import serializers
from .models import UserVerification

class UserVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserVerification
        fields = "__all__"
        read_only_fields = ["user", "status", "created_at", "updated_at"]





from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, UserVerification

class ProfileSerializer(serializers.ModelSerializer):
    profile_pic = serializers.ImageField(required=False)
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    date_joined = serializers.DateTimeField(source="user.date_joined", read_only=True)

    # 🔗 KYC FIELDS
    kyc_status = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    account_id = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = (
            "profile_pic",
            "location",
            "email",
            "first_name",
            "last_name",
            "date_joined",
            "kyc_status",
            "phone_number",
            "account_id",
        )

    def get_kyc_status(self, obj):
        if hasattr(obj.user, "verification"):
            return obj.user.verification.status
        return "not_submitted"

    def get_phone_number(self, obj):
        if hasattr(obj.user, "verification"):
            return obj.user.verification.phone_number
        return None

    def get_account_id(self, obj):
        if hasattr(obj.user, "verification"):
            return f"KYC-{obj.user.verification.id}"
        return None

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})

        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        instance.user.save()

        return super().update(instance, validated_data)