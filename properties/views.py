from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.shortcuts import get_object_or_404

from wallet.services import credit_wallet
from .filters import PropertyFilter
from django.db import transaction as db_tx
from .models import *
from .serializers import *
from .serializers import GroupPaymentInviteSerializer
from decimal import Decimal
from wallet.calculations import calculate_net_balance_for_user
from wallet.models import PaymentTransaction, Wallet



class PropertyListCreateView(generics.ListCreateAPIView):
    queryset = Property.objects.all()
    queryset = Property.objects.filter(
        status="available",
        is_verified=True
    )
    
    
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PropertyFilter
    search_fields = ['title', 'description', 'location', 'city']
    ordering_fields = ['price', 'area_sqft', 'created_at', 'views_count']
    ordering = ['-created_at']
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PropertyCreateUpdateSerializer
        return PropertyListSerializer
    def get_serializer_context(self):
       return {"request": self.request}
    
    def perform_create(self, serializer):
        user = self.request.user
        VERIFICATION_FEE = Decimal("1000.00")

        # Default property state
        is_verified = False
        status = "draft"

        # Ensure wallet exists
        wallet, _ = Wallet.objects.get_or_create(user=user)

        # ✅ CHECK DERIVED BALANCE
        balance = calculate_net_balance_for_user(user) + wallet.bonus_balance
        if balance >= VERIFICATION_FEE:
            # 🔥 CREATE APPROVED INVESTMENT TRANSACTION
            PaymentTransaction.objects.create(
                user=user,
                transaction_type="withdrawal",
                amount=VERIFICATION_FEE,
                status="approved",
                wallet=wallet,
                wallet_effect="debit",
                admin_note="Property verification fee",
                processed_at=timezone.now(),
            )

            is_verified = True
            status = "draft"

        # ✅ CREATE PROPERTY
        serializer.save(
            owner=user,
            is_verified=is_verified,
            status=status
        )
    


class PropertyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a property"""
    queryset = Property.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return PropertyCreateUpdateSerializer
        return PropertyDetailSerializer
    
    def get_object(self):
        obj = super().get_object()
        # Increment view count if it's a GET request and not the owner

        # 🔒 Draft protection
        if obj.status == "draft" and self.request.user != obj.owner and not self.request.user.is_staff:
            raise PermissionDenied("Property is not published yet")
    

        if self.request.method == 'GET' and self.request.user != obj.owner:
            obj.views_count += 1
            obj.save(update_fields=['views_count'])
        return obj
    
    def perform_update(self, serializer):
        # Only owner can update their property
        if serializer.instance.owner != self.request.user:
            raise PermissionDenied("You can only update your own properties.")
        serializer.save()
    
    def perform_destroy(self, instance):
        # Only owner can delete their property
        if instance.owner != self.request.user:
            raise PermissionDenied("You can only delete your own properties.")
        instance.delete()

class MyPropertiesView(generics.ListAPIView):
    """List current user's properties"""
    serializer_class = PropertyListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Property.objects.filter(owner=self.request.user)

class PropertyImageUploadView(generics.CreateAPIView):
    """Upload images for a property"""
    serializer_class = PropertyImageSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def create(self, request, *args, **kwargs):
        property_id = kwargs.get('property_id')
        property_obj = get_object_or_404(Property, id=property_id)
        
        # Check if user owns the property
        if property_obj.owner != request.user:
            return Response(
                {'error': 'You can only upload images for your own properties.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Handle multiple image upload
        images_data = request.FILES.getlist('images')
        uploaded_images = []
        
        for image_data in images_data:
            serializer = self.get_serializer(data={
                'image': image_data,
                'property': property_obj.id
            })
            if serializer.is_valid():
                serializer.save(property=property_obj)
                uploaded_images.append(serializer.data)
        
        return Response({
            'message': f'{len(uploaded_images)} images uploaded successfully',
            'images': uploaded_images
        }, status=status.HTTP_201_CREATED)

class PropertyInquiryView(generics.CreateAPIView):
    """Create an inquiry for a property"""
    serializer_class = PropertyInquirySerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        property_id = kwargs.get('property_id')
        property_obj = get_object_or_404(Property, id=property_id)
        
        # Don't allow owner to inquire about their own property
        if property_obj.owner == request.user:
            return Response(
                {'error': 'You cannot inquire about your own property.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(property=property_obj, inquirer=request.user)
            return Response({
                'message': 'Inquiry sent successfully!',
                'inquiry': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MyInquiriesView(generics.ListAPIView):
    """List user's inquiries"""
    serializer_class = PropertyInquirySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PropertyInquiry.objects.filter(inquirer=self.request.user)

class PropertyInquiriesReceivedView(generics.ListAPIView):
    """List inquiries received for user's properties"""
    serializer_class = PropertyInquirySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PropertyInquiry.objects.filter(property__owner=self.request.user)

@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def toggle_favorite(request, property_id):
    """Toggle property favorite status"""
    property_obj = get_object_or_404(Property, id=property_id)
    
    if request.method == 'POST':
        favorite, created = PropertyFavorite.objects.get_or_create(
            property=property_obj, 
            user=request.user
        )
        if created:
            return Response({
                'message': 'Property added to favorites',
                'is_favorited': True
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'message': 'Property already in favorites',
                'is_favorited': True
            })
    
    elif request.method == 'DELETE':
        try:
            favorite = PropertyFavorite.objects.get(
                property=property_obj, 
                user=request.user
            )
            favorite.delete()
            return Response({
                'message': 'Property removed from favorites',
                'is_favorited': False
            })
        except PropertyFavorite.DoesNotExist:
            return Response({
                'message': 'Property not in favorites',
                'is_favorited': False
            })

class FavoritePropertiesView(generics.ListAPIView):
    """List user's favorite properties"""
    serializer_class = PropertyFavoriteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PropertyFavorite.objects.filter(user=self.request.user)

@api_view(['GET'])
def property_stats(request):
    """Get property statistics"""
    total_properties = Property.objects.count()
    available_properties = Property.objects.filter(status='available').count()
    sold_properties = Property.objects.filter(status='sold').count()
    
    property_types = Property.objects.values('property_type').distinct().count()
    
    return Response({
        'total_properties': total_properties,
        'available_properties': available_properties,
        'sold_properties': sold_properties,
        'property_types': property_types,
    })


#new

class CreateInterestView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PropertyInterestCreateSerializer

    @db_tx.atomic
    def post(self, request, property_id):
        prop = get_object_or_404(Property, id=property_id)

        if prop.owner == request.user:
            return Response({"error": "Owner cannot request interest in own property."}, status=400)

        if prop.status == "sold":
            return Response({"error": "Property already sold."}, status=400)

        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        interest, created = PropertyInterest.objects.get_or_create(
            property=prop,
            requester=request.user,
            defaults={"message": ser.validated_data.get("message", "")}
        )
        if not created:
            return Response({"message": "Interest already requested.", "interest": PropertyInterestSerializer(interest).data})

        # mark property pending (as you said)
        if prop.status == "available":
            prop.status = "pending"
            prop.save(update_fields=["status"])

        # create owner notification ("popup")
        OwnerNotification.objects.create(
            user=prop.owner,
            property=prop,
            type="interest",
            title="New interest request",
            message=f"{request.user.username} is interested in {prop.title}."
        )

        # ensure pool exists (inactive until owner accepts)
        InvestmentPool.objects.get_or_create(
            property=prop,
            defaults={
                "investors_required": max(2, min(50, getattr(prop, "investors_required", 2))),
                "total_required": prop.price,
                "status": "inactive",
            }
        )

        return Response({"message": "Interest sent to owner.", "interest": PropertyInterestSerializer(interest).data}, status=201)



class InterestsReceivedView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PropertyInterestSerializer

    def get_queryset(self):
        return PropertyInterest.objects.filter(property__owner=self.request.user)




class RespondInterestView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    @db_tx.atomic
    def post(self, request, interest_id):
        action = request.data.get("action")
        if action not in ["accept", "reject"]:
            return Response({"error": "action must be accept or reject"}, status=400)

        interest = get_object_or_404(PropertyInterest, id=interest_id)
        prop = interest.property

        if prop.owner != request.user:
            raise PermissionDenied("Only owner can respond.")

        if prop.status == "sold":
            return Response({"error": "Property already sold."}, status=400)

        if action == "reject":
            interest.status = "rejected"
            interest.save(update_fields=["status"])
            return Response({"message": "Rejected.", "interest": PropertyInterestSerializer(interest).data})

        # accept = choose lead investor
        # reject all other interests for same property (since lead investor only)
        PropertyInterest.objects.filter(property=prop).exclude(id=interest.id).update(status="rejected")
        interest.status = "accepted"
        interest.save(update_fields=["status"])

        # open pool
        pool, _ = InvestmentPool.objects.get_or_create(
            property=prop,
            defaults={"investors_required": max(2, min(50, prop.investors_required)), "total_required": prop.price}
        )
        pool.investors_required = max(2, min(50, prop.investors_required))
        pool.total_required = prop.price
        pool.status = "open"
        pool.save()

        OwnerNotification.objects.create(
            user=interest.requester,
            property=prop,
            type="interest",
            title="Interest accepted",
            message=f"Owner accepted your request for {prop.title}. You can proceed to payment."
        )

        return Response({
            "message": "Accepted as lead investor.",
            "interest": PropertyInterestSerializer(interest).data,
            "pool": InvestmentPoolSerializer(pool).data
        })




class LeadInvestorTransactionView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FakeTransactionCreateSerializer

    @db_tx.atomic
    def post(self, request, property_id):
        prop = get_object_or_404(Property, id=property_id)

        if prop.owner == request.user:
            return Response({"error": "Owner cannot pay for own property."}, status=400)

        if prop.status == "sold":
            return Response({"error": "Property already sold."}, status=400)

        # must be accepted lead investor
        lead_interest = PropertyInterest.objects.filter(
            property=prop, requester=request.user, status="accepted"
        ).first()
        if not lead_interest:
            return Response({"error": "You are not accepted by owner for this property."}, status=403)

        pool = getattr(prop, "investment_pool", None)
        if not pool or pool.status != "open":
            return Response({"error": "Payment not enabled yet. Owner must accept first."}, status=400)

        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        # For now lead investor pays full amount OR per investor?
        # Since your flow sells after lead investor pays, amount = property.price.
        amount = prop.price

        tx_status = "failed" if ser.validated_data.get("force_fail") else "success"

        tx = Transaction.objects.create(
            property=prop,
            paid_by=request.user,
            status=tx_status,
            provider="fake",
            amount=amount,
            payer_name=ser.validated_data["payer_name"],
            payer_phone=ser.validated_data["payer_phone"],
            note=ser.validated_data.get("note", "")
        )

        if transaction.status == "success":
         credit_wallet(
        wallet=user.wallet,
        amount=transaction.amount,
        tx_type="investment",
        source="payment",
        reference_id=transaction.id
    )


        if tx_status != "success":
            return Response({"message": "Transaction failed.", "transaction": TransactionSerializer(tx).data}, status=400)
        
        credit_wallet(
    wallet=request.user.wallet,
    amount=amount,
    tx_type="investment",
    source="payment",
    reference_id=tx.id,
    note=f"Lead investor payment for {prop.title}"
)


        # SUCCESS => sold for everyone
        prop.status = "sold"
        prop.save(update_fields=["status"])

        pool.status = "closed"
        pool.save(update_fields=["status"])

        OwnerNotification.objects.create(
            user=prop.owner,
            property=prop,
            type="transaction",
            title="Property sold",
            message=f"Payment successful by {request.user.username}. Property marked as SOLD."
        )

        return Response({"message": "Payment successful. Property sold.", "transaction": TransactionSerializer(tx).data}, status=201)



class MyTransactionsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(paid_by=self.request.user)




class MyNotificationsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OwnerNotificationSerializer

    def get_queryset(self):
        return OwnerNotification.objects.filter(user=self.request.user)




from decimal import Decimal
from django.db import transaction as db_tx
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from django.contrib.auth.models import User
from .models import (
    Property, PurchasePlan, PlanInvite, PropertyInterest,
    Contribution, Transaction, OwnerNotification, money_round
)
from .serializers import (
    CreateInterestSerializer, PropertyInterestSerializer,
    PlanInviteSerializer, FakePaymentSerializer,
    TransactionSerializer, OwnerNotificationSerializer
)


def _is_invited(plan: PurchasePlan, user) -> bool:
    return PlanInvite.objects.filter(plan=plan, invited_user=user).exists()


def _payment_allowed(plan: PurchasePlan, user) -> bool:
    if plan.status != "active":
        return False
    if plan.property.status == "sold":
        return False
    if plan.mode == "single":
        return plan.created_by_id == user.id
    # group
    return (plan.created_by_id == user.id) or _is_invited(plan, user)


def _planned_payers_count(plan: PurchasePlan) -> int:
    # planned unique payers = creator + invited users
    return 1 + plan.invites.count()


def _compute_user_payable(plan: PurchasePlan, user) -> Decimal:
    """
    Equal split + last payer adjustment.
    Rule: last payer is the final one to pay among planned payers (based on confirmed_count).
    """
    if plan.mode == "single":
        return plan.total_payable

    share = plan.per_person_amount()
    last_share = plan.last_person_amount()

    # If this payer would complete the group (i.e., they are the last to confirm), charge last_share
    # Otherwise, charge standard share.
    remaining_after_this = plan.group_size - (plan.confirmed_count + 1)
    if remaining_after_this == 0:
        return last_share
    return share


class CreateInterestView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CreateInterestSerializer

    @db_tx.atomic
    def post(self, request, property_id):
        prop = get_object_or_404(Property, id=property_id)

        if prop.owner_id == request.user.id:
            return Response({"error": "Owner cannot create interest on own property."}, status=400)
        if prop.status == "sold":
            return Response({"error": "Property already sold."}, status=400)

        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        mode = ser.validated_data["mode"]
        group_size = ser.validated_data.get("group_size")
        invited_user_ids = ser.validated_data.get("invited_user_ids", [])
        message = ser.validated_data.get("message", "")

        if mode == "single":
            group_size = 1
            invited_user_ids = []
        else:
            if group_size is None:
                return Response({"error": "group_size is required for group mode."}, status=400)
            if not (2 <= int(group_size) <= 50):
                return Response({"error": "group_size must be between 2 and 50."}, status=400)

            if len(invited_user_ids) != int(group_size) - 1:
                return Response({"error": f"invited_user_ids must be exactly {int(group_size)-1} users."}, status=400)

            if len(set(invited_user_ids)) != len(invited_user_ids):
                return Response({"error": "Duplicate invited users not allowed."}, status=400)

            if request.user.id in invited_user_ids:
                return Response({"error": "Do not include yourself in invited_user_ids."}, status=400)

            if prop.owner_id in invited_user_ids:
                return Response({"error": "Do not invite property owner."}, status=400)

        # Create plan (snapshot pricing)
        plan = PurchasePlan.objects.create(
            property=prop,
            created_by=request.user,
            mode=mode,
            group_size=int(group_size),
            base_price=prop.price,
            gst_percent=Decimal("18.00"),
            platform_percent=Decimal("10.00"),
            total_payable=money_round(prop.price * Decimal("1.28")),
            status="requested",
        )

        # Create invites if group
        if mode == "group":
            users = User.objects.filter(id__in=invited_user_ids)
            found_ids = set(u.id for u in users)
            missing = [str(x) for x in invited_user_ids if x not in found_ids]
            if missing:
                return Response({"error": "Some invited_user_ids not found.", "missing": missing}, status=400)

            PlanInvite.objects.bulk_create([
                PlanInvite(plan=plan, invited_user=u, status="invited") for u in users
            ])

        # Create interest
        interest = PropertyInterest.objects.create(
            property=prop,
            requester=request.user,
            plan=plan,
            status="requested",
            message=message
        )

        # property becomes pending as soon as interest raised (as your earlier flow)
        if prop.status == "available":
            prop.status = "pending"
            prop.save(update_fields=["status"])

        # notify owner with details
        if mode == "single":
            detail_msg = (
                f"{request.user.username} wants to buy {prop.title} (Single Pay). "
                f"Total payable (incl GST 18% + platform 10%): {plan.total_payable}."
            )
        else:
            per_person = plan.per_person_amount()
            last_person = plan.last_person_amount()
            detail_msg = (
                f"{request.user.username} wants to buy {prop.title} (Group Pay). "
                f"Group size: {plan.group_size}. Total payable (incl GST 18% + platform 10%): {plan.total_payable}. "
                f"Per person: ~{per_person}, last payer: {last_person}."
            )

        OwnerNotification.objects.create(
            user=prop.owner,
            property=prop,
            type="interest",
            title="New purchase request",
            message=detail_msg
        )

        return Response({"message": "Interest sent to owner.", "interest": PropertyInterestSerializer(interest).data}, status=201)


class InterestsReceivedView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PropertyInterestSerializer

    def get_queryset(self):
        return PropertyInterest.objects.filter(property__owner=self.request.user)


class RespondInterestView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    @db_tx.atomic
    def post(self, request, interest_id):
        action = request.data.get("action")
        if action not in ["accept", "reject"]:
            return Response({"error": "action must be accept or reject"}, status=400)

        interest = get_object_or_404(PropertyInterest, id=interest_id)
        prop = interest.property

        if prop.owner_id != request.user.id:
            raise PermissionDenied("Only owner can respond.")

        if prop.status == "sold":
            return Response({"error": "Property already sold."}, status=400)

        if action == "reject":
            interest.status = "rejected"
            interest.save(update_fields=["status"])
            interest.plan.status = "closed"
            interest.plan.save(update_fields=["status"])
            return Response({"message": "Rejected.", "interest": PropertyInterestSerializer(interest).data})

        # ACCEPT one => reject all others
        PropertyInterest.objects.filter(property=prop).exclude(id=interest.id).update(status="rejected")

        # close other plans too
        other_plans = PurchasePlan.objects.filter(property=prop).exclude(id=interest.plan_id)
        other_plans.update(status="closed")

        interest.status = "accepted"
        interest.save(update_fields=["status"])

        plan = interest.plan
        plan.status = "active"
        plan.save(update_fields=["status"])

        # keep property pending until all payments done
        if prop.status != "pending":
            prop.status = "pending"
            prop.save(update_fields=["status"])

        OwnerNotification.objects.create(
            user=interest.requester,
            property=prop,
            type="interest",
            title="Request accepted",
            message=f"Owner accepted your request for {prop.title}. You can proceed with payment."
        )

        return Response({"message": "Accepted.", "interest": PropertyInterestSerializer(interest).data})



class PlanPayableView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, plan_id):
        plan = get_object_or_404(PurchasePlan, id=plan_id)

        allowed = _payment_allowed(plan, request.user)
        if not allowed:
            return Response({"allowed": False, "error": "You are not allowed to pay for this plan."}, status=403)

        if plan.mode == "group" and _planned_payers_count(plan) != plan.group_size:
            return Response({"allowed": False, "error": "Invites are not complete for this group size."}, status=400)

        payable = _compute_user_payable(plan, request.user)

        return Response({
            "allowed": True,
            "plan_id": str(plan.id),
            "mode": plan.mode,
            "group_size": plan.group_size,
            "base_price": str(plan.base_price),
            "gst_percent": str(plan.gst_percent),
            "platform_percent": str(plan.platform_percent),
            "total_payable": str(plan.total_payable),
            "confirmed_count": plan.confirmed_count,
            "confirmed_total": str(plan.confirmed_total),
            "your_payable": str(payable),
            "note": "Last payer amount may differ slightly due to rounding."
        })




class PlanPayView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FakePaymentSerializer

    @db_tx.atomic
    def post(self, request, plan_id):
        plan = get_object_or_404(PurchasePlan, id=plan_id)
        prop = plan.property
        user = request.user

        if not _payment_allowed(plan, user):
            return Response({"error": "You are not allowed to pay for this plan."}, status=403)

        if prop.status == "sold":
            return Response({"error": "Property already sold."}, status=400)

        if not hasattr(plan, "interest") or plan.interest.status != "accepted" or plan.status != "active":
            return Response({"error": "Owner has not accepted this plan yet."}, status=400)

        if Contribution.objects.filter(plan=plan, payer=user, status="confirmed").exists():
            return Response({"error": "You have already paid for this plan."}, status=400)

        if plan.confirmed_count >= plan.group_size:
            return Response({"error": "Plan already fully paid."}, status=400)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        amount = _compute_user_payable(plan, user)

        # 🔐 GROUP PAYMENT RULES
        # ✅ LINK-BASED GROUP PAYMENT RULE   
        if plan.mode == "group":
            if plan.confirmed_count >= plan.group_size:
                   return Response(
                    {"error": "Group payment is already full."},
                    status=400
                )
        contribution = Contribution.objects.create(
            plan=plan,
            payer=user,
            amount=amount,
            status="pending"
        )

        tx_status = "failed" if serializer.validated_data.get("force_fail") else "success"

        transaction = Transaction.objects.create(
            contribution=contribution,
            provider="fake",
            status=tx_status,
            amount=amount,
            payer_name=serializer.validated_data["payer_name"],
            payer_phone=serializer.validated_data["payer_phone"],
            note=serializer.validated_data.get("note", "")
        )
        if transaction.status == "success":
          credit_wallet(
        wallet=user.wallet,
        amount=transaction.amount,
        tx_type="investment",
        source="payment",
        reference_id=transaction.id
    )
    

        if tx_status != "success":
            contribution.status = "failed"
            contribution.save(update_fields=["status"])
            return Response({"message": "Transaction failed."}, status=400)

        contribution.status = "confirmed"
        contribution.save(update_fields=["status"])

        # 🔗 WALLET CREDIT HOOK
        credit_wallet(
        wallet=user.wallet,
        amount=amount,
        tx_type="investment",
        source="payment",
        reference_id=transaction.id,
        note=f"Property investment payment for {prop.title}"
)


        # ✅ Mark invite as paid
        if plan.mode == "group" and user != plan.created_by:
            GroupPaymentInvite.objects.filter(
                plan=plan,
                invited_user=user
            ).update(status="paid")

        OwnerNotification.objects.create(
            user=prop.owner,
            property=prop,
            type="payment",
            title="Payment received",
            message=f"{user.username} paid ₹{amount} for {prop.title}."
        )

        if plan.confirmed_count == plan.group_size and plan.confirmed_total == plan.total_payable:
            prop.status = "sold"
            prop.save(update_fields=["status"])

            plan.status = "closed"
            plan.save(update_fields=["status"])

            OwnerNotification.objects.create(
                user=prop.owner,
                property=prop,
                type="sold",
                title="Property sold",
                message=f"{prop.title} is fully paid and marked SOLD."
            )

        return Response(
            {
                "message": "Payment successful.",
                "transaction": TransactionSerializer(transaction).data,
                "property_status": prop.status,
                "confirmed_count": plan.confirmed_count,
                "confirmed_total": str(plan.confirmed_total),
                "total_payable": str(plan.total_payable),
            },
            status=201,
        )



class MyTransactionsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(
            contribution__payer=self.request.user
        ).select_related(
            "contribution",
            "contribution__plan",
            "contribution__plan__property"
        )


class MyNotificationsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OwnerNotificationSerializer

    def get_queryset(self):
        return OwnerNotification.objects.filter(user=self.request.user)






class MyInterestsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PropertyInterestSerializer

    def get_queryset(self):
        return PropertyInterest.objects.filter(requester=self.request.user)





from django.contrib.auth.models import User
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from .serializers import UserMiniSerializer

class UserListView(ListAPIView):
    serializer_class = UserMiniSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return User.objects.all()




class CreateGroupPurchaseView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    @db_tx.atomic
    def post(self, request, property_id):
        prop = get_object_or_404(Property, id=property_id)

        if prop.owner_id == request.user.id:
            return Response({"error": "Owner cannot create request"}, status=400)

        if prop.status == "sold":
            return Response({"error": "Property already sold"}, status=400)

        group_size = request.data.get("group_size")
        message = request.data.get("message", "")

        if not group_size or not (2 <= int(group_size) <= 50):
            return Response(
                {"error": "group_size must be between 2 and 50"},
                status=400
            )

        # 🔒 RULE: user can only have ONE interest per property
        if PropertyInterest.objects.filter(
            property=prop,
            requester=request.user
        ).exists():
            return Response(
                {"error": "You already have an active request for this property."},
                status=400
            )

        # 1️⃣ CREATE PLAN FIRST
        plan = PurchasePlan.objects.create(
            property=prop,
            created_by=request.user,
            mode="group",
            group_size=int(group_size),
            base_price=prop.price,
            gst_percent=Decimal("18.00"),
            platform_percent=Decimal("10.00"),
            total_payable=money_round(prop.price * Decimal("1.28")),
            status="requested",
        )

        # 2️⃣ AUTO-GENERATE DUMMY INVITES
        users = User.objects.exclude(
            id__in=[request.user.id, prop.owner_id]
        )[: int(group_size) - 1]

        if users.count() != int(group_size) - 1:
            return Response(
                {"error": "Not enough users available"},
                status=400
            )

        PlanInvite.objects.bulk_create([
            PlanInvite(plan=plan, invited_user=u)
            for u in users
        ])

        # 3️⃣ CREATE INTEREST WITH PLAN (REQUIRED)
        interest = PropertyInterest.objects.create(
            property=prop,
            requester=request.user,
            plan=plan,
            status="requested",
            message=message,
        )

        # property → pending
        if prop.status == "available":
            prop.status = "pending"
            prop.save(update_fields=["status"])

        # notify owner
        OwnerNotification.objects.create(
            user=prop.owner,
            property=prop,
            type="interest",
            title="Group purchase request",
            message=(
                f"{request.user.username} requested group purchase "
                f"({group_size} investors)."
            )
        )

        return Response(
            {"message": "Group purchase request sent successfully"},
            status=201
        )



class InitiateGroupPaymentView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    @db_tx.atomic
    def post(self, request, plan_id):
        plan = get_object_or_404(PurchasePlan, id=plan_id)

        if plan.created_by != request.user:
            return Response({"error": "Only host can initiate"}, status=403)

        if plan.mode != "group" or plan.status != "active":
            return Response({"error": "Invalid plan state"}, status=400)

        if GroupPaymentInvite.objects.filter(plan=plan).exists():
            return Response({"error": "Already initiated"}, status=400)

        invites = PlanInvite.objects.filter(plan=plan)

        for invite in invites:
            GroupPaymentInvite.objects.create(
                plan=plan,
                invited_user=invite.invited_user,
                amount=plan.per_person_amount(),
            )

            OwnerNotification.objects.create(
                user=invite.invited_user,
                property=plan.property,
                type="group_payment",
                title="Group payment request",
                message=(
                    f"{request.user.username} invited you to pay "
                    f"₹{plan.per_person_amount()} for {plan.property.title}"
                )
            )

        return Response({"message": "Group payment initiated"}, status=201)




class RespondGroupPaymentInviteView(generics.GenericAPIView):
    permission_classes = []  # 🔥 REMOVE AUTH

    @db_tx.atomic
    def post(self, request, invite_id):
        action = request.data.get("action")

        if action not in ["accept", "reject"]:
            return Response(
                {"error": "action must be accept or reject"},
                status=400
            )

        invite = get_object_or_404(
            GroupPaymentInvite,
            token=invite_id
        )

        if invite.status != "pending":
            return Response({"error": "Already responded"}, status=400)

        if action == "accept":
            invite.status = "accepted"
            invite.save(update_fields=["status"])

            OwnerNotification.objects.create(
                user=invite.plan.created_by,
                property=invite.plan.property,
                type="group_payment",
                title="Group payment accepted",
                message="A member accepted the group payment invite"
            )

            return Response({
                "message": "Invite accepted",
                "redirect": f"/payment/{invite.plan.id}"
            })

        invite.status = "rejected"
        invite.save(update_fields=["status"])

        OwnerNotification.objects.create(
            user=invite.plan.created_by,
            property=invite.plan.property,
            type="group_payment",
            title="Group payment rejected",
            message="A member rejected the group payment invite"
        )

        return Response({"message": "Invite rejected"})



class UserSearchView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserMiniSerializer

    def get_queryset(self):
        q = self.request.query_params.get("q")
        if not q:
            return User.objects.none()
        
    def get_queryset(self):
        print("SEARCH USER:", self.request.user)
        print("QUERY:", self.request.query_params.get("q"))

        q = self.request.query_params.get("q")
        if not q:
         return User.objects.none()

        return User.objects.filter(username__icontains=q)

        return User.objects.filter(
            username__icontains=q
        ).exclude(id=self.request.user.id)
    
    




class SendGroupPaymentInviteView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, plan_id):
        plan = get_object_or_404(PurchasePlan, id=plan_id)

        if plan.created_by != request.user:
            return Response({"error": "Only host can invite"}, status=403)

        user_id = request.data.get("user_id")
        user = get_object_or_404(User, id=user_id)

        if GroupPaymentInvite.objects.filter(plan=plan, invited_user=user).exists():
            return Response({"error": "Already invited"}, status=400)

        GroupPaymentInvite.objects.create(
            plan=plan,
            invited_user=user,
            is_payer=False
        )

        OwnerNotification.objects.create(
            user=user,
            property=plan.property,
            type="group_payment",
            title="Group payment request",
            message=f"{request.user.username} invited you to join payment for {plan.property.title}"
        )

        return Response({"message": "Invite sent"})




from rest_framework import generics
from rest_framework.permissions import IsAuthenticated



class MyGroupPaymentInvitesView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GroupPaymentInviteSerializer

    def get_queryset(self):
        qs = GroupPaymentInvite.objects.all()
        print("DEBUG INVITES:", qs)  # 👈 TEMP DEBUG
        return qs




class CreateShareInviteView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, plan_id):
        plan = get_object_or_404(PurchasePlan, id=plan_id)

        if plan.created_by != request.user:
            return Response({"error": "Only host can create invite"}, status=403)

        invite = GroupPaymentInvite.objects.create(
            plan=plan,
            invited_user=None  # will be set when user accepts
        )

        link = f"http://localhost:5173/group-invite/{invite.token}"

        return Response({
            "invite_link": link
        })



class PropertyImageDeleteView(generics.DestroyAPIView):
    queryset = PropertyImage.objects.all()
    permission_classes = [IsAuthenticated]


from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import PropertyRequest, Property
from .serializers import PropertyRequestSerializer


# CREATE REQUEST (FORM SUBMIT)
class CreatePropertyRequestView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PropertyRequestSerializer

    def perform_create(self, serializer):
        property_id = self.kwargs["property_id"]
        prop = get_object_or_404(Property, id=property_id)

        serializer.save(
            user=self.request.user,
            property=prop,
            status="pending"
        )


# LIST MY REQUESTS (Pending / Approved / Rejected)
class MyPropertyRequestsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PropertyRequestSerializer

    def get_queryset(self):
        return PropertyRequest.objects.filter(user=self.request.user)





from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from .models import Property, PropertyImage
from .serializers import PropertyImageSerializer


# 🔹 LIST IMAGES FOR A PROPERTY
class PropertyImageListView(generics.ListAPIView):
    serializer_class = PropertyImageSerializer

    def get_queryset(self):
        return PropertyImage.objects.filter(
            property_id=self.kwargs["property_id"]
        )
    
class SetPrimaryPropertyImageView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = PropertyImage.objects.all()

    def update(self, request, *args, **kwargs):
        img = self.get_object()
        if img.property.owner != request.user:
            raise PermissionDenied()

        PropertyImage.objects.filter(property=img.property).update(is_primary=False)
        img.is_primary = True
        img.save()

        return Response({"message": "Primary image set"})


class PropertyImageDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = PropertyImage.objects.all()

# 🔹 UPLOAD MULTIPLE IMAGES
class PropertyImageUploadView(generics.CreateAPIView):
    serializer_class = PropertyImageSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        property_id = kwargs["property_id"]
        prop = get_object_or_404(Property, id=property_id)

        # 🔐 Only owner can upload
        if prop.owner != request.user:
            raise PermissionDenied("You can upload images only for your own property")

        images = request.FILES.getlist("images")
        if not images:
            return Response(
                {"error": "No images provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        uploaded = []
        for img in images:
            serializer = self.get_serializer(
                data={"image": img},
                context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(property=prop)
            uploaded.append(serializer.data)

        return Response(
            {
                "message": f"{len(uploaded)} images uploaded successfully",
                "images": uploaded,
            },
            status=status.HTTP_201_CREATED
        )


# 🔹 SET PRIMARY IMAGE
class SetPrimaryPropertyImageView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PropertyImageSerializer
    queryset = PropertyImage.objects.all()

    def update(self, request, *args, **kwargs):
        image = self.get_object()

        if image.property.owner != request.user:
            raise PermissionDenied("Only owner can set primary image")

        # Reset others
        PropertyImage.objects.filter(
            property=image.property
        ).update(is_primary=False)

        image.is_primary = True
        image.save(update_fields=["is_primary"])

        return Response({"message": "Primary image updated"})


# 🔹 DELETE IMAGE
class PropertyImageDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = PropertyImage.objects.all()

    def perform_destroy(self, instance):
        if instance.property.owner != self.request.user:
            raise PermissionDenied("Only owner can delete images")
        instance.delete()







# views.py
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from .models import Property, PropertyImage
from .serializers import PropertyImageUploadSerializer


class PropertyImageUploadView(generics.CreateAPIView):
    serializer_class = PropertyImageUploadSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, property_id):
        prop = get_object_or_404(Property, id=property_id)

        # 🔐 owner check
        if prop.owner != request.user:
            raise PermissionDenied("You can upload images only for your property")

        images = request.FILES.getlist("images")

        if not images:
            return Response(
                {"error": "No images provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        created = []
        for img in images:
            image_obj = PropertyImage.objects.create(
                property=prop,
                image=img
            )
            created.append({
                "id": image_obj.id,
                "image": image_obj.image.url,
                "is_primary": image_obj.is_primary
            })

        return Response(
            {
                "message": f"{len(created)} images uploaded",
                "images": created
            },
            status=status.HTTP_201_CREATED
        )



class PropertyImageDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = PropertyImage.objects.all()

    def perform_destroy(self, instance):
        if instance.property.owner != self.request.user:
            raise PermissionDenied("Only owner can delete images")
        instance.delete()






#new 



# 🔥 SAFE PROPERTY DELETE API (FINAL OVERRIDE)
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from django.db import transaction as db_tx

class DeletePropertyView(APIView):
    permission_classes = [IsAuthenticated]

    @db_tx.atomic
    def delete(self, request, property_id):
        prop = get_object_or_404(Property, id=property_id)

        # 🔐 Owner check
        if prop.owner != request.user:
            raise PermissionDenied("You can delete only your own property")

        # ❌ Block delete if already sold
        if prop.status == "sold":
            return Response(
                {"error": "Sold property cannot be deleted"},
                status=status.HTTP_400_BAD_REQUEST
            )

        title = prop.title
        prop.delete()  # CASCADE deletes everything linked

        return Response(
    {
        "message": "Property deleted successfully",
        "property_title": title
    },
    status=status.HTTP_200_OK
)




from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from .models import Property, PropertyListingRequest


class CreatePropertyListingRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, property_id):
        prop = get_object_or_404(Property, id=property_id)

        if prop.owner != request.user:
            raise PermissionDenied("Only owner can request listing")

        if prop.is_verified:
            return Response(
                {"error": "Property already listed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if hasattr(prop, "listing_request"):
            return Response(
                {"error": "Listing request already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )

        req = PropertyListingRequest.objects.create(
            user=request.user,
            property=prop,
            status="payment_pending",
            is_paid=False
        )

        return Response(
            {
                "request_id": str(req.id),
                "listing_fee": str(req.listing_fee),
                "currency": "INR",
                "status": req.status,
                "message": "Listing payment required"
            },
            status=status.HTTP_201_CREATED
        )




class MyListingRequestsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = PropertyListingRequest.objects.filter(user=request.user)

        data = [
            {
                "id": str(r.id),
                "property_title": r.property.title,
                "status": r.status,
                "is_paid": r.is_paid,
                "fee": str(r.listing_fee),
                "created_at": r.created_at,
            }
            for r in qs
        ]

        return Response(data)
    



from django.utils import timezone
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction as db_tx

class ListingPaymentView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    @db_tx.atomic
    def post(self, request, request_id):
        listing = get_object_or_404(PropertyListingRequest, id=request_id)

        if listing.user != request.user:
            return Response({"error": "Not allowed"}, status=403)

        if listing.is_paid:
            return Response({"error": "Already paid"}, status=400)

        # 🔹 Simulated payment (replace with Razorpay later)
        amount = listing.listing_fee

        tx = Transaction.objects.create(
            provider="fake",
            status="success",
            amount=amount,
            payer_name=request.user.username,
            payer_phone="N/A",
            note="Property listing fee"
        )

        # ✅ Mark listing as paid
        listing.is_paid = True
        listing.status = "paid"
        listing.paid_at = timezone.now()
        listing.save()

        # ✅ Verify & list property
        prop = listing.property
        prop.is_verified = True
        prop.save(update_fields=["is_verified"])

        return Response(
            {
                "message": "Listing payment successful",
                "transaction_id": str(tx.id),
                "property_id": str(prop.id),
                "property_listed": True
            },
            status=status.HTTP_200_OK
        )
