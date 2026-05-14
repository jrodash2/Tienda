from django.db import migrations


def create_store_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for group_name in ('Tienda', 'Ventas'):
        Group.objects.get_or_create(name=group_name)


def noop_reverse(apps, schema_editor):
    # No se eliminan grupos para no afectar permisos existentes en ambientes instalados.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('tienda', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(create_store_groups, noop_reverse),
    ]
