from django.contrib import admin
from rest_framework.authtoken.views import obtain_auth_token
from django.urls import path
from .import views 

urlpatterns = [

    #employee apis
    path('employee/dashboard/', views.employee_view_dashboard, name='employee_dashboard'), # Employee dashboard
    path('employee/view-request/<int:request_id>/', views.employee_view_request, name='employee-view-request'), # View a specific request
    path('employee/edit-request/<int:request_id>/', views.employee_edit_request, name='edit_request'), # Edit travel request
    path('employee/cancel-request/<int:request_id>/', views.employee_cancel_request, name='cancel_request'), # Cancel travel request
    path('submit-request/', views.employee_submit_request, name='employee_submit_request'), 
    path('employee/resubmit-request/<int:request_id>/', views.employee_resubmit_request, name='resubmit_request'),

    #manager apis
    path('manager/view-requests/',views.manager_view_requests, name="manager_view_requests"), # manager view all requests
    path('manager/view-request/<int:request_id>/',views.manager_view_request_by_id, name="manager_view_requests"),
    path('manager/filter-sort-requests/',views.manager_filter_sort_requests, name="manager_view_requests"), # manager filter and sort requests
    path('manager/action/<int:request_id>/', views.manage_travel_request, name='manage_travel_request'), # manager approve or reject request
    path('manager/search/', views.manager_search_requests, name='manager-view-request'), # manager search requests
    path('manager/request-info/<int:request_id>/', views.manager_send_email, name='manager-view-request'), # manager send email request
    

    #admin apis
     path('api/travel-requests/', views.get_travel_requests, name='travel-requests-list'),    # View all requests
     path('api/view-specific-request/<int:request_id>', views.get_specific_request, name='travel-requests-list'),    #View a specific request
     path('api/request-info/<int:request_id>/', views.admin_request_email, name='request-additional-info'), #send email request
     path('api/close-request/<int:request_id>/', views.close_travel_request, name='process-close-travel-request'), #close approved request
     path('api/employees/', views.get_all_employees, name='all-employees'),   #Get all employees
     path('api/managers/', views.get_all_managers, name='all-managers'),  # Get all managers
     path('api/update-user/<int:user_id>/', views.update_user, name='update-user'),   #Update user details
     path('initial_register_admin/',views.create_initial_admin), #create admin
     path('admin_login/',views.admin_login), #admin login
     path('userlogin/',views.user_login), #employee or manager login
     path('logout/',views.user_logout), # employee or manager logout
     path('add_user/',views.add_user), #admin adds employee or manager
     path('delete_user/<str:email>/',views.delete_user), #admin deletes employee or manager
   ]

 

