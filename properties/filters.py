import django_filters
from .models import Property

class PropertyFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr='lte')
    min_area = django_filters.NumberFilter(field_name="area_sqft", lookup_expr='gte')
    max_area = django_filters.NumberFilter(field_name="area_sqft", lookup_expr='lte')
    min_bedrooms = django_filters.NumberFilter(field_name="bedrooms", lookup_expr='gte')
    max_bedrooms = django_filters.NumberFilter(field_name="bedrooms", lookup_expr='lte')
    min_bathrooms = django_filters.NumberFilter(field_name="bathrooms", lookup_expr='gte')
    max_bathrooms = django_filters.NumberFilter(field_name="bathrooms", lookup_expr='lte')
    
    city = django_filters.CharFilter(lookup_expr='icontains')
    location = django_filters.CharFilter(lookup_expr='icontains')
    property_type = django_filters.ChoiceFilter(choices=Property.PROPERTY_TYPES)
    listing_type = django_filters.ChoiceFilter(choices=Property.LISTING_TYPE)
    status = django_filters.ChoiceFilter(choices=Property.PROPERTY_STATUS)
    
    furnished = django_filters.BooleanFilter()
    parking_spaces = django_filters.NumberFilter(lookup_expr='gte')
    
    class Meta:
        model = Property
        fields = [
            'property_type', 'listing_type', 'status', 'city', 
            'bedrooms', 'bathrooms', 'furnished'
        ]
