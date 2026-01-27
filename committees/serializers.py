from rest_framework import serializers
from .models import Committee, CommitteeMembership


class CommitteeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Committee
        fields = "__all__"


class CommitteeMembershipSerializer(serializers.ModelSerializer):
    committee_name = serializers.CharField(
        source="committee.name", read_only=True
    )

    class Meta:
        model = CommitteeMembership
        fields = [
            "id",
            "committee",
            "committee_name",
            "principal_invested",
            "interest_accrued",
            "joined_at",
            "status",
            "is_loan_eligible",
        ]
