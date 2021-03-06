# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-12-19 09:03
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('relationaldb', '0006_auto_20171219_0857'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tournamentparticipantbalance',
            name='participant',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='tournament_balance', to='relationaldb.TournamentParticipant'),
        ),
    ]
