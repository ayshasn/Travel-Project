from urllib.request import Request
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND,HTTP_204_NO_CONTENT,HTTP_500_INTERNAL_SERVER_ERROR
from django.db.utils import DatabaseError
from django.http import JsonResponse
from .models import Employee, TravelRequest,User,Admin,Manager,UserProfile
from rest_framework.decorators import api_view,permission_classes,authentication_classes
from.serializers import EmployeeSerializer,TravelRequestSerializer,AdminSerializer,ManagerSerializer
from datetime import date
from django.core.mail import send_mail
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import TokenAuthentication

 
 
 
# Employee Dashboard
@api_view(["GET"])
@permission_classes([AllowAny]) 
def employee_view_dashboard(request):
    """
    Retrieves all travel requests for the logged-in employee.

    This function fetches all travel requests associated with the currently authenticated employee.

    Returns:
        Response (JSON): A list of the employee's travel requests.
            - HTTP 200: Successfully retrieved travel requests.
            - HTTP 404: Employee profile not found.
    """
    try:
        employee = Employee.objects.get(user_profile__user=request.user)  
        travel_requests = TravelRequest.objects.filter(employee=employee)
        serializer = TravelRequestSerializer(travel_requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Employee.DoesNotExist:
        return Response({"error": "Employee profile not found."}, status=status.HTTP_404_NOT_FOUND)


 
@api_view(["GET"])
def employee_view_request(request, request_id):
    """
    Retrieves details of a specific travel request by its ID.

    Args:
        request (HttpRequest): The request object.
        request_id (int): The ID of the travel request to retrieve.

    Returns:
        Response (JSON): The travel request details.
            - HTTP 200: Request found and returned successfully.
            - HTTP 404: Travel request with the given ID does not exist.
    """
    try:
        travel_request = TravelRequest.objects.get(id=request_id)
        serializer = TravelRequestSerializer(travel_request) 
        return Response(serializer.data, status=HTTP_200_OK)
    except TravelRequest.DoesNotExist:
        return Response({"error": "Request not found"}, status=HTTP_404_NOT_FOUND)
 
 
# Edit Travel Request
@api_view(["PUT"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def employee_edit_request(request, request_id):
    """
    Allows employees to edit their own pending travel request.

    This function enables an authenticated employee to update an existing travel request 
    if it is still in the "pending" status.

    Args:
        request (HttpRequest): The request object containing the updated travel details.
        request_id (int): The ID of the travel request to edit.

    Returns:
        Response (JSON): The updated travel request details.
            - HTTP 200: Request successfully updated.
            - HTTP 400: Validation error in submitted data.
            - HTTP 404: Travel request not found or does not belong to the employee.
    """
    try:
        travel_request = TravelRequest.objects.get(
            id=request_id,
            employee__user_profile__user=request.user,
             
        )
    except TravelRequest.DoesNotExist:
        return Response({"error": "Pending travel request not found."}, status=status.HTTP_404_NOT_FOUND)

    serializer = TravelRequestSerializer(travel_request, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Request updated successfully!", "data": serializer.data}, status=status.HTTP_200_OK)
    
    return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)



# Cancel Travel Request (Only if not approved/rejected & is a past request)
@api_view(["PUT"])
@authentication_classes([TokenAuthentication])
def employee_cancel_request(request, request_id):
    """
    Allows employees to cancel a travel request if:
    - The request is not already approved or rejected.
    - The request is eligible for cancellation.

    Args:
        request (HttpRequest): The request object from the authenticated employee.
        request_id (int): The ID of the travel request to be cancelled.

    Returns:
        Response (JSON): A message confirming the cancellation or an error message.
            - HTTP 200: Request cancelled successfully.
            - HTTP 400: Request cannot be cancelled (already approved/rejected).
            - HTTP 404: Travel request not found.
    """
    try:
        travel_request = TravelRequest.objects.get(id=request_id)
    except TravelRequest.DoesNotExist:
        return Response({"error": "Request not found."}, status=HTTP_404_NOT_FOUND)
    
    # Check if travel date is in the past
    # if travel_request.start_date > date.today():
    #     return Response({"error": "Only past requests can be cancelled."}, status=HTTP_400_BAD_REQUEST)
    # Check if the request is already approved/rejected

    if travel_request.status in ["approved", "rejected"]:
        return Response({"error": "Approved or rejected requests cannot be cancelled."}, status=HTTP_400_BAD_REQUEST)
 
    # Cancel the request
    travel_request.status = 'cancelled'
    travel_request.is_closed = True
    travel_request.save()
 
    return Response({"message": "Request has been cancelled successfully."}, status=HTTP_200_OK)


@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def employee_submit_request(request):
    """
    Allows employees to submit a new travel request.

    This function validates the request details, ensures that the employee has an assigned manager, 
    and saves the request in the database.

    Args:
        request (HttpRequest): The request object containing travel request details.

    Returns:
        Response (JSON): A success message with travel request data or an error message.
            - HTTP 201: Travel request submitted successfully.
            - HTTP 400: Missing or invalid data (e.g., past start date, missing manager).
            - HTTP 404: Employee profile not found.
    """
    data = request.data 
    try:
        employee = Employee.objects.get(user_profile__user=request.user) 
    except Employee.DoesNotExist:
        return Response({"error": "Employee profile not found."}, status=status.HTTP_404_NOT_FOUND)

    # Validate date fields
    start_date = data.get("start_date")
    end_date = data.get("end_date")

    if not start_date or not end_date:
        return Response({"error": "Start date and end date are required."}, status=status.HTTP_400_BAD_REQUEST)

    start_date = date.fromisoformat(start_date)
    end_date = date.fromisoformat(end_date)

    if start_date < date.today():
        return Response({"error": "Start date must be in the future."}, status=status.HTTP_400_BAD_REQUEST)

    if end_date <= start_date:
        return Response({"error": "End date must be after start date."}, status=status.HTTP_400_BAD_REQUEST)

    # Assign manager from employee record
    if not employee.manager:
        return Response({"error": "Employee does not have an assigned manager."}, status=status.HTTP_400_BAD_REQUEST)

    manager = employee.manager 

  
    request_data = data.copy()
    request_data["employee"] = employee.id
    request_data["manager"] = manager.id 

    serializer = TravelRequestSerializer(data=request_data)

    if serializer.is_valid():
        travel_request = serializer.save(
            employee=employee,
            manager=manager,
            additional_notes=data.get("additional_notes", "")
        )
        return Response(
            {
                "message": "Travel request submitted successfully.",
                "data": TravelRequestSerializer(travel_request).data,
            },
            status=status.HTTP_201_CREATED
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

 
@api_view(["PUT"])
@authentication_classes([TokenAuthentication])
def employee_resubmit_request(request, request_id):
    """
    Allows employees to resubmit a travel request if it was previously marked as 'pending'.

    This function ensures that the travel request exists, is in the correct status for resubmission, 
    and has at least one updated field before being resubmitted.

    Args:
        request (HttpRequest): The request object containing updated travel request details.
        request_id (int): The ID of the travel request to be resubmitted.

    Returns:
        Response (JSON): The updated travel request data or an error message.
            - HTTP 200: Request successfully resubmitted.
            - HTTP 400: Request cannot be resubmitted (wrong status, no changes made).
            - HTTP 404: Travel request not found.
    """
    try:
        travel_request = TravelRequest.objects.get(id=request_id)
    except TravelRequest.DoesNotExist:
        return Response({"error": "Request not found"}, status=HTTP_404_NOT_FOUND)
 
    if travel_request.status != "pending":
        return Response({"error": "Only requests requiring more info can be resubmitted"}, status=HTTP_400_BAD_REQUEST)
 
    if not request.data:
        return Response({"error": "At least one field must be updated before resubmission"}, status=HTTP_400_BAD_REQUEST)
 
    serializer = TravelRequestSerializer(travel_request, data=request.data, partial=True)
    if serializer.is_valid():
        travel_request.status = "pending"  # Set status back to pending
        serializer.save()
        return Response(serializer.data, status=HTTP_200_OK)
 
    return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
 
#MANAGER

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def manager_view_requests(request):
    """
    Retrieves all travel requests assigned to the logged-in manager.

    This function fetches and returns all travel requests where the manager is responsible 
    for reviewing and approving them.

    Args:
        request (HttpRequest): The request object from the authenticated manager.

    Returns:
        Response (JSON): A list of travel requests with their details.
            - HTTP 200: Successfully retrieved requests.
    """
    requests = TravelRequest.objects.all()

    data = [{
        'id': req.id,
        'employee': req.employee.first_name,
        'from_location': req.from_location,
        'to_location': req.to_location,
        'status': req.status,
        'start_date': req.start_date.strftime("%Y-%m-%d"),
        'end_date': req.end_date.strftime("%Y-%m-%d"),
    } for req in requests]

    return Response(data, status=HTTP_200_OK)


from django.db.models import Q

from django.utils.dateparse import parse_date


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def manager_filter_sort_requests(request):
    """
    Filters and sorts travel requests based on query parameters.

    Managers can filter travel requests by:
        - start_date (YYYY-MM-DD)
        - end_date (YYYY-MM-DD)
        - employee_name (case-insensitive search)
        - status (pending, approved, rejected, etc.)

    Sorting options:
        - sort_by: The field to sort by (default: 'start_date')
        - sort_order: 'asc' (ascending) or 'desc' (descending)

    Args:
        request (HttpRequest): The request object containing query parameters.

    Returns:
        Response (JSON): A list of filtered and sorted travel requests.
            - HTTP 200: Successfully retrieved requests.
            - HTTP 400: Invalid date format or filtering errors.
    """
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    employee_name = request.GET.get('employee_name')
    status_filter = request.GET.get('status')
    sort_by = request.GET.get('sort_by', 'start_date')
    sort_order = request.GET.get('sort_order', 'asc')

    start_date = parse_date(start_date_str) if start_date_str else None
    end_date = parse_date(end_date_str) if end_date_str else None

    if start_date_str and not start_date:
        return Response({"error": "Invalid start_date format. Use YYYY-MM-DD."}, status=HTTP_400_BAD_REQUEST)
    if end_date_str and not end_date:
        return Response({"error": "Invalid end_date format. Use YYYY-MM-DD."}, status=HTTP_400_BAD_REQUEST)

    requests = TravelRequest.objects.all()

    if start_date and end_date:
        if start_date > end_date:
            return Response({"error": "Start date cannot be greater than end date."}, status=HTTP_400_BAD_REQUEST)

        requests = requests.filter(
            start_date__gte=start_date, 
            end_date__lte=end_date     
        )

    if employee_name:
        requests = requests.filter(employee__first_name__icontains=employee_name)

    if status_filter:
        requests = requests.filter(status=status_filter)

    if sort_order == 'desc':
        sort_by = f'-{sort_by}'
    requests = requests.order_by(sort_by)
    data = [{
        'id': req.id,
        'employee': req.employee.first_name,
        'from_location': req.from_location,
        'to_location': req.to_location,
        'status': req.status,
        'start_date': req.start_date.strftime("%Y-%m-%d"),
        'end_date': req.end_date.strftime("%Y-%m-%d"),
    } for req in requests]

    return Response(data, status=HTTP_200_OK)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def manager_search_requests(request):
    """
    Searches for travel requests based on specific parameters.

    Available search filters:
        - request_id: Exact match (numeric).
        - employee_name: Partial match, case-insensitive.
        - from_location: Partial match, case-insensitive.
        - to_location: Partial match, case-insensitive.

    Args:
        request (HttpRequest): The request object containing search query parameters.

    Returns:
        Response (JSON): A list of matching travel requests.
            - HTTP 200: Successfully retrieved search results.
            - HTTP 400: Invalid request_id format.
    """
    request_id = request.GET.get('request_id')
    employee_name = request.GET.get('employee_name')
    from_location = request.GET.get('from_location')
    to_location = request.GET.get('to_location')

    requests = TravelRequest.objects.all()


    if request_id:
        if request_id.isdigit():
            requests = requests.filter(id=int(request_id))
        else:
            return Response({"error": "Invalid request_id. It should be a number."}, status=HTTP_400_BAD_REQUEST)

    if employee_name:
        requests = requests.filter(employee__first_name__icontains=employee_name)

    if from_location:
        requests = requests.filter(from_location__icontains=from_location)

    if to_location:
        requests = requests.filter(to_location__icontains=to_location)

    data = [{
        'id': req.id,
        'employee': req.employee.first_name,
        'from_location': req.from_location,
        'to_location': req.to_location,
        'status': req.status,
        'start_date': req.start_date.strftime("%Y-%m-%d"),
        'end_date': req.end_date.strftime("%Y-%m-%d"),
    } for req in requests]

    return Response(data, status=HTTP_200_OK)
 
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
def get_travel_requests(request):
    """
    Retrieves a filtered and sorted list of travel requests.

    Available filters:
        - start_date: Retrieve requests with a travel start date greater than or equal to this value.
        - end_date: Retrieve requests with a travel end date less than or equal to this value.
        - employee_name: Partial match for the employee's first name (case-insensitive).
        - status: Filter by request status (e.g., pending, approved, rejected).

    Sorting:
        - order_by: The field to sort by (default: 'id').

    Args:
        request (HttpRequest): The request object containing filter and sorting query parameters.

    Returns:
        Response (JSON): A list of travel requests matching the criteria.
            - HTTP 200: Successfully retrieved filtered and sorted travel requests.
    """
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    employee_name = request.GET.get('employee_name')
    status_filter = request.GET.get('status')
    order_by = request.GET.get('order_by', 'id')
   
    requests = TravelRequest.objects.all()
   
    if start_date and end_date:
        requests = requests.filter(travel_from__gte=start_date, travel_to__lte=end_date)
    if employee_name:
        requests = requests.filter(employee__name__icontains=employee_name)
    if status_filter:
        requests = requests.filter(status=status_filter)
   
    requests = requests.order_by(order_by)
   
    data = [{
        'id': req.id,
        'employee': req.employee.first_name,
        'from_location': req.from_location,
        'to_location': req.to_location,
        'status': req.status,
        'travel_from': req.from_location,
        'travel_to': req.to_location
    } for req in requests]
   
    return Response(data, status=HTTP_200_OK)
 
 
 
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
def get_specific_request(request, request_id):
    """
    Retrieves details of a specific travel request by its ID.

    Args:
        request (HttpRequest): The request object from an authenticated user.
        request_id (int): The ID of the travel request to retrieve.

    Returns:
        Response (JSON): The details of the travel request or an error message.
            - HTTP 200: Successfully retrieved the travel request.
            - HTTP 404: Travel request not found.
            - HTTP 500: Database error or unexpected server error.
    """
    try:
        travel_request = TravelRequest.objects.get(id=request_id)
        serializer = TravelRequestSerializer(travel_request)
        return Response(serializer.data, status=HTTP_200_OK)
 
    except TravelRequest.DoesNotExist:
        return Response(
            {"error": "Travel request not found."},
            status=HTTP_404_NOT_FOUND
        )
 
    except DatabaseError:
        return Response(
            {"error": "Database error occurred while fetching travel request details."},
            status=HTTP_500_INTERNAL_SERVER_ERROR
        )
 
    except Exception as e:
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=HTTP_500_INTERNAL_SERVER_ERROR
        )
 
 
@api_view(['PUT'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def close_travel_request(request, request_id):
    """
    Allows the admin to close a travel request if it has been approved.

    The function checks if the travel request exists and is in the "approved" state. 
    If so, it updates the status to "Closed."

    Args:
        request (HttpRequest): The request object from an authenticated admin.
        request_id (int): The ID of the travel request to be closed.

    Returns:
        Response (JSON): A success message or an error message.
            - HTTP 200: Travel request successfully closed.
            - HTTP 400: Request cannot be closed (not in approved state).
            - HTTP 404: Travel request not found.
            - HTTP 500: Unexpected server error.
    """
    try:
        # Retrieve the travel request by ID
        travel_request = TravelRequest.objects.get(id=request_id)

        if travel_request.status == "approved":
            travel_request.status = "Closed"
            travel_request.save()
            return Response(
                {"message": "Approved travel request has been successfully closed."},
                status=HTTP_200_OK
            )
        else:
            return Response(
                {"error": "Only approved travel requests can be closed."},
                status=HTTP_400_BAD_REQUEST
            )

    except TravelRequest.DoesNotExist:
        return Response(
            {"error": "Travel request not found."},
            status=HTTP_404_NOT_FOUND
        )

    except Exception as e:
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=HTTP_500_INTERNAL_SERVER_ERROR
        )

 
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
def get_all_employees(request):
    """
    Retrieves a list of all employees.

    This function fetches all employees from the database and returns their details.

    Args:
        request (HttpRequest): The request object from an authenticated user.

    Returns:
        Response (JSON): A list of all employees.
            - HTTP 200: Successfully retrieved employees.
    """
    employees = Employee.objects.all()
    serializer = EmployeeSerializer(employees, many=True)
    return Response(serializer.data, status=HTTP_200_OK)
 
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
def get_all_managers(request):
    """
    Retrieves a list of all managers.

    This function filters and returns only employees with the role of 'Manager.'

    Args:
        request (HttpRequest): The request object from an authenticated user.

    Returns:
        Response (JSON): A list of all managers.
            - HTTP 200: Successfully retrieved managers.
    """
    managers = Employee.objects.filter(role="Manager")
    serializer = EmployeeSerializer(managers, many=True)
    return Response(serializer.data, status=HTTP_200_OK)
 
@api_view(['PUT'])
@authentication_classes([TokenAuthentication])
def update_user(request, user_id):
    """
    Updates the details of an employee or manager.

    This function allows updating an employee's or manager's details using partial updates.

    Args:
        request (HttpRequest): The request object containing updated data.
        user_id (int): The ID of the user to update.

    Returns:
        Response (JSON): The updated user details or an error message.
            - HTTP 200: Successfully updated user details.
            - HTTP 400: Validation error in submitted data.
            - HTTP 404: User not found.
    """
    try:
        user = Employee.objects.get(id=user_id)
        serializer = EmployeeSerializer(user, data=request.data, partial=True)
 
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
 
    except Employee.DoesNotExist:
        return Response({"error": "User not found."}, status=HTTP_404_NOT_FOUND)
    
@api_view(['PUT'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def manage_travel_request(request, request_id):
    """
    Allows a manager to approve or reject a travel request.

    The manager can update the status of a travel request to either "Approved" or "Rejected."
    An optional rejection reason can also be provided.

    Expected request body:
        {
            "action": "approve" / "reject",
            "reason": "Optional reason for rejection"
        }

    Args:
        request (HttpRequest): The request object containing the manager's decision.
        request_id (int): The ID of the travel request to be updated.

    Returns:
        Response (JSON): A success message or an error message.
            - HTTP 200: Request successfully approved or rejected.
            - HTTP 400: Invalid action provided.
            - HTTP 404: Travel request not found.
    """
    try:
        travel_request = TravelRequest.objects.get(id=request_id)
        action = request.data.get("action")

        if action == "approve":
            travel_request.status = "Approved"
        elif action == "reject":
            travel_request.status = "Rejected"
        else:
            return Response({"error": "Invalid action."}, status=HTTP_400_BAD_REQUEST)

        travel_request.save()
        return Response({
            "message": f"Request {action} successfully!",
            "status": travel_request.status,
        }, status=HTTP_200_OK)

    except TravelRequest.DoesNotExist:
        return Response({"error": "Travel request not found."}, status=HTTP_404_NOT_FOUND)

 
@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
def delete_user(request, user_id):
    """
    Deletes an employee or manager from the system.

    This function removes a user based on the provided user ID.
    Only authenticated users with the necessary permissions can perform this action.

    Args:
        request (HttpRequest): The request object from an authenticated user.
        user_id (int): The ID of the employee or manager to delete.

    Returns:
        Response (JSON): A success message or an error message.
            - HTTP 200: User successfully deleted.
            - HTTP 404: User not found.
    """
    try:
        user = Employee.objects.get(id=user_id)
        user.delete()
        return Response({"message": "User deleted successfully."}, status=HTTP_200_OK)
 
    except Employee.DoesNotExist:
        return Response({"error": "User not found."}, status=HTTP_404_NOT_FOUND)
   

from django.conf import settings


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def admin_request_email(request, request_id):
    """
    Sends an email requesting additional information about a travel request.

    The admin can request additional details from the employee by sending an email.
    The request must be linked to an employee with a valid email.

    Expected request body:
        {
            "additional_requests": "Specify the additional information needed."
        }

    Args:
        request (HttpRequest): The request object containing the additional request details.
        request_id (int): The ID of the travel request for which additional information is required.

    Returns:
        Response (JSON): A success message or an error message.
            - HTTP 200: Additional request saved and email sent successfully.
            - HTTP 400: Request not linked to an employee with an email, or missing additional request details.
            - HTTP 500: Email sending failed due to a server error.
    """
 
    request_obj = get_object_or_404(TravelRequest, id=request_id)

    if not hasattr(request_obj, "employee") or not request_obj.employee or not request_obj.employee.email:
        return Response({"message": "Request is not linked to an Employee with an email."}, status=400)

    recipient_email = request_obj.employee.email 

    additional_request = request.data.get("additional_requests")
    if not additional_request:
        return Response({"message": "Additional request is required"}, status=400)


    request_obj.admin_notes = additional_request 
    request_obj.is_resubmitted = True
    request_obj.save()

    subject = "Additional Information Requested"
    message = (
        f"Dear {request_obj.employee.first_name},\n\n"
        f"We need more details regarding your request (ID: {request_obj.id}).\n\n"
        f"Additional Request: {additional_request}\n\n"
        f"Please provide the requested information at your earliest convenience.\n\n"
        f"Best Regards,\nYour Support Team"
    )

    try:
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,  
            [recipient_email],  
            fail_silently=False,
        )
    except Exception as e:
        return Response({"message": f"Additional request saved, but email failed to send: {str(e)}"}, status=500)

    return Response({"message": "Additional request added and email sent successfully"}, status=200)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def manager_send_email(request, request_id):
    """
    Sends an email from the manager to the employee with additional information.

    The manager can provide notes regarding the employee's travel request, 
    which will be updated in the database and sent via email.

    Expected request body:
        {
            "manager_notes": "Manager's feedback or additional information."
        }

    Args:
        request (HttpRequest): The request object containing the manager's response.
        request_id (int): The ID of the travel request for which the manager is providing feedback.

    Returns:
        Response (JSON): A success message or an error message.
            - HTTP 200: Manager's response added and email sent successfully.
            - HTTP 400: Request is not linked to an employee with an email, or missing manager notes.
            - HTTP 500: Email sending failed due to a server error.
    """

    request_obj = get_object_or_404(TravelRequest, id=request_id)

    if not hasattr(request_obj, "employee") or not request_obj.employee or not request_obj.employee.email:
        return Response({"message": "Request is not linked to an Employee with an email."}, status=400)

    recipient_email = request_obj.employee.email 

    manager_response = request.data.get("manager_notes")
    if not manager_response:
        return Response({"message": "Manager's response is required"}, status=400)

    request_obj.manager_notes = manager_response
    request_obj.save()

    subject = "Information Update from Manager"
    message = (
        f"Dear {request_obj.employee.first_name},\n\n"
        f"Your travel request (ID: {request_obj.id}) has been reviewed by the manager.\n\n"
        f"Manager's Notes: {manager_response}\n\n"
        f"Please review the provided information.\n\n"
        f"Best Regards,\nYour Management Team"
    )

    try:
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER, 
            [recipient_email], 
            fail_silently=False,
        )
    except Exception as e:
        return Response({"message": f"Manager's response saved, but email failed to send: {str(e)}"}, status=500)

    return Response({"message": "Manager's response added and email sent successfully"}, status=200)

 
 
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
def create_initial_admin(request):
    """
    Creates an initial admin account.

    This function registers a new admin user with a hashed password and stores the admin details.

    Expected request body:
        {
            "username": "admin_username",
            "password": "secure_password",
            "email_id": "admin@example.com"
        }

    Args:
        request (HttpRequest): The request object containing the admin details.

    Returns:
        Response (JSON): A success message with admin details or an error message.
            - HTTP 201: Admin created successfully.
            - HTTP 400: Invalid input data (missing fields, validation errors).
    """

    serializer = AdminSerializer(data=request.data)
 
    if serializer.is_valid():
        username = serializer.validated_data.get("username")
        password = request.data.get("password") 
        email_id = serializer.validated_data.get("email_id")
 
        if not password:
            return Response({"error": "Password is required."}, status=status.HTTP_400_BAD_REQUEST)
 
        user = User.objects.create_user(username=username, password=password, email=email_id)

        hashed_password = make_password(password)
 
        admin = Admin.objects.create(
            user=user,
            username=username,
            password=hashed_password,
            email_id=email_id
        )
 
        return Response({"message": "Admin created successfully.", "admin": AdminSerializer(admin).data}, status=status.HTTP_201_CREATED)
 
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
def admin_login(request):
    """
    Authenticates an admin user and generates an authentication token.

    The function verifies the provided username and password. If authentication is 
    successful and the user has an admin profile, a token is returned.

    Expected request body:
        {
            "username": "admin_username",
            "password": "admin_password"
        }

    Args:
        request (HttpRequest): The request object containing the admin's login credentials.

    Returns:
        Response (JSON): A success message with a token or an error message.
            - HTTP 200: Login successful, token provided.
            - HTTP 400: Missing username or password.
            - HTTP 401: Invalid credentials or user is not an admin.
    """
    username = request.data.get('username')
    password = request.data.get('password')
 
    if not username or not password:
        return Response({"error": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(username=username, password=password)
 
    if user is not None and hasattr(user, 'admin_profile'):  
        token, created = Token.objects.get_or_create(user=user)
        return Response({"message": "Login successful", "token": token.key}, status=status.HTTP_200_OK)
   
    return Response({"error": "Invalid credentials or user is not an admin."}, status=status.HTTP_401_UNAUTHORIZED)
 
 
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
def user_login(request):
    """
    Authenticates a manager or employee and generates an authentication token.

    The function verifies the provided username and password. If authentication is 
    successful, it checks the user's role and returns a token.

    Expected request body:
        {
            "username": "user_username",
            "password": "user_password"
        }

    Args:
        request (HttpRequest): The request object containing the user's login credentials.

    Returns:
        Response (JSON): A success message with a token or an error message.
            - HTTP 200: Login successful, token provided.
            - HTTP 400: Missing username or password.
            - HTTP 401: Invalid credentials.
            - HTTP 403: Unauthorized role (not a manager or employee).
            - HTTP 404: User profile not found.
    """
    username = request.data.get('username')
    password = request.data.get('password')
 
    if not username or not password:
        return Response({"error": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)
 
    user = authenticate(username=username, password=password)
 
    if user is None:
        return Response({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

    user_profile = UserProfile.objects.filter(user=user).first()
   
    if not user_profile:
        return Response({"error": "User profile not found in the database."}, status=status.HTTP_404_NOT_FOUND)
 
    role = user_profile.role
 
    if role not in ["manager", "employee"]:
        return Response({"error": "Unauthorized user role."}, status=status.HTTP_403_FORBIDDEN)
 
    token, created = Token.objects.get_or_create(user=user)
 
    return Response({
        "message": "Login successful",
        "token": token.key,
        "role": role,
        "status": user_profile.status
    }, status=status.HTTP_200_OK)
 
 
 
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def user_logout(request):
    """
    Logs out the authenticated user by deleting their authentication token.

    This function ensures that the user's token is removed, effectively logging them out 
    and preventing further access to authenticated endpoints until they log in again.

    Args:
        request (HttpRequest): The request object from the authenticated user.

    Returns:
        Response (JSON): A success message or an error message.
            - HTTP 200: Logout successful.
            - HTTP 500: Unexpected error occurred while logging out.
    """
    try:
        request.user.auth_token.delete()
        return Response({"message": "Logout successful."}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": "Something went wrong."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
 
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def add_user(request):
    """
    Allows an admin to add a new user as a manager or employee.

    The function verifies that the request is made by an admin and then 
    creates a new user account with the specified details.

    Expected request body:
        {
            "user_type": "manager" / "employee",
            "username": "new_username",
            "email": "user@example.com",
            "password": "secure_password",
            "first_name": "John",
            "last_name": "Doe",
            "gender": "Male" / "Female" / "Not Specified",
            "designation": "HR" (default: HR),
            "status": "active" / "inactive" (default: active),
            "manager": 1  # (Required only if user_type is 'employee')
        }

    Args:
        request (HttpRequest): The request object containing the user details.

    Returns:
        Response (JSON): A success message with the newly created user's details or an error message.
            - HTTP 201: User created successfully (manager or employee).
            - HTTP 400: Missing or invalid data (e.g., duplicate username/email, invalid user type).
            - HTTP 403: User does not have permission to add users.
    """
    if not hasattr(request.user, 'admin_profile'):
        return Response({"error": "Only admins can add users."}, status=status.HTTP_403_FORBIDDEN)
 
    user_type = request.data.get("user_type") 
    if user_type not in ["manager", "employee"]:
        return Response({"error": "Invalid user_type. Choose 'manager' or 'employee'."}, status=status.HTTP_400_BAD_REQUEST)
 

    username = request.data.get("username")
    email = request.data.get("email")
    password = request.data.get("password")
 
    if not all([username, email, password]):
        return Response({"error": "Username, email, and password are required."}, status=status.HTTP_400_BAD_REQUEST)

    if UserProfile.objects.filter(user__username=username).exists():
        return Response({"error": "A user with this username already exists."}, status=status.HTTP_400_BAD_REQUEST)
    if UserProfile.objects.filter(user__email=email).exists():
        return Response({"error": "A user with this email already exists."}, status=status.HTTP_400_BAD_REQUEST)
 
    first_name = request.data.get("first_name")
    last_name = request.data.get("last_name")
    gender = request.data.get("gender", "Not Specified")
    designation = request.data.get("designation", "HR") 
    status_choice = request.data.get("status", "active")
 
    if not all([first_name, last_name, designation]):
        return Response({"error": "First name, last name and designation are required."}, status=status.HTTP_400_BAD_REQUEST)
 
    user = User(username=username, email=email)
    user.set_password(password) 
    user.save()
 
    user_profile = UserProfile.objects.create(user=user, role=user_type, status=status_choice)
 
    if user_type == "manager":
        manager = Manager.objects.create(
            user_profile=user_profile,
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            email=email,
            status=status_choice,
            designation=designation
        )
        return Response({"message": "Manager created successfully.", "manager": ManagerSerializer(manager).data},
                        status=status.HTTP_201_CREATED)
 
    elif user_type == "employee":
        manager_id = request.data.get("manager")
        manager = None
        if manager_id:
            try:
                manager = Manager.objects.get(id=manager_id)
            except Manager.DoesNotExist:
                return Response({"error": "Manager not found."}, status=status.HTTP_400_BAD_REQUEST)
 
        employee = Employee.objects.create(
            user_profile=user_profile,
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            email=email,
            status=status_choice,
            designation=designation,
            manager=manager
        )
        return Response({"message": "Employee created successfully.", "employee": EmployeeSerializer(employee).data},
                        status=status.HTTP_201_CREATED)

@csrf_exempt
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def send_additional_info_request(request, request_id):
    """
    Admin can send an email to an employee requesting additional information.
    
    Expected request body:
    {
        "message": "Provide the required details about your trip."
    }
    """
    try:
        travel_request = TravelRequest.objects.get(id=request_id)
        admin_message = request.data.get("message")

        if not admin_message:
            return Response({"error": "Message cannot be empty."}, status=HTTP_400_BAD_REQUEST)

        travel_request.admin_notes = admin_message
        travel_request.save()

        subject = "Request for Additional Information"
        message = f"Dear {travel_request.employee.first_name},\n\n{admin_message}\n\nPlease respond as soon as possible.\n\nBest regards,\nAdmin"
        recipient_email = travel_request.employee.email 

        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER, 
            [recipient_email],  
            fail_silently=False,
        )

        return Response({
            "message": "Email sent successfully!",
            "admin_notes": travel_request.admin_notes
        }, status=HTTP_200_OK)

    except TravelRequest.DoesNotExist:
        return Response({"error": "Travel request not found."}, status=HTTP_404_NOT_FOUND)
