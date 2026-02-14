from rest_framework import serializers
from .models import Property, PropertyImage, PropertyInquiry, PropertyFavorite
from django.contrib.auth.models import User
from .models import *
from .models import GroupPaymentInvite


class PropertyImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = PropertyImage
        fields = [
            "id",
            "image",
            "caption",
            "is_primary",
            "created_at",
        ]

    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image:
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
class PropertyVideoSerializer(serializers.ModelSerializer):
    video = serializers.SerializerMethodField()

    class Meta:
        model = PropertyVideo
        fields = ["id", "video", "created_at"]

    def get_video(self, obj):
        request = self.context.get("request")
        if obj.video:
            return request.build_absolute_uri(obj.video.url) if request else obj.video.url
        return None


class PropertyOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class PropertyListSerializer(serializers.ModelSerializer):
    main_image = serializers.SerializerMethodField()
    other_images = serializers.SerializerMethodField()
    video = serializers.SerializerMethodField()

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
            "status",
            "area_sqft",
            "property_type",
            "is_verified",
            "main_image",
            "other_images",
            "video",   # 👈 IMPORTANT
        ]

    def get_main_image(self, obj):
        request = self.context.get("request")
        image = obj.images.filter(is_primary=True).first() or obj.images.first()

        if image and image.image:
            return request.build_absolute_uri(image.image.url) if request else image.image.url
        return None

    def get_other_images(self, obj):
        request = self.context.get("request")
        images = obj.images.filter(is_primary=False)

        urls = []
        for img in images:
            urls.append(request.build_absolute_uri(img.image.url) if request else img.image.url)

        return urls

    def get_video(self, obj):
        request = self.context.get("request")
        vid = obj.videos.first()

        if not vid:
            return None

        return request.build_absolute_uri(vid.video.url) if request else vid.video.url

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # 🔥 remove video if None
        if not data.get("video"):
            data.pop("video", None)

        return data

class PropertyDetailSerializer(serializers.ModelSerializer):
    images = PropertyImageSerializer(many=True, read_only=True)
    video = serializers.SerializerMethodField()
    owner = PropertyOwnerSerializer(read_only=True)
    price_per_sqft = serializers.ReadOnlyField()
    is_favorited = serializers.SerializerMethodField()
    inquiry_count = serializers.SerializerMethodField()
    user_request_status = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = "__all__"

    def get_video(self, obj):
        request = self.context.get("request")
        vid = obj.videos.first()

        if not vid:
            return None

        return request.build_absolute_uri(vid.video.url) if request else vid.video.url

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if not data.get("video"):
            data.pop("video", None)

        return data

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return PropertyFavorite.objects.filter(
                property=obj, user=request.user
            ).exists()
        return False

    def get_inquiry_count(self, obj):
        return obj.inquiries.count()

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
    images = PropertyImageSerializer(many=True, read_only=True)

    class Meta:
        model = Property
        exclude = ['owner', 'views_count', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context["request"]
        video_file = request.FILES.get("video")

        property_obj = super().create(validated_data)

        if video_file:
            PropertyVideo.objects.create(
                property=property_obj,
                video=video_file
            )

        return property_obj



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
