from django.urls import path
from . import views

urlpatterns = [
    path('', views.predictions_home, name='predictions_home'),
    path('new/', views.new_prediction, name='new_prediction'),
    path('<int:prediction_id>/', views.prediction_detail, name='prediction_detail'),
    path('models/train/', views.train_prediction_model, name='train_model'),
    path('models/<int:model_id>/', views.model_detail, name='model_detail'),
    path('models/<int:model_id>/activate/', views.set_active_model, name='set_active_model'),
    path('models/<int:model_id>/delete/', views.delete_model, name='delete_model'),
]