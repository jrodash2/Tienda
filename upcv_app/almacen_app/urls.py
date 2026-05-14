from django.urls import path
from django.contrib.auth import views as auth_views
from . import views


app_name = 'almacen'

# Manejador global de errores (esto debe estar fuera de urlpatterns)
handler403 = 'almacen_app.views.acceso_denegado'  # Asegúrate que el nombre de tu app sea correcto

urlpatterns = [
    path('', views.home, name='home'), 
    path('dahsboard/', views.dahsboard, name='dahsboard'),
    path('signin/', views.signin, name='signin'),
    path('logout/', views.signout, name='logout'),

    # Acceso denegado
    path('no-autorizado/', views.acceso_denegado, name='acceso_denegado'),

    # Usuarios
    path('usuario/crear/', views.user_create, name='user_create'),
    path('usuario/editar/<int:user_id>/', views.user_edit, name='user_edit'),

    path('usuario/eliminar/<int:user_id>/', views.user_delete, name='user_delete'),

    # Cambiar contraseña
    path('cambiar-contraseña/', auth_views.PasswordChangeView.as_view(
        template_name='almacen/password_change_form.html',
        success_url='/cambiar-contraseña/hecho/'  # Redirección tras éxito
    ), name='password_change'),

    path('cambiar-contraseña/hecho/', auth_views.PasswordChangeDoneView.as_view(
        template_name='almacen/password_change_done.html'
    ), name='password_change_done'),
    
  
    path('institucion/editar/', views.editar_institucion, name='editar_institucion'),
    
    

]
