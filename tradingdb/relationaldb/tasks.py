import traceback
from datetime import timedelta

from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.mail import mail_admins
from django.core.management import call_command, settings
from django.db import transaction
from django.utils import timezone

from .models import TournamentParticipant

logger = get_task_logger(__name__)

oid = 'TOURNAMENT_BLOCK'


def send_email(message):
    logger.info('Task error: {}'.format(message))
    # send email
    mail_admins('[tradingdb Error] ', message)


@shared_task
def issue_tokens():
    participants = TournamentParticipant.objects.filter(
        tokens_issued=False,
        created__lte=timezone.now() - timedelta(minutes=1)  # 1 min timeframe to prevent issuing tokens twice in the event of reorg
    )[:50]

    if len(participants):
        try:
            participant_addresses = participants.values_list('address', flat=True)
            participant_addresses_string = ",".join(address for address in participant_addresses)
            # Update first
            with transaction.atomic():
                TournamentParticipant.objects.filter(address__in=participant_addresses).update(tokens_issued=True)
                call_command('issue_tournament_tokens', participant_addresses_string, settings.TOURNAMENT_TOKEN_ISSUANCE)
        except Exception as err:
            logger.error(err)
            send_email(traceback.format_exc())
    else:
        logger.info("No new tournament participants")


@shared_task
def clear_issued_tokens_flag():
    TournamentParticipant.objects.filter(tokens_issued=True).update(tokens_issued=False)
    logger.info("Cleared issued tokens flag for tournament participants")


@shared_task
def calculate_scoreboard():
    """
    The task executes the calculation of the scoreboard
    """
    try:
        call_command('calculate_scoreboard')
    except Exception as err:
        logger.error(str(err))
        send_email(traceback.format_exc())


@shared_task
def db_dump():
    """
    The task creates a dump of the database
    """
    try:
        call_command('db_dump')
    except Exception as err:
        logger.error(str(err))
        send_email(traceback.format_exc())
