# Generated by Django 3.0.3 on 2020-08-17 10:18

from django.db import migrations

from openwisp_monitoring.monitoring.configuration import get_metric_configuration


def standardize_alertsettings_threshold(apps, schema_editor):
    AlertSettings = apps.get_model('monitoring', 'AlertSettings')
    metric_config = get_metric_configuration()
    for alert_settings in AlertSettings.objects.filter(
        metric__configuration__in=['disk', 'memory', 'cpu'], custom_threshold__lte=1
    ):
        alert_settings.custom_threshold *= 100
        if (
            alert_settings.custom_threshold
            == metric_config[alert_settings.metric.configuration]['alert_settings'][
                'threshold'
            ]
        ):
            alert_settings.custom_threshold = None
        alert_settings.save()


def reverse_alertsettings_threshold(apps, schema_editor):
    AlertSettings = apps.get_model('monitoring', 'AlertSettings')
    metric_config = get_metric_configuration()
    for alert_settings in AlertSettings.objects.filter(
        metric__configuration__in=['disk', 'memory', 'cpu']
    ):
        if alert_settings.custom_threshold is None:
            alert_settings.custom_threshold = metric_config[
                alert_settings.metric.configuration
            ]['alert_settings']['threshold']
        alert_settings.custom_threshold /= 100
        alert_settings.save()


class Migration(migrations.Migration):

    dependencies = [('monitoring', '0020_make_alertsettings_fields_null')]

    operations = [
        migrations.RunPython(
            standardize_alertsettings_threshold,
            reverse_code=reverse_alertsettings_threshold,
        )
    ]
