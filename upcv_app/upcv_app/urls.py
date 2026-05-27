from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from almacen_app import views as almacen_views
from tienda import views as tienda_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', tienda_views.tienda_inicio, name='home'),
    path('tienda/', include('tienda.urls')),
    path('almacen/', include('almacen_app.urls')),
    path('login/', almacen_views.signin, name='login'),
    path('signin/', almacen_views.signin, name='signin'),
    path('logout/', almacen_views.signout, name='logout'),
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
