from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
import uuid
import os
import builtins


def property_image_upload_path(instance, filename):
    """Generate upload path for property images"""
    ext = filename.split('.')[-1]
    filename = f'{uuid.uuid4()}.{ext}'
    return os.path.join('properties', str(instance.property.id), filename)

class Property(models.Model):
    PROPERTY_TYPES = [
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('industrial', 'Industrial'),
        ('land', 'Land'),
        ('apartment', 'Apartment'),
        ('villa', 'Villa'),
        ('office', 'Office'),
        ('shop', 'Shop'),
        ('warehouse', 'Warehouse'),
    ]
    
    PROPERTY_STATUS = [
        ('draft', 'Draft'),          # 🆕
        ('available', 'Available'),
        ('sold', 'Sold'),
        ('rented', 'Rented'),
        ('pending', 'Pending'),
        ('withdrawn', 'Withdrawn'),
    ]
    
    LISTING_TYPE = [
        ('sale', 'For Sale'),
        ('rent', 'For Rent'),
        ('both', 'Sale & Rent'),
    ]

    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES)
    listing_type = models.CharField(max_length=10, choices=LISTING_TYPE, default='sale')
    status = models.CharField(max_length=20, choices=PROPERTY_STATUS, default='draft')
    
    # Location
    location = models.CharField(max_length=300)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    # Property Details
    price = models.DecimalField(max_digits=15, decimal_places=2)
    rent_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    area_sqft = models.IntegerField(validators=[MinValueValidator(1)])
    bedrooms = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(20)])
    bathrooms = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(20)])
    floors = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    parking_spaces = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Features
    furnished = models.BooleanField(default=False)
    ac_available = models.BooleanField(default=False)
    balcony = models.BooleanField(default=False)
    gym = models.BooleanField(default=False)
    swimming_pool = models.BooleanField(default=False)
    garden = models.BooleanField(default=False)
    security = models.BooleanField(default=False)
    lift_available = models.BooleanField(default=False)
    power_backup = models.BooleanField(default=False)
    
    # Ownership & Contact
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='properties')
    contact_name = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=15)
    contact_email = models.EmailField()
    
    # Metadata
    is_featured = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    views_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # in Property model
    investors_required = models.PositiveIntegerField(default=2)  # can be 2-50
    investment_enabled = models.BooleanField(default=True)
    investors_min = models.PositiveIntegerField(default=2) 
    investors_max = models.PositiveIntegerField(default=50)
    


    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Properties'
    
    def __str__(self):
        return f"{self.title} - {self.location}"
    
    @builtins.property
    def main_image(self):
     primary = self.images.filter(is_primary=True).first()
     if primary:
        return primary.image
     fallback = self.images.first()
     return fallback.image if fallback else None


    
    @builtins.property
    def price_per_sqft(self):
        """Calculate price per square foot"""
        return round(float(self.price) / self.area_sqft, 2)

class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField("image")
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_primary', 'created_at']
    
    def __str__(self):
        return f"Image for {self.property.title}"
    

class PropertyVideo(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="videos"
    )

    video = models.FileField(upload_to="properties/videos/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Video - {self.property.title}"

class PropertyInquiry(models.Model):
    INQUIRY_TYPES = [
        ('buying', 'Interested in Buying'),
        ('renting', 'Interested in Renting'),
        ('viewing', 'Schedule Viewing'),
        ('info', 'More Information'),
    ]
    
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='inquiries')
    inquirer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inquiries')
    inquiry_type = models.CharField(max_length=20, choices=INQUIRY_TYPES)
    message = models.TextField()
    contact_phone = models.CharField(max_length=15, blank=True)
    preferred_contact_time = models.CharField(max_length=100, blank=True)
    is_responded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Property Inquiries'
    
    def __str__(self):
        return f"Inquiry for {self.property.title} by {self.inquirer.username}"

class PropertyFavorite(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='favorites')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_properties')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('property', 'user')
    
    def __str__(self):
        return f"{self.user.username} - {self.property.title}"





#new


from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
from decimal import Decimal
import uuid




class InvestmentPool(models.Model):
    """
    Ready for future 2-50 investors collection.
    In current flow: only lead investor pays, but pool stores split info.
    """
    STATUS = [
        ("inactive", "Inactive"),
        ("open", "Open"),
        ("closed", "Closed"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.OneToOneField("Property", on_delete=models.CASCADE, related_name="investment_pool")
    investors_required = models.PositiveIntegerField(default=2)  # 2-50
    total_required = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS, default="inactive")
    created_at = models.DateTimeField(auto_now_add=True)

    @builtins.property
    def per_investor_amount(self):
        if self.investors_required <= 0:
            return Decimal("0.00")
        return (self.total_required / Decimal(self.investors_required)).quantize(Decimal("0.01"))


class Investment(models.Model):
    STATUS = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("failed", "Failed"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pool = models.ForeignKey(InvestmentPool, on_delete=models.CASCADE, related_name="investments")
    investor = models.ForeignKey(
    User,
    on_delete=models.CASCADE,
    related_name="property_investments"
)

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("pool", "investor")  # equal split => only one investment per pool






from django.db import models
from django.contrib.auth.models import User
import uuid
from decimal import Decimal

class OwnerNotification(models.Model):
    TYPE_CHOICES = [("interest","Interest"), ("payment","Payment"), ("sold","Sold")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
    User,
    on_delete=models.CASCADE,
    related_name="property_notifications"
)

    property = models.ForeignKey("Property", on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=120)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]





import uuid
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
from django.core.exceptions import ValidationError

def money_round(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

class PurchasePlan(models.Model):
    MODE = [("single", "Single Pay"), ("group", "Group Pay")]
    STATUS = [("draft","Draft"), ("requested","Requested"), ("active","Active"), ("closed","Closed")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey("Property", on_delete=models.CASCADE, related_name="purchase_plans")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="purchase_plans")

    mode = models.CharField(max_length=10, choices=MODE)
    group_size = models.PositiveIntegerField(default=1)  # 1 for single, 2-50 for group

    base_price = models.DecimalField(max_digits=15, decimal_places=2)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("18.00"))
    platform_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("10.00"))
    total_payable = models.DecimalField(max_digits=15, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)

    def calc_total(self) -> Decimal:
        multiplier = Decimal("1.00") + (self.gst_percent / Decimal("100")) + (self.platform_percent / Decimal("100"))
        return money_round(self.base_price * multiplier)

    def per_person_amount(self) -> Decimal:
        if self.group_size <= 0:
            return Decimal("0.00")
        return money_round(self.total_payable / Decimal(self.group_size))
    
    def is_ready_to_activate(self) -> bool:
        """Check if plan can move from requested → active"""
        return (
            self.confirmed_count == self.group_size and
            self.confirmed_total >= self.total_payable
        )
    
    def activate(self):
        """Safely transition to active"""
        if not self.is_ready_to_activate():
            raise ValidationError("Plan not ready")
        self.status = "active"
        self.save()

    def last_person_amount(self) -> Decimal:
        share = self.per_person_amount()
        if self.group_size <= 1:
            return self.total_payable
        return money_round(self.total_payable - (share * Decimal(self.group_size - 1)))

    @builtins.property
    def confirmed_total(self) -> Decimal:
        s = self.contributions.filter(status="confirmed").aggregate(t=Sum("amount"))["t"]
        return s or Decimal("0.00")

    @builtins.property
    def confirmed_count(self) -> int:
        return self.contributions.filter(status="confirmed").count()


class PlanInvite(models.Model):
    STATUS = [("invited","Invited"), ("accepted","Accepted"), ("declined","Declined")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(PurchasePlan, on_delete=models.CASCADE, related_name="invites")
    invited_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="plan_invites")
    status = models.CharField(max_length=20, choices=STATUS, default="invited")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("plan", "invited_user")


class PropertyInterest(models.Model):
    STATUS = [("requested","Requested"), ("accepted","Accepted"), ("rejected","Rejected")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey("Property", on_delete=models.CASCADE, related_name="interest_requests")
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name="interest_requests")

    # IMPORTANT: make this OneToOne (one interest -> one plan)
    plan = models.OneToOneField(PurchasePlan, on_delete=models.CASCADE, related_name="interest")

    status = models.CharField(max_length=20, choices=STATUS, default="requested")
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("property", "requester")


class Contribution(models.Model):
    STATUS = [("pending","Pending"), ("confirmed","Confirmed"), ("failed","Failed")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(PurchasePlan, on_delete=models.CASCADE, related_name="contributions")
    payer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="contributions")

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def refund(self, reason: str):
        """Process refund if transaction exists"""
        if self.transaction and self.transaction.status == "success":
            # Call Razorpay refund API
            # Create refund record
            # Mark contribution as refunded
            pass

    class Meta:
        unique_together = ("plan", "payer")




class Transaction(models.Model):
    STATUS = [
        ("success", "Success"),
        ("failed", "Failed"),
        ("pending", "Pending"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contribution = models.OneToOneField(Contribution, on_delete=models.CASCADE, related_name="transaction")

    provider = models.CharField(max_length=30, default="fake")  # later razorpay
    status = models.CharField(max_length=20, choices=STATUS, default="success")

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    payer_name = models.CharField(max_length=120)
    payer_phone = models.CharField(max_length=20)
    note = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # later razorpay fields
    provider_order_id = models.CharField(max_length=100, blank=True, null=True)
    provider_payment_id = models.CharField(max_length=100, blank=True, null=True)
    provider_signature = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]



import uuid

class GroupPaymentInvite(models.Model):
    plan = models.ForeignKey(PurchasePlan, on_delete=models.CASCADE)
    invited_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False )

    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
        ],
        default="pending"
    )




import uuid
from django.db import models
from django.contrib.auth.models import User


class PropertyRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    PAYMENT_MODE = [
        ("single", "Single Payment"),
        ("group", "Group Payment"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="property_requests")
    property = models.ForeignKey("Property", on_delete=models.CASCADE, related_name="purchase_requests")

    full_name = models.CharField(max_length=120)
    age = models.PositiveIntegerField()
    occupation = models.CharField(max_length=120)

    payment_mode = models.CharField(max_length=10, choices=PAYMENT_MODE)
    group_size = models.PositiveIntegerField(null=True, blank=True)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Property Request"
        verbose_name_plural = "Property Requests"

    def __str__(self):
        return f"{self.full_name} → {self.property.title}"





#new



class PropertyListingRequest(models.Model):
    STATUS_CHOICES = [
        ("payment_pending", "Payment Pending"),
        ("paid", "Paid"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    property = models.OneToOneField(
        Property,
        on_delete=models.CASCADE,
        related_name="listing_request"
    )

    listing_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1000
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="payment_pending"
    )

    is_paid = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
