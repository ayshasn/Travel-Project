from django.contrib.auth.models import User
from rest_framework import serializers
from .models import UserProfile, Admin, Manager, Employee, TravelRequest
 
# ========================== User Serializers ==========================
 
class UserSerializer(serializers.ModelSerializer):
    """Serializer for the User model with role and status from UserProfile"""
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
 
    class Meta:
        model = UserProfile
        fields = ['id', 'username', 'email', 'role', 'status']
 
 
class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new User with hashed password"""
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=UserProfile.ROLE_CHOICES)  
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role']
 
    def create(self, validated_data):
        role = validated_data.pop('role')  
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']  
        )
        UserProfile.objects.create(user=user, role=role)  
        return user
 
# ========================== Admin Serializers ==========================
 
class AdminSerializer(serializers.ModelSerializer):
    """Serializer for Admin model"""
    user = UserSerializer()  
 
    class Meta:
        model = Admin
        fields = ['id', 'user', 'username', 'email_id']
 
# ========================== Manager Serializers ==========================
 
class ManagerSerializer(serializers.ModelSerializer):
    """Serializer for Manager model"""
    user_profile = UserSerializer()  
 
    class Meta:
        model = Manager
        fields = ['id', 'user_profile', 'first_name', 'last_name', 'email', 'designation', 'status']
 
# ========================== Employee Serializers ==========================
 
class EmployeeSerializer(serializers.ModelSerializer):
    """Serializer for Employee model"""
    user_profile = UserSerializer() 
    manager = serializers.PrimaryKeyRelatedField(queryset=Manager.objects.all(), allow_null=True)
 
    class Meta:
        model = Employee
        fields = ['id', 'user_profile', 'first_name', 'last_name', 'email', 'designation', 'status', 'manager']
 
# ========================== Travel Request Serializers ==========================
 
class EmployeeTravelRequestSerializer(serializers.ModelSerializer):
    """Serializer for employees to view their travel requests"""
    manager = serializers.CharField(source='manager.first_name', read_only=True)
 
    class Meta:
        model = TravelRequest
        fields = ['id', 'manager', 'from_location', 'to_location', 'start_date', 'end_date', 'status']
 
 
class ManagerTravelRequestSerializer(serializers.ModelSerializer):
    """Serializer for managers to view and manage employee travel requests"""
    employee_name = serializers.CharField(source='employee.first_name', read_only=True)
 
    class Meta:
        model = TravelRequest
        fields = ['id', 'employee_name', 'status']
 
 
class TravelRequestSerializer(serializers.ModelSerializer):
    """Serializer for travel requests ensuring correct reference handling"""
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())
    manager = serializers.PrimaryKeyRelatedField(queryset=Manager.objects.all())

    class Meta:
        model = TravelRequest
        fields = [
            'id', 'employee', 'manager', 'from_location', 'to_location',
            'start_date', 'end_date', 'status', 'is_closed', 'additional_notes','travel_mode'
        ]
