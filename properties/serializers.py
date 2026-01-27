from rest_framework import serializers
from .models import Property, PropertyImage, PropertyInquiry, PropertyFavorite
from django.contrib.auth.models import User
from .models import *
from .models import GroupPaymentInvite


class PropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = [
            "id",
            "image",
            "caption",
            "is_primary",
            "created_at",
        ]


class PropertyOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class PropertyListSerializer(serializers.ModelSerializer):
    main_image = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            "id",
            "title",
            "price",
            "city",
            "location",
            "bedrooms",
            "bathrooms",
            "status",          # ✅ ADD THIS
            "area_sqft",
            "property_type",
            "is_verified",
            "main_image",
        ]

    def get_main_image(self, obj):
        img = obj.main_image
        return img.url if img else None

class PropertyDetailSerializer(serializers.ModelSerializer):
    """Serializer for property detail view (complete data)"""
    images = PropertyImageSerializer(many=True, read_only=True)
    owner = PropertyOwnerSerializer(read_only=True)
    price_per_sqft = serializers.ReadOnlyField()
    is_favorited = serializers.SerializerMethodField()
    inquiry_count = serializers.SerializerMethodField()

    # ✅ NEW FIELD
    user_request_status = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = '__all__'  # this will auto-include user_request_status

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return PropertyFavorite.objects.filter(
                property=obj, user=request.user
            ).exists()
        return False

    def get_inquiry_count(self, obj):
        return obj.inquiries.count()

    # ✅ NEW METHOD
    def get_user_request_status(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None

        pr = PropertyRequest.objects.filter(
            property=obj,
            user=request.user
        ).first()

        return pr.status if pr else None

class PropertyCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating properties"""
    images = PropertyImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Property
        exclude = ['owner', 'views_count', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # Set the owner to the current user
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)

class PropertyInquirySerializer(serializers.ModelSerializer):
    inquirer = PropertyOwnerSerializer(read_only=True)
    property_title = serializers.CharField(source='property.title', read_only=True)
    
    class Meta:
        model = PropertyInquiry
        fields = '__all__'
        read_only_fields = ['inquirer', 'is_responded']
    
    def create(self, validated_data):
        validated_data['inquirer'] = self.context['request'].user
        return super().create(validated_data)

class PropertyFavoriteSerializer(serializers.ModelSerializer):
    property = PropertyListSerializer(read_only=True)
    
    class Meta:
        model = PropertyFavorite
        fields = ['id', 'property', 'created_at']
        read_only_fields = ['user']


#new

from rest_framework import serializers
from .models import PropertyInterest, OwnerNotification, InvestmentPool, Transaction

class PropertyInterestCreateSerializer(serializers.Serializer):
    message = serializers.CharField(required=False, allow_blank=True)



class InvestmentPoolSerializer(serializers.ModelSerializer):
    per_investor_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = InvestmentPool
        fields = ["id", "property", "investors_required", "total_required", "status", "per_investor_amount", "created_at"]

class FakeTransactionCreateSerializer(serializers.Serializer):
    payer_name = serializers.CharField(max_length=120)
    payer_phone = serializers.CharField(max_length=20)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True)
    force_fail = serializers.BooleanField(required=False, default=False)



from rest_framework import serializers
from django.contrib.auth.models import User
from .models import PurchasePlan, PlanInvite, PropertyInterest, Contribution, Transaction, OwnerNotification


class CreateInterestSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=["single", "group"])
    group_size = serializers.IntegerField(required=False)
    invited_user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False
    )
    message = serializers.CharField(required=False, allow_blank=True)


class PurchasePlanSerializer(serializers.ModelSerializer):
    per_person_amount = serializers.SerializerMethodField()
    last_person_amount = serializers.SerializerMethodField()
    confirmed_total = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    confirmed_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PurchasePlan
        fields = "__all__"

    def get_per_person_amount(self, obj):
        return str(obj.per_person_amount())

    def get_last_person_amount(self, obj):
        return str(obj.last_person_amount())


class PropertyInterestSerializer(serializers.ModelSerializer):
    plan = PurchasePlanSerializer(read_only=True)
    requester_username = serializers.CharField(source="requester.username", read_only=True)
    property_title = serializers.CharField(source="property.title", read_only=True)

    class Meta:
        model = PropertyInterest
        fields = "__all__"


class PlanInviteSerializer(serializers.ModelSerializer):
    invited_username = serializers.CharField(source="invited_user.username", read_only=True)

    class Meta:
        model = PlanInvite
        fields = "__all__"


class FakePaymentSerializer(serializers.Serializer):
    payer_name = serializers.CharField(max_length=120)
    payer_phone = serializers.CharField(max_length=20)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True)
    force_fail = serializers.BooleanField(required=False, default=False)


class ContributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contribution
        fields = "__all__"


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"


class OwnerNotificationSerializer(serializers.ModelSerializer):
    property_title = serializers.CharField(source="property.title", read_only=True)

    class Meta:
        model = OwnerNotification
        fields = "__all__"




from django.contrib.auth.models import User
from rest_framework.serializers import ModelSerializer

class UserMiniSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]



class InitiateGroupPaymentSerializer(serializers.Serializer):
    pass

class PropertyMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = [
            "id",
            "title",
            "price",
            "status",
        ]



class GroupPaymentInviteSerializer(serializers.ModelSerializer):
    property = PropertyMiniSerializer(
        source="plan.property",
        read_only=True
    )

    class Meta:
        model = GroupPaymentInvite
        fields = [
            "id",
            "status",
            "created_at",
            "property",
        ]



from rest_framework import serializers
from .models import PropertyRequest

# serializers.py
from rest_framework import serializers
from .models import PropertyRequest

class PropertyRequestSerializer(serializers.ModelSerializer):
    property_title = serializers.CharField(
        source="property.title",
        read_only=True
    )

    class Meta:
        model = PropertyRequest
        fields = [
            "id",
            "property",
            "property_title",
            "full_name",
            "age",
            "occupation",
            "payment_mode",
            "group_size",
            "status",
            "created_at",
        ]
        read_only_fields = [
            "property",
            "status",
            "created_at",
        ]

    def validate(self, data):
        if data["payment_mode"] == "group":
            if not data.get("group_size") or data["group_size"] < 2:
                raise serializers.ValidationError(
                    "Group size must be at least 2"
                )
        else:
            data["group_size"] = None
        return data





# serializers.py
from rest_framework import serializers
from .models import PropertyImage

class PropertyImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = ["id", "image", "is_primary"]
